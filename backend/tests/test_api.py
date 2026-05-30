import base64
import io

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
