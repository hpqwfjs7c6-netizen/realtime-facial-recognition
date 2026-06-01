import base64
import io
import logging

import main
import recognition

# Un pixel JPEG encodé en base64 (data URL).
PIXEL_B64 = (
    "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8U"
    "HRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAA"
    "AAAACP/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AfwD/2Q=="
)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["azure_configured"] is True


def test_settings(client):
    resp = client.get("/settings")
    assert resp.status_code == 200
    assert "headpose_pitch_max" in resp.json()


def test_analyze_no_face(client, monkeypatch):
    monkeypatch.setattr(recognition, "detect_faces", lambda b: [])
    resp = client.post("/analyze-face", json={"image": PIXEL_B64})
    assert resp.status_code == 200
    assert resp.json() == {"faces": []}


def test_analyze_looking_away(client, monkeypatch):
    fake = [{"faceRectangle": {"top": 1, "left": 2, "width": 3, "height": 4},
             "faceAttributes": {"headPose": {"pitch": 40, "yaw": 0, "roll": 0}}}]
    monkeypatch.setattr(recognition, "detect_faces", lambda b: fake)
    resp = client.post("/analyze-face", json={"image": PIXEL_B64})
    assert resp.status_code == 200
    face = resp.json()["faces"][0]
    assert face["recognized"] is False
    assert face["system_action"] == "User looking away"


def test_analyze_recognized(client, monkeypatch):
    fake = [{"faceRectangle": {"top": 1, "left": 2, "width": 3, "height": 4},
             "faceAttributes": {"headPose": {"pitch": 0, "yaw": 0, "roll": 0}}}]
    monkeypatch.setattr(recognition, "detect_faces", lambda b: fake)
    monkeypatch.setattr(
        recognition, "verify_against_references",
        lambda path: (True, 0.91, {"id": 1, "name": "Alice"}),
    )
    resp = client.post("/analyze-face", json={"image": PIXEL_B64})
    assert resp.status_code == 200
    face = resp.json()["faces"][0]
    assert face["recognized"] is True
    assert face["name"] == "Alice"
    assert face["confidence"] == 0.91


def test_auto_enroll_unknown_clear_face(client, monkeypatch):
    """Un visage net non reconnu est auto-enrôlé puis renvoyé comme « Visage N »."""
    fake = [{"faceRectangle": {"top": 0, "left": 0, "width": 1, "height": 1},
             "faceAttributes": {"headPose": {"pitch": 0, "yaw": 0, "roll": 0}}}]
    monkeypatch.setattr(recognition, "detect_faces", lambda b: fake)
    # DeepFace présent (sentinel) mais aucune correspondance -> auto-enrôlement.
    monkeypatch.setattr(recognition, "DeepFace", object())
    monkeypatch.setattr(recognition, "verify_against_references", lambda p: (False, 0.0, None))

    resp = client.post("/analyze-face", json={"image": PIXEL_B64})
    assert resp.status_code == 200
    face = resp.json()["faces"][0]
    assert face["recognized"] is True
    assert face["name"].startswith("Visage ")
    assert face["system_action"] == "Auto-enrôlé"

    refs = client.get("/references").json()["references"]
    assert any(r["name"].startswith("Visage ") and r["auto"] is True for r in refs)


def test_auto_enroll_disabled(client, monkeypatch):
    from config import settings
    monkeypatch.setattr(settings, "AUTO_ENROLL", False)
    fake = [{"faceRectangle": {"top": 0, "left": 0, "width": 1, "height": 1},
             "faceAttributes": {"headPose": {"pitch": 0, "yaw": 0, "roll": 0}}}]
    monkeypatch.setattr(recognition, "detect_faces", lambda b: fake)
    monkeypatch.setattr(recognition, "verify_against_references", lambda p: (False, 0.0, None))
    resp = client.post("/analyze-face", json={"image": PIXEL_B64})
    assert resp.json()["faces"][0]["recognized"] is False


