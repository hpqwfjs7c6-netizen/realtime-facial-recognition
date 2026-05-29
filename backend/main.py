"""API FastAPI de reconnaissance faciale temps réel.

Endpoints :
  GET  /health              -> état du service
  POST /analyze-face        -> analyse une image (multi-visages, multi-références)
  POST /references          -> enrôle un visage de référence (upload)
  GET  /references          -> liste les références
  DELETE /references/{id}   -> supprime une référence
  GET  /history             -> historique des reconnaissances
  GET  /settings            -> seuils et configuration courante
"""
import base64
import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database
import recognition
from actions import trigger_action
from config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("recognition.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    if not settings.azure_configured():
        logger.warning("Clés Azure manquantes : la détection de visages échouera.")
    if recognition.DeepFace is None:
        logger.warning("DeepFace non installé : la vérification 1:1 échouera (pip install deepface).")
    logger.info("Démarrage OK — %d référence(s) enrôlée(s).", len(database.list_references()))
    yield


app = FastAPI(title="Real-time Facial Recognition API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Auth simple par clé API (optionnelle) ---
async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if settings.API_KEY and x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Clé API invalide ou manquante.")


class ImagePayload(BaseModel):
    image: str


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "azure_configured": settings.azure_configured(),
        "deepface_available": recognition.DeepFace is not None,
        "references": len(database.list_references()),
        "recognition_action": settings.RECOGNITION_ACTION,
    }


@app.get("/settings")
async def get_settings() -> dict:
    return {
        "headpose_pitch_max": settings.HEADPOSE_PITCH_MAX,
        "headpose_yaw_max": settings.HEADPOSE_YAW_MAX,
        "recognition_action": settings.RECOGNITION_ACTION,
        "deepface_model": settings.DEEPFACE_MODEL,
    }


def _decode_image(data_url: str) -> bytes:
    raw = data_url.split(",", 1)[1] if "," in data_url else data_url
    try:
        return base64.b64decode(raw)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Erreur de décodage base64 : {exc}")


@app.post("/analyze-face", dependencies=[Depends(require_api_key)])
async def analyze_face(payload: ImagePayload) -> dict:
    if not settings.azure_configured():
        raise HTTPException(status_code=500, detail="Azure Face API non configuré.")

    image_bytes = _decode_image(payload.image)

    try:
        detected = recognition.detect_faces(image_bytes)
    except requests_exc() as exc:
        raise HTTPException(status_code=502, detail=f"Erreur réseau vers Azure : {exc}")

    if not detected:
        return {"faces": []}

    capture_path = recognition.save_temp_capture(image_bytes)
    faces_out = []
    try:
        for face in detected:
            rect = face.get("faceRectangle", {})
            pose = face.get("faceAttributes", {}).get("headPose", {})
            pitch = pose.get("pitch", 0.0)
            yaw = pose.get("yaw", 0.0)
            roll = pose.get("roll", 0.0)

            recognized = False
            confidence = 0.0
            name = None
            ref_id = None
            system_action = "None"

            if not recognition.is_looking_direct(pitch, yaw):
                system_action = "User looking away"
            else:
                recognized, confidence, matched = recognition.verify_against_references(capture_path)
                if recognized and matched:
                    name = matched["name"]
                    ref_id = matched["id"]
                    system_action = trigger_action(name, confidence)
                elif recognition.DeepFace is None or not database.list_references():
                    system_action = "No reference / DeepFace missing"
                else:
                    system_action = "Not recognized"

            database.log_event(
                recognized=recognized,
                confidence=confidence,
                pitch=pitch,
                yaw=yaw,
                roll=roll,
                name=name,
                reference_id=ref_id,
                system_action=system_action,
            )

            faces_out.append(
                {
                    "faceRectangle": {
                        "top": rect.get("top", 0),
                        "left": rect.get("left", 0),
                        "width": rect.get("width", 0),
                        "height": rect.get("height", 0),
                    },
                    "recognized": recognized,
                    "confidence": round(confidence, 2),
                    "name": name,
                    "pitch": pitch,
                    "yaw": yaw,
                    "roll": roll,
                    "system_action": system_action,
                }
            )
    finally:
        if os.path.exists(capture_path):
            os.remove(capture_path)

    return {"faces": faces_out}


@app.post("/references", dependencies=[Depends(require_api_key)])
async def enroll_reference(name: str = Form(...), file: UploadFile = File(...)) -> dict:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide.")
    database.init_db()  # garantit que REFERENCES_DIR existe
    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    safe_name = "".join(c for c in name if c.isalnum() or c in ("-", "_")) or "ref"
    dest = os.path.join(settings.REFERENCES_DIR, f"{safe_name}_{os.urandom(4).hex()}{ext}")
    with open(dest, "wb") as f:
        f.write(content)
    return database.add_reference(name, dest)


@app.get("/references", dependencies=[Depends(require_api_key)])
async def get_references() -> dict:
    return {"references": database.list_references()}


@app.delete("/references/{ref_id}", dependencies=[Depends(require_api_key)])
async def remove_reference(ref_id: int) -> dict:
    if not database.delete_reference(ref_id):
        raise HTTPException(status_code=404, detail="Référence introuvable.")
    return {"deleted": ref_id}


@app.get("/history", dependencies=[Depends(require_api_key)])
async def get_history(limit: int = 50) -> dict:
    return {"events": database.list_events(limit=limit)}


def requests_exc():
    """Tuple d'exceptions réseau requests (import paresseux pour faciliter les tests)."""
    import requests

    return requests.exceptions.RequestException
