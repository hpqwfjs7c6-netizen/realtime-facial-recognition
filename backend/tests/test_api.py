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

    deleted = client.delete(f"/references/{ref_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] == ref_id


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