def test_rename_reference(client):
    img = base64.b64decode(PIXEL_B64.split(",", 1)[1])
    ref_id = client.post(
        "/references",
        data={"name": "Visage 1"},
        files={"file": ("v.jpg", io.BytesIO(img), "image/jpeg")},
    ).json()["id"]

    resp = client.patch(f"/references/{ref_id}", json={"name": "Charlie"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Charlie"

    listed = client.get("/references").json()["references"]
    assert any(r["id"] == ref_id and r["name"] == "Charlie" for r in listed)

    # Renommer une référence inexistante -> 404.
    assert client.patch("/references/999999", json={"name": "X"}).status_code == 404


def test_reference_image_endpoint(client):
    img = base64.b64decode(PIXEL_B64.split(",", 1)[1])
    ref_id = client.post(
        "/references",
        data={"name": "Dora"},
        files={"file": ("d.jpg", io.BytesIO(img), "image/jpeg")},
    ).json()["id"]
    resp = client.get(f"/references/{ref_id}/image")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/")
    assert client.get("/references/999999/image").status_code == 404


def test_enroll_and_list_and_delete(client):
    img = base64.b64decode(PIXEL_B64.split(",", 1)[1])
    resp = client.post(
        "/references",
        data={"name": "Bob"},
        files={"file": ("bob.jpg", io.BytesIO(img), "image/jpeg")},
    )
    assert resp.status_code == 200
    ref_id = resp.json()["id"]

    listed = client.get("/references").json()["references"]
    assert any(r["id"] == ref_id for r in listed)
    # image_path (chemin filesystem interne) ne doit jamais fuiter via l'API.
    assert all("image_path" not in r for r in listed)

    deleted = client.delete(f"/references/{ref_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] == ref_id


def test_enroll_rejects_non_image(client):
    resp = client.post(
        "/references",
        data={"name": "Mallory"},
        files={"file": ("evil.jpg", io.BytesIO(b"not an image"), "image/jpeg")},
    )
    assert resp.status_code == 400


def test_analyze_rejects_non_image(client):
    # base64 valide mais contenu non-image -> rejet de format.
    payload = "data:image/jpeg;base64," + base64.b64encode(b"hello world").decode()
    resp = client.post("/analyze-face", json={"image": payload})
    assert resp.status_code == 400


def test_history_limit_is_bounded(client):
    resp = client.get("/history?limit=999999")
    assert resp.status_code == 200
    assert len(resp.json()["events"]) <= 200


def test_history_records_events(client, monkeypatch):
    monkeypatch.setattr(recognition, "detect_faces", lambda b: [])
    client.post("/analyze-face", json={"image": PIXEL_B64})
    resp = client.get("/history")
    assert resp.status_code == 200
    assert "events" in resp.json()


def test_bad_base64(client, monkeypatch):
    fake = [{"faceRectangle": {}, "faceAttributes": {"headPose": {}}}]
    monkeypatch.setattr(recognition, "detect_faces", lambda b: fake)
    resp = client.post("/analyze-face", json={"image": "!!!notbase64!!!"})
    assert resp.status_code == 400


# --- Sprint 1 — Sécurité & conformité ---

def test_security_headers_present(client):
    resp = client.get("/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "no-referrer"
    assert "content-security-policy" in resp.headers


def test_requires_api_key(client, monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "API_KEY", "secret")
    # Sans en-tête -> 401.
    assert client.get("/references").status_code == 401
    # Avec la bonne clé -> 200.
    assert client.get("/references", headers={"x-api-key": "secret"}).status_code == 200


def test_pii_masking(client, monkeypatch, caplog):
    from config import settings

    monkeypatch.setattr(settings, "LOG_MASK_PII", True)
    fake = [{"faceRectangle": {"top": 1, "left": 2, "width": 3, "height": 4},
             "faceAttributes": {"headPose": {"pitch": 0, "yaw": 0, "roll": 0}}}]
    monkeypatch.setattr(recognition, "detect_faces", lambda b: fake)
    monkeypatch.setattr(
        recognition, "verify_against_references",
        lambda path: (True, 0.91, {"id": 1, "name": "Alice"}),
    )
    with caplog.at_level(logging.INFO):
        client.post("/analyze-face", json={"image": PIXEL_B64})
    # Le nom en clair ne doit jamais apparaître dans les logs ; sa forme
    # masquée (première lettre + astérisques) oui.
    assert "Alice" not in caplog.text
    assert "A****" in caplog.text


def test_rate_limit_enforced():
    """Le câblage slowapi renvoie bien un 429 au-delà de la limite."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from slowapi import Limiter
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    app = FastAPI()
    app.state.limiter = Limiter(key_func=get_remote_address, default_limits=["3/minute"])
    app.add_exception_handler(RateLimitExceeded, main._rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    with TestClient(app) as c:
        statuses = [c.get("/ping").status_code for _ in range(6)]
    assert 429 in statuses


# --- Sprint 2 — Fiabilité & résilience ---

def test_azure_retries_then_succeeds(monkeypatch):
    """detect_faces réessaie sur erreur réseau transitoire puis réussit."""
    import requests

    from config import settings

    monkeypatch.setattr(settings, "AZURE_MAX_RETRIES", 2)
    monkeypatch.setattr(settings, "AZURE_BACKOFF_BASE", 0)  # pas d'attente en test
    monkeypatch.setattr(recognition.time, "sleep", lambda s: None)

    calls = {"n": 0}

    class _Resp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return [{"faceRectangle": {}}]

    def fake_post(*a, **k):
        calls["n"] += 1
        if calls["n"] < 3:
            raise requests.ConnectionError("boom")
        return _Resp()

    monkeypatch.setattr(recognition.requests, "post", fake_post)
    result = recognition.detect_faces(b"img")
    assert calls["n"] == 3
    assert result == [{"faceRectangle": {}}]


def test_azure_retries_exhausted(monkeypatch):
    """Après épuisement des tentatives, l'erreur réseau est propagée."""
    import requests

    from config import settings

    monkeypatch.setattr(settings, "AZURE_MAX_RETRIES", 1)
    monkeypatch.setattr(settings, "AZURE_BACKOFF_BASE", 0)
    monkeypatch.setattr(recognition.time, "sleep", lambda s: None)

    def always_fail(*a, **k):
        raise requests.Timeout("slow")

    monkeypatch.setattr(recognition.requests, "post", always_fail)
    try:
        recognition.detect_faces(b"img")
        assert False, "devait lever une exception réseau"
    except requests.RequestException:
        pass


def test_deepface_timeout_skips_reference(monkeypatch, tmp_path):
    """Une vérification DeepFace qui dépasse le délai n'interrompt pas la boucle."""
    import time as _time

    from config import settings

    import types

    ref_img = tmp_path / "ref.jpg"
    ref_img.write_bytes(b"x")
    monkeypatch.setattr(settings, "DEEPFACE_TIMEOUT", 0.2)

    def slow_verify(*a, **k):
        _time.sleep(2)
        return {"verified": True, "distance": 0.1}

    monkeypatch.setattr(recognition, "DeepFace", types.SimpleNamespace(verify=slow_verify))
    monkeypatch.setattr(
        recognition, "list_references_internal",
        lambda: [{"id": 1, "name": "Slow", "image_path": str(ref_img)}],
    )
    recognized, confidence, matched = recognition.verify_against_references("cap.jpg")
    assert recognized is False
    assert matched is None


def test_purge_old_events(client):
    import database

    # Événement ancien (au-delà du TTL) + événement récent.
    with database.get_connection() as conn:
        conn.execute(
            """INSERT INTO recognition_events
               (recognized, confidence, system_action, created_at)
               VALUES (0, 0.0, 'old', '2000-01-01T00:00:00+00:00')"""
        )
    database.log_event(recognized=False, confidence=0.0, system_action="new")

    removed = database.purge_old_events(ttl_days=30, max_rows=0)
    assert removed >= 1
    remaining = [e["system_action"] for e in database.list_events(limit=100)]
    assert "old" not in remaining
    assert "new" in remaining


def test_purge_max_rows_cap(client):
    import database

    for i in range(5):
        database.log_event(recognized=False, confidence=0.0, system_action=f"e{i}")
    database.purge_old_events(ttl_days=0, max_rows=3)
    assert len(database.list_events(limit=100)) <= 3


def test_delete_reference_nulls_event_link(client, monkeypatch):
    import database

    fake = [{"faceRectangle": {"top": 1, "left": 2, "width": 3, "height": 4},
             "faceAttributes": {"headPose": {"pitch": 0, "yaw": 0, "roll": 0}}}]
    monkeypatch.setattr(recognition, "detect_faces", lambda b: fake)
    monkeypatch.setattr(
        recognition, "verify_against_references",
        lambda path: (True, 0.91, {"id": 1, "name": "Alice"}),
    )
    # Crée une vraie référence puis un événement la référençant.
    img = base64.b64decode(PIXEL_B64.split(",", 1)[1])
    ref_id = client.post(
        "/references",
        data={"name": "Eve"},
        files={"file": ("e.jpg", io.BytesIO(img), "image/jpeg")},
    ).json()["id"]
    database.log_event(recognized=True, confidence=0.9, reference_id=ref_id, name="Eve")

    assert client.delete(f"/references/{ref_id}").status_code == 200
    # Aucun événement ne doit encore pointer vers la référence supprimée.
    with database.get_connection() as conn:
        rows = conn.execute(
            "SELECT COUNT(*) AS n FROM recognition_events WHERE reference_id = ?",
            (ref_id,),
        ).fetchone()
    assert rows["n"] == 0
