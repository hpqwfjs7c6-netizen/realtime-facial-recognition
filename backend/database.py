"""Persistance SQLite : visages de référence enrôlés et historique des reconnaissances."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from config import settings


def _ensure_dirs() -> None:
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    os.makedirs(settings.REFERENCES_DIR, exist_ok=True)


@contextmanager
def get_connection():
    _ensure_dirs()
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Crée les tables si elles n'existent pas."""
    _ensure_dirs()
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS references_face (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                image_path TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS recognition_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference_id INTEGER,
                name TEXT,
                recognized INTEGER NOT NULL,
                confidence REAL NOT NULL,
                pitch REAL,
                yaw REAL,
                roll REAL,
                system_action TEXT,
                created_at TEXT NOT NULL
            );
            """
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Références ---

def add_reference(name: str, image_path: str) -> dict:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO references_face (name, image_path, created_at) VALUES (?, ?, ?)",
            (name, image_path, _now()),
        )
        ref_id = cur.lastrowid
    # N'expose pas image_path (chemin filesystem interne) dans les réponses API.
    return {"id": ref_id, "name": name}


def list_references() -> list[dict]:
    """Liste publique des références — sans le chemin filesystem interne."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, created_at FROM references_face ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def list_references_internal() -> list[dict]:
    """Usage interne : inclut image_path (jamais exposé via l'API)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, image_path, created_at FROM references_face ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_reference(ref_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, image_path, created_at FROM references_face WHERE id = ?",
            (ref_id,),
        ).fetchone()
    return dict(row) if row else None


def delete_reference(ref_id: int) -> bool:
    ref = get_reference(ref_id)
    if not ref:
        return False
    with get_connection() as conn:
        conn.execute("DELETE FROM references_face WHERE id = ?", (ref_id,))
    # Suppression du fichier image associé
    try:
        if ref["image_path"] and os.path.exists(ref["image_path"]):
            os.remove(ref["image_path"])
    except OSError:
        pass
    return True


# --- Historique ---

def log_event(
    recognized: bool,
    confidence: float,
    pitch: float | None = None,
    yaw: float | None = None,
    roll: float | None = None,
    name: str | None = None,
    reference_id: int | None = None,
    system_action: str | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO recognition_events
               (reference_id, name, recognized, confidence, pitch, yaw, roll, system_action, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                reference_id,
                name,
                1 if recognized else 0,
                confidence,
                pitch,
                yaw,
                roll,
                system_action,
                _now(),
            ),
        )


def list_events(limit: int = 50) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM recognition_events ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    events = []
    for row in rows:
        event = dict(row)
        event["recognized"] = bool(event["recognized"])
        events.append(event)
    return events
