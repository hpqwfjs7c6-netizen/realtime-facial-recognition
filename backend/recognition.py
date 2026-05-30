"""Logique de reconnaissance : détection Azure (multi-visages) + vérification DeepFace (multi-références)."""
import logging
import os
import tempfile

import requests

from config import settings
from database import list_references_internal

logger = logging.getLogger("recognition.engine")

try:
    from deepface import DeepFace
except ImportError:  # pragma: no cover
    DeepFace = None


def azure_headers() -> dict:
    return {
        "Ocp-Apim-Subscription-Key": settings.AZURE_FACE_KEY,
        "Content-Type": "application/octet-stream",
    }


def detect_faces(image_bytes: bytes) -> list[dict]:
    """Appelle Azure Face Detect et retourne la liste des visages (avec headPose)."""
    url = (
        f"{settings.AZURE_FACE_ENDPOINT.rstrip('/')}/face/v1.0/detect"
        "?returnFaceId=false&returnFaceLandmarks=false"
        "&returnFaceAttributes=headPose"
        "&detectionModel=detection_03&recognitionModel=recognition_04"
    )
    response = requests.post(
        url,
        headers=azure_headers(),
        data=image_bytes,
        timeout=settings.AZURE_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def is_looking_direct(pitch: float, yaw: float) -> bool:
    return (
        -settings.HEADPOSE_PITCH_MAX <= pitch <= settings.HEADPOSE_PITCH_MAX
        and -settings.HEADPOSE_YAW_MAX <= yaw <= settings.HEADPOSE_YAW_MAX
    )


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
            result = DeepFace.verify(
                img1_path=ref["image_path"],
                img2_path=capture_path,
                model_name=settings.DEEPFACE_MODEL,
                enforce_detection=False,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Erreur DeepFace pour la référence %s: %s", ref["id"], exc)
            continue

        distance = result.get("distance", 1.0)
        confidence = max(0.0, 1.0 - distance)
        if result.get("verified", False) and confidence > best_confidence:
            best_confidence = confidence
            matched_ref = ref

    return matched_ref is not None, best_confidence, matched_ref


def save_temp_capture(image_bytes: bytes) -> str:
    """Écrit la capture dans un fichier temporaire unique (évite les collisions concurrentes)."""
    fd, path = tempfile.mkstemp(suffix=".jpg", prefix="capture_", dir=settings.DATA_DIR)
    with os.fdopen(fd, "wb") as f:
        f.write(image_bytes)
    return path
