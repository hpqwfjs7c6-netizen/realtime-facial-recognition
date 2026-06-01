"""Logique de reconnaissance : détection Azure (multi-visages) + vérification DeepFace (multi-références)."""
import io
import logging
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

import requests

from config import settings
from database import list_references_internal

logger = logging.getLogger("recognition.engine")

# Codes HTTP transitoires sur lesquels une nouvelle tentative a du sens.
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
# Exécuteur dédié pour borner la durée des vérifications DeepFace (R8).
_verify_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="deepface")

try:
    from deepface import DeepFace
except ImportError:  # pragma: no cover
    DeepFace = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


def azure_headers() -> dict:
    return {
        "Ocp-Apim-Subscription-Key": settings.AZURE_FACE_KEY,
        "Content-Type": "application/octet-stream",
    }


def detect_faces(image_bytes: bytes) -> list[dict]:
    """Appelle Azure Face Detect avec retries/backoff sur erreurs transitoires.

    Réessaie sur erreurs réseau (timeout, connexion) et statuts HTTP 429/5xx,
    avec un backoff exponentiel (`AZURE_BACKOFF_BASE * 2**tentative`). Les erreurs
    4xx non transitoires (hors 429) sont propagées immédiatement.
    """
    url = (
        f"{settings.AZURE_FACE_ENDPOINT.rstrip('/')}/face/v1.0/detect"
        "?returnFaceId=false&returnFaceLandmarks=false"
        "&returnFaceAttributes=headPose"
        "&detectionModel=detection_03&recognitionModel=recognition_04"
    )
    attempts = max(0, settings.AZURE_MAX_RETRIES) + 1
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.post(
                url,
                headers=azure_headers(),
                data=image_bytes,
                timeout=settings.AZURE_TIMEOUT,
            )
            if response.status_code in _RETRYABLE_STATUS and attempt < attempts - 1:
                logger.warning(
                    "Azure a renvoyé %s (tentative %d/%d), nouvelle tentative…",
                    response.status_code, attempt + 1, attempts,
                )
                last_exc = requests.HTTPError(f"HTTP {response.status_code}")
            else:
                response.raise_for_status()
                return response.json()
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_exc = exc
            if attempt >= attempts - 1:
                break
            logger.warning(
                "Erreur réseau Azure (tentative %d/%d) : %s", attempt + 1, attempts, exc
            )
        # Backoff exponentiel avant la prochaine tentative.
        time.sleep(settings.AZURE_BACKOFF_BASE * (2 ** attempt))

    # Toutes les tentatives ont échoué : propage la dernière erreur réseau.
    raise last_exc if last_exc else requests.RequestException("Azure injoignable")


def is_looking_direct(pitch: float, yaw: float) -> bool:
    return (
        -settings.HEADPOSE_PITCH_MAX <= pitch <= settings.HEADPOSE_PITCH_MAX
        and -settings.HEADPOSE_YAW_MAX <= yaw <= settings.HEADPOSE_YAW_MAX
    )


def is_clear_for_enrollment(pitch: float, yaw: float, roll: float) -> bool:
    """Vrai si la pose de tête est suffisamment frontale pour une référence nette."""
    return (
        abs(pitch) <= settings.AUTO_ENROLL_PITCH_MAX
        and abs(yaw) <= settings.AUTO_ENROLL_YAW_MAX
        and abs(roll) <= settings.AUTO_ENROLL_ROLL_MAX
    )


def _verify_with_timeout(ref_path: str, capture_path: str) -> dict:
    """Exécute DeepFace.verify avec une borne de temps (évite un hang process).

    Lève `concurrent.futures.TimeoutError` si la vérification dépasse
    `DEEPFACE_TIMEOUT`.
    """
    future = _verify_executor.submit(
        DeepFace.verify,
        img1_path=ref_path,
        img2_path=capture_path,
        model_name=settings.DEEPFACE_MODEL,
        enforce_detection=False,
    )
    return future.result(timeout=settings.DEEPFACE_TIMEOUT)


def verify_against_references(capture_path: str) -> tuple[bool, float, dict | None]:
    """Compare la capture à toutes les références enrôlées.

    Retourne (reconnu, meilleure_confiance, référence_correspondante).
    """
    if DeepFace is None:
        logger.warning("DeepFace n'est pas installé.")
        return False, 0.0, None

    references = list_references_internal()
    if not references:
        return False, 0.0, None

    best_confidence = 0.0
    matched_ref: dict | None = None

    for ref in references:
        if not os.path.exists(ref["image_path"]):
            continue
        try:
            result = _verify_with_timeout(ref["image_path"], capture_path)
        except FuturesTimeoutError:
            try:
                import metrics
                metrics.inc("deepface_timeouts_total")
            except Exception:  # noqa: BLE001 — métriques best-effort
                pass
            logger.error(
                "DeepFace : délai dépassé (%.1fs) pour la référence %s.",
                settings.DEEPFACE_TIMEOUT, ref["id"],
            )
            continue
        except Exception as exc:  # noqa: BLE001
            logger.error("Erreur DeepFace pour la référence %s: %s", ref["id"], exc)
            continue

        distance = result.get("distance", 1.0)
        confidence = max(0.0, 1.0 - distance)
        if result.get("verified", False) and confidence > best_confidence:
            best_confidence = confidence
            matched_ref = ref

    return matched_ref is not None, best_confidence, matched_ref


def _crop_face_bytes(image_bytes: bytes, rect: dict, padding: float = 0.25) -> bytes:
    """Recadre le visage (rectangle Azure) avec une marge. Renvoie un JPEG.

    Si Pillow est indisponible ou le rectangle invalide, renvoie l'image entière.
    """
    if Image is None:
        return image_bytes
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:  # noqa: BLE001
        return image_bytes

    w, h = img.size
    left = rect.get("left", 0)
    top = rect.get("top", 0)
    fw = rect.get("width", 0)
    fh = rect.get("height", 0)
    if fw <= 0 or fh <= 0:
        return image_bytes

    px = int(fw * padding)
    py = int(fh * padding)
    x1 = max(0, left - px)
    y1 = max(0, top - py)
    x2 = min(w, left + fw + px)
    y2 = min(h, top + fh + py)
    if x2 <= x1 or y2 <= y1:
        return image_bytes

    crop = img.crop((x1, y1, x2, y2))
    out = io.BytesIO()
    crop.save(out, format="JPEG", quality=90)
    return out.getvalue()


def save_temp_capture(image_bytes: bytes, rect: dict | None = None) -> str:
    """Écrit la capture (recadrée sur le visage si `rect` fourni) dans un fichier temporaire unique."""
    data = _crop_face_bytes(image_bytes, rect) if rect else image_bytes
    fd, path = tempfile.mkstemp(suffix=".jpg", prefix="capture_", dir=settings.DATA_DIR)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return path


def save_reference_image(image_bytes: bytes, rect: dict | None = None) -> str:
    """Persiste le visage recadré comme image de référence et renvoie son chemin."""
    os.makedirs(settings.REFERENCES_DIR, exist_ok=True)
    data = _crop_face_bytes(image_bytes, rect) if rect else image_bytes
    fd, path = tempfile.mkstemp(suffix=".jpg", prefix="auto_", dir=settings.REFERENCES_DIR)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return path
