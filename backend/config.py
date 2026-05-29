"""Configuration centralisée et validée pour l'API de reconnaissance faciale."""
import os
from dotenv import load_dotenv

load_dotenv()


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _get_list(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


class Settings:
    """Paramètres de l'application, chargés depuis l'environnement."""

    # --- Azure Face API ---
    AZURE_FACE_ENDPOINT: str = os.getenv("AZURE_FACE_ENDPOINT", "")
    AZURE_FACE_KEY: str = os.getenv("AZURE_FACE_KEY", "")
    AZURE_TIMEOUT: float = _get_float("AZURE_TIMEOUT", 10.0)

    # --- Stockage ---
    DATA_DIR: str = os.getenv("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
    DB_PATH: str = os.getenv("DB_PATH", os.path.join(DATA_DIR, "app.db"))
    REFERENCES_DIR: str = os.getenv("REFERENCES_DIR", os.path.join(DATA_DIR, "references"))

    # --- Reconnaissance ---
    # Seuils head pose (regard direct)
    HEADPOSE_PITCH_MAX: float = _get_float("HEADPOSE_PITCH_MAX", 15.0)
    HEADPOSE_YAW_MAX: float = _get_float("HEADPOSE_YAW_MAX", 15.0)
    # Modèle DeepFace
    DEEPFACE_MODEL: str = os.getenv("DEEPFACE_MODEL", "VGG-Face")

    # --- Action déclenchée à la reconnaissance ---
    # Valeurs: none | log | command | webhook
    RECOGNITION_ACTION: str = os.getenv("RECOGNITION_ACTION", "log").lower()
    RECOGNITION_COMMAND: str = os.getenv("RECOGNITION_COMMAND", "")
    RECOGNITION_WEBHOOK_URL: str = os.getenv("RECOGNITION_WEBHOOK_URL", "")

    # --- Sécurité / API ---
    API_KEY: str = os.getenv("API_KEY", "")  # vide = pas d'auth
    CORS_ORIGINS: list[str] = _get_list("CORS_ORIGINS", "http://localhost:3000")

    @classmethod
    def azure_configured(cls) -> bool:
        return bool(cls.AZURE_FACE_ENDPOINT and cls.AZURE_FACE_KEY)


settings = Settings()
