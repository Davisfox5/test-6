import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app as application


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a test client with a temp data directory."""
    monkeypatch.setattr(application, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(application, "VIDEOS_DIR", str(tmp_path / "videos"))
    monkeypatch.setattr(application, "PROJECTS_FILE", str(tmp_path / "projects.json"))
    os.makedirs(tmp_path / "videos", exist_ok=True)
    application.app.config["TESTING"] = True
    with application.app.test_client() as c:
        yield c


def test_index(client):
    rv = client.get("/")
    assert rv.status_code == 200
    assert b"GameTape" in rv.data


def test_create_and_list_projects(client):
    rv = client.post("/api/projects", json={"name": "Game 1"})
    assert rv.status_code == 201
    data = rv.get_json()
    assert data["name"] == "Game 1"
    assert len(data["tag_types"]) > 0

    rv = client.get("/api/projects")
    assert rv.status_code == 200
    projects = rv.get_json()
    assert len(projects) == 1
    assert projects[0]["name"] == "Game 1"


def test_create_project_requires_name(client):
    rv = client.post("/api/projects", json={"name": ""})
    assert rv.status_code == 400


def test_get_project(client):
    rv = client.post("/api/projects", json={"name": "Game 2"})
    pid = rv.get_json()["id"]
    rv = client.get(f"/api/projects/{pid}")
    assert rv.status_code == 200
    assert rv.get_json()["name"] == "Game 2"


def test_delete_project(client):
    rv = client.post("/api/projects", json={"name": "To Delete"})
    pid = rv.get_json()["id"]
    rv = client.delete(f"/api/projects/{pid}")
    assert rv.status_code == 200
    rv = client.get("/api/projects")
    assert len(rv.get_json()) == 0


def test_create_clip(client):
    rv = client.post("/api/projects", json={"name": "Clip Test"})
    pid = rv.get_json()["id"]

    rv = client.post(f"/api/projects/{pid}/clips", json={
        "tag_type": "Goal",
        "start": 10.0,
        "end": 15.5,
        "label": "Great goal",
        "notes": "Top corner"
    })
    assert rv.status_code == 201
    clip = rv.get_json()
    assert clip["tag_type"] == "Goal"
    assert clip["start"] == 10.0
    assert clip["end"] == 15.5


def test_clip_end_must_be_after_start(client):
    rv = client.post("/api/projects", json={"name": "Bad Clip"})
    pid = rv.get_json()["id"]

    rv = client.post(f"/api/projects/{pid}/clips", json={
        "tag_type": "Shot",
        "start": 20.0,
        "end": 10.0,
    })
    assert rv.status_code == 400


def test_list_clips(client):
    rv = client.post("/api/projects", json={"name": "List Test"})
    pid = rv.get_json()["id"]

    client.post(f"/api/projects/{pid}/clips", json={
        "tag_type": "Pass", "start": 1, "end": 3, "label": "a"
    })
    client.post(f"/api/projects/{pid}/clips", json={
        "tag_type": "Shot", "start": 5, "end": 8, "label": "b"
    })

    rv = client.get(f"/api/projects/{pid}/clips")
    assert len(rv.get_json()) == 2


def test_update_clip(client):
    rv = client.post("/api/projects", json={"name": "Update Test"})
    pid = rv.get_json()["id"]

    rv = client.post(f"/api/projects/{pid}/clips", json={
        "tag_type": "Foul", "start": 30, "end": 35, "label": "orig"
    })
    cid = rv.get_json()["id"]

    rv = client.put(f"/api/projects/{pid}/clips/{cid}", json={"label": "updated"})
    assert rv.status_code == 200
    assert rv.get_json()["label"] == "updated"


def test_delete_clip(client):
    rv = client.post("/api/projects", json={"name": "Del Clip"})
    pid = rv.get_json()["id"]

    rv = client.post(f"/api/projects/{pid}/clips", json={
        "tag_type": "Corner", "start": 40, "end": 45
    })
    cid = rv.get_json()["id"]

    rv = client.delete(f"/api/projects/{pid}/clips/{cid}")
    assert rv.status_code == 200

    rv = client.get(f"/api/projects/{pid}/clips")
    assert len(rv.get_json()) == 0


def test_update_tag_types(client):
    rv = client.post("/api/projects", json={"name": "Tags Test"})
    pid = rv.get_json()["id"]

    new_types = [{"name": "Custom", "color": "#ff0000"}]
    rv = client.put(f"/api/projects/{pid}/tag_types", json={"tag_types": new_types})
    assert rv.status_code == 200
    assert len(rv.get_json()) == 1
    assert rv.get_json()[0]["name"] == "Custom"


def test_project_not_found(client):
    assert client.get("/api/projects/nope").status_code == 404
    assert client.delete("/api/projects/nope").status_code == 404
    assert client.post("/api/projects/nope/clips", json={}).status_code == 404
    assert client.get("/api/projects/nope/clips").status_code == 404


# ── Player Tests ───────────────────────────────────────────────────────

def test_create_and_list_players(client):
    rv = client.post("/api/projects", json={"name": "Player Test"})
    pid = rv.get_json()["id"]

    rv = client.post(f"/api/projects/{pid}/players", json={
        "name": "John Doe", "number": "10"
    })
    assert rv.status_code == 201
    player = rv.get_json()
    assert player["name"] == "John Doe"
    assert player["number"] == "10"
    assert "id" in player

    rv = client.get(f"/api/projects/{pid}/players")
    assert rv.status_code == 200
    assert len(rv.get_json()) == 1


def test_create_player_requires_name(client):
    rv = client.post("/api/projects", json={"name": "P2"})
    pid = rv.get_json()["id"]

    rv = client.post(f"/api/projects/{pid}/players", json={"name": "", "number": "5"})
    assert rv.status_code == 400


def test_update_player(client):
    rv = client.post("/api/projects", json={"name": "P3"})
    pid = rv.get_json()["id"]

    rv = client.post(f"/api/projects/{pid}/players", json={"name": "Alice", "number": "7"})
    player_id = rv.get_json()["id"]

    rv = client.put(f"/api/projects/{pid}/players/{player_id}", json={
        "name": "Alice Smith", "number": "11"
    })
    assert rv.status_code == 200
    assert rv.get_json()["name"] == "Alice Smith"
    assert rv.get_json()["number"] == "11"


def test_delete_player(client):
    rv = client.post("/api/projects", json={"name": "P4"})
    pid = rv.get_json()["id"]

    rv = client.post(f"/api/projects/{pid}/players", json={"name": "Bob", "number": "3"})
    player_id = rv.get_json()["id"]

    rv = client.delete(f"/api/projects/{pid}/players/{player_id}")
    assert rv.status_code == 200

    rv = client.get(f"/api/projects/{pid}/players")
    assert len(rv.get_json()) == 0


def test_clip_with_players(client):
    rv = client.post("/api/projects", json={"name": "Clip Players"})
    pid = rv.get_json()["id"]

    # Add two players
    rv1 = client.post(f"/api/projects/{pid}/players", json={"name": "Player A", "number": "9"})
    rv2 = client.post(f"/api/projects/{pid}/players", json={"name": "Player B", "number": "5"})
    p1_id = rv1.get_json()["id"]
    p2_id = rv2.get_json()["id"]

    # Create clip with both players tagged
    rv = client.post(f"/api/projects/{pid}/clips", json={
        "tag_type": "Goal",
        "start": 10,
        "end": 15,
        "label": "Nice goal",
        "players": [p1_id, p2_id],
    })
    assert rv.status_code == 201
    clip = rv.get_json()
    assert clip["players"] == [p1_id, p2_id]

    # Update clip to only one player
    rv = client.put(f"/api/projects/{pid}/clips/{clip['id']}", json={
        "players": [p1_id],
    })
    assert rv.status_code == 200
    assert rv.get_json()["players"] == [p1_id]


def test_clip_default_empty_players(client):
    rv = client.post("/api/projects", json={"name": "No Players"})
    pid = rv.get_json()["id"]

    rv = client.post(f"/api/projects/{pid}/clips", json={
        "tag_type": "Shot", "start": 1, "end": 5
    })
    assert rv.status_code == 201
    assert rv.get_json()["players"] == []


def test_player_not_found(client):
    rv = client.post("/api/projects", json={"name": "PNF"})
    pid = rv.get_json()["id"]

    rv = client.put(f"/api/projects/{pid}/players/nonexistent", json={"name": "X"})
    assert rv.status_code == 404


# ── Export Tests ───────────────────────────────────────────────────────

def _make_project_with_clips(client):
    """Helper: create a project with players and clips for export tests."""
    rv = client.post("/api/projects", json={"name": "Export Test"})
    pid = rv.get_json()["id"]

    rv1 = client.post(f"/api/projects/{pid}/players", json={"name": "Alice", "number": "10"})
    rv2 = client.post(f"/api/projects/{pid}/players", json={"name": "Bob", "number": "7"})
    p1 = rv1.get_json()["id"]
    p2 = rv2.get_json()["id"]

    client.post(f"/api/projects/{pid}/clips", json={
        "tag_type": "Goal", "start": 10, "end": 15,
        "label": "First goal", "notes": "Header", "players": [p1],
    })
    client.post(f"/api/projects/{pid}/clips", json={
        "tag_type": "Shot", "start": 20, "end": 23,
        "label": "Wide shot", "players": [p2],
    })
    client.post(f"/api/projects/{pid}/clips", json={
        "tag_type": "Goal", "start": 55, "end": 60,
        "label": "Second goal", "players": [p1, p2],
    })
    return pid, p1, p2


def test_export_csv_all_clips(client):
    pid, _, _ = _make_project_with_clips(client)
    rv = client.get(f"/api/projects/{pid}/export/csv")
    assert rv.status_code == 200
    assert rv.content_type.startswith("text/csv")
    text = rv.data.decode("utf-8")
    lines = text.strip().split("\n")
    assert len(lines) == 4  # header + 3 clips
    assert "Goal" in text
    assert "Shot" in text
    assert "Alice" in text


def test_export_csv_filtered_by_tag_type(client):
    pid, _, _ = _make_project_with_clips(client)
    rv = client.get(f"/api/projects/{pid}/export/csv?tag_type=Goal")
    assert rv.status_code == 200
    text = rv.data.decode("utf-8")
    lines = text.strip().split("\n")
    assert len(lines) == 3  # header + 2 Goal clips
    assert "Shot" not in text.split("\n", 1)[1]  # Not in data rows


def test_export_csv_filtered_by_player(client):
    pid, p1, p2 = _make_project_with_clips(client)
    rv = client.get(f"/api/projects/{pid}/export/csv?player={p2}")
    assert rv.status_code == 200
    text = rv.data.decode("utf-8")
    lines = text.strip().split("\n")
    assert len(lines) == 3  # header + 2 clips with Bob


def test_export_csv_filtered_by_search(client):
    pid, _, _ = _make_project_with_clips(client)
    rv = client.get(f"/api/projects/{pid}/export/csv?search=wide")
    assert rv.status_code == 200
    text = rv.data.decode("utf-8")
    lines = text.strip().split("\n")
    assert len(lines) == 2  # header + 1 clip


def test_export_json_all_clips(client):
    pid, _, _ = _make_project_with_clips(client)
    rv = client.get(f"/api/projects/{pid}/export/json")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data["project"] == "Export Test"
    assert data["clip_count"] == 3
    assert len(data["clips"]) == 3
    # Check player info is resolved
    goal_clip = [c for c in data["clips"] if c["label"] == "First goal"][0]
    assert goal_clip["players"][0]["name"] == "Alice"
    assert "duration" in goal_clip


def test_export_json_filtered(client):
    pid, _, _ = _make_project_with_clips(client)
    rv = client.get(f"/api/projects/{pid}/export/json?tag_type=Shot")
    data = json.loads(rv.data)
    assert data["clip_count"] == 1
    assert data["clips"][0]["tag_type"] == "Shot"


def test_export_csv_project_not_found(client):
    rv = client.get("/api/projects/nope/export/csv")
    assert rv.status_code == 404


def test_export_json_project_not_found(client):
    rv = client.get("/api/projects/nope/export/json")
    assert rv.status_code == 404


def test_export_video_no_video(client):
    rv = client.post("/api/projects", json={"name": "No Video"})
    pid = rv.get_json()["id"]
    client.post(f"/api/projects/{pid}/clips", json={
        "tag_type": "Goal", "start": 1, "end": 5
    })
    rv = client.post(f"/api/projects/{pid}/export/video", json={})
    assert rv.status_code == 400
    assert "No video" in rv.get_json()["error"]


def test_export_video_no_matching_clips(client, tmp_path):
    rv = client.post("/api/projects", json={"name": "Empty Export"})
    pid = rv.get_json()["id"]
    # Create a dummy video file so the file-exists check passes
    import app as application
    video_path = os.path.join(str(tmp_path), "videos", f"{pid}.mp4")
    with open(video_path, "wb") as f:
        f.write(b"fake")
    projects = application._load_projects()
    projects[pid]["video_filename"] = f"{pid}.mp4"
    application._save_projects(projects)

    rv = client.post(f"/api/projects/{pid}/export/video", json={"tag_type": "Nonexistent"})
    assert rv.status_code == 400
    assert "No clips" in rv.get_json()["error"]


# ── Annotation Tests ──────────────────────────────────────────────────

def _make_project_with_clip(client):
    """Helper: create a project with one clip for annotation tests."""
    rv = client.post("/api/projects", json={"name": "Ann Test"})
    pid = rv.get_json()["id"]
    rv = client.post(f"/api/projects/{pid}/clips", json={
        "tag_type": "Goal", "start": 10, "end": 20, "label": "Test clip"
    })
    cid = rv.get_json()["id"]
    return pid, cid


def test_create_and_list_annotations(client):
    pid, cid = _make_project_with_clip(client)

    rv = client.post(f"/api/projects/{pid}/clips/{cid}/annotations", json={
        "type": "arrow",
        "color": "#ff0000",
        "lineWidth": 3,
        "startTime": 10,
        "endTime": 15,
        "data": {"x1": 0.1, "y1": 0.2, "x2": 0.5, "y2": 0.6},
    })
    assert rv.status_code == 201
    ann = rv.get_json()
    assert ann["type"] == "arrow"
    assert ann["color"] == "#ff0000"
    assert ann["data"]["x1"] == 0.1
    assert "id" in ann

    rv = client.get(f"/api/projects/{pid}/clips/{cid}/annotations")
    assert rv.status_code == 200
    assert len(rv.get_json()) == 1


def test_create_multiple_annotation_types(client):
    pid, cid = _make_project_with_clip(client)

    types_data = [
        {"type": "arrow", "data": {"x1": 0.1, "y1": 0.2, "x2": 0.5, "y2": 0.6}},
        {"type": "rect", "data": {"x1": 0.2, "y1": 0.3, "x2": 0.7, "y2": 0.8}},
        {"type": "circle", "data": {"cx": 0.5, "cy": 0.5, "rx": 0.1, "ry": 0.1}},
        {"type": "freehand", "data": {"points": [{"x": 0.1, "y": 0.1}, {"x": 0.3, "y": 0.4}]}},
        {"type": "text", "data": {"x": 0.5, "y": 0.5, "text": "Nice play!"}},
    ]
    for td in types_data:
        rv = client.post(f"/api/projects/{pid}/clips/{cid}/annotations", json={
            **td, "color": "#00ff00", "lineWidth": 2, "startTime": 10, "endTime": 15,
        })
        assert rv.status_code == 201, f"Failed for type {td['type']}"

    rv = client.get(f"/api/projects/{pid}/clips/{cid}/annotations")
    assert len(rv.get_json()) == 5


def test_invalid_annotation_type(client):
    pid, cid = _make_project_with_clip(client)
    rv = client.post(f"/api/projects/{pid}/clips/{cid}/annotations", json={
        "type": "invalid", "data": {}
    })
    assert rv.status_code == 400


def test_update_annotation(client):
    pid, cid = _make_project_with_clip(client)

    rv = client.post(f"/api/projects/{pid}/clips/{cid}/annotations", json={
        "type": "rect", "color": "#ff0000", "lineWidth": 3,
        "startTime": 10, "endTime": 15,
        "data": {"x1": 0.1, "y1": 0.2, "x2": 0.5, "y2": 0.6},
    })
    aid = rv.get_json()["id"]

    rv = client.put(f"/api/projects/{pid}/clips/{cid}/annotations/{aid}", json={
        "color": "#00ff00",
        "endTime": 18,
    })
    assert rv.status_code == 200
    assert rv.get_json()["color"] == "#00ff00"
    assert rv.get_json()["endTime"] == 18


def test_delete_annotation(client):
    pid, cid = _make_project_with_clip(client)

    rv = client.post(f"/api/projects/{pid}/clips/{cid}/annotations", json={
        "type": "circle", "data": {"cx": 0.5, "cy": 0.5, "rx": 0.1, "ry": 0.1},
        "startTime": 10, "endTime": 15,
    })
    aid = rv.get_json()["id"]

    rv = client.delete(f"/api/projects/{pid}/clips/{cid}/annotations/{aid}")
    assert rv.status_code == 200

    rv = client.get(f"/api/projects/{pid}/clips/{cid}/annotations")
    assert len(rv.get_json()) == 0


def test_clear_all_annotations(client):
    pid, cid = _make_project_with_clip(client)

    for i in range(3):
        client.post(f"/api/projects/{pid}/clips/{cid}/annotations", json={
            "type": "arrow", "data": {"x1": 0.1, "y1": 0.1, "x2": 0.5, "y2": 0.5},
            "startTime": 10, "endTime": 15,
        })

    rv = client.get(f"/api/projects/{pid}/clips/{cid}/annotations")
    assert len(rv.get_json()) == 3

    rv = client.delete(f"/api/projects/{pid}/clips/{cid}/annotations")
    assert rv.status_code == 200

    rv = client.get(f"/api/projects/{pid}/clips/{cid}/annotations")
    assert len(rv.get_json()) == 0


def test_annotation_not_found(client):
    pid, cid = _make_project_with_clip(client)
    rv = client.put(f"/api/projects/{pid}/clips/{cid}/annotations/nope", json={})
    assert rv.status_code == 404


def test_annotation_clip_not_found(client):
    rv = client.post("/api/projects", json={"name": "Ann404"})
    pid = rv.get_json()["id"]
    rv = client.get(f"/api/projects/{pid}/clips/nope/annotations")
    assert rv.status_code == 404
    rv = client.post(f"/api/projects/{pid}/clips/nope/annotations", json={
        "type": "arrow", "data": {}
    })
    assert rv.status_code == 404


def test_annotation_defaults(client):
    pid, cid = _make_project_with_clip(client)
    rv = client.post(f"/api/projects/{pid}/clips/{cid}/annotations", json={
        "type": "arrow", "data": {"x1": 0, "y1": 0, "x2": 1, "y2": 1},
    })
    assert rv.status_code == 201
    ann = rv.get_json()
    # Should default startTime to clip start (10) and endTime to clip end (20)
    assert ann["startTime"] == 10
    assert ann["endTime"] == 20
    assert ann["color"] == "#ff0000"
    assert ann["lineWidth"] == 3


# ── Recording Tests ───────────────────────────────────────────────────

def test_upload_and_list_recordings(client, tmp_path):
    pid, cid = _make_project_with_clip(client)

    # Upload a fake recording
    from io import BytesIO
    data = {
        "recording": (BytesIO(b"fake webm data"), "test_recording.webm"),
    }
    rv = client.post(
        f"/api/projects/{pid}/clips/{cid}/recordings",
        data=data,
        content_type="multipart/form-data",
    )
    assert rv.status_code == 201
    rec = rv.get_json()
    assert "id" in rec
    assert rec["filename"].endswith(".webm")

    # List recordings
    rv = client.get(f"/api/projects/{pid}/clips/{cid}/recordings")
    assert rv.status_code == 200
    recs = rv.get_json()
    assert len(recs) == 1
    assert recs[0]["id"] == rec["id"]


def test_upload_recording_with_duration(client, tmp_path):
    pid, cid = _make_project_with_clip(client)

    from io import BytesIO
    data = {
        "recording": (BytesIO(b"fake"), "rec.webm"),
        "duration": "45",
    }
    rv = client.post(
        f"/api/projects/{pid}/clips/{cid}/recordings",
        data=data,
        content_type="multipart/form-data",
    )
    assert rv.status_code == 201
    assert rv.get_json()["duration"] == "45"


def test_upload_recording_no_file(client):
    pid, cid = _make_project_with_clip(client)
    rv = client.post(f"/api/projects/{pid}/clips/{cid}/recordings",
                     data={}, content_type="multipart/form-data")
    assert rv.status_code == 400


def test_delete_recording(client, tmp_path):
    pid, cid = _make_project_with_clip(client)

    from io import BytesIO
    rv = client.post(
        f"/api/projects/{pid}/clips/{cid}/recordings",
        data={"recording": (BytesIO(b"data"), "rec.webm")},
        content_type="multipart/form-data",
    )
    rec_id = rv.get_json()["id"]

    rv = client.delete(f"/api/projects/{pid}/clips/{cid}/recordings/{rec_id}")
    assert rv.status_code == 200

    rv = client.get(f"/api/projects/{pid}/clips/{cid}/recordings")
    assert len(rv.get_json()) == 0


def test_delete_recording_not_found(client):
    pid, cid = _make_project_with_clip(client)
    rv = client.delete(f"/api/projects/{pid}/clips/{cid}/recordings/nope")
    assert rv.status_code == 404


def test_serve_recording(client, tmp_path):
    pid, cid = _make_project_with_clip(client)

    from io import BytesIO
    content = b"fake webm content here"
    rv = client.post(
        f"/api/projects/{pid}/clips/{cid}/recordings",
        data={"recording": (BytesIO(content), "rec.webm")},
        content_type="multipart/form-data",
    )
    filename = rv.get_json()["filename"]

    rv = client.get(f"/recordings/{filename}")
    assert rv.status_code == 200
    assert rv.data == content


def test_recording_clip_not_found(client):
    rv = client.post("/api/projects", json={"name": "Rec404"})
    pid = rv.get_json()["id"]
    rv = client.get(f"/api/projects/{pid}/clips/nope/recordings")
    assert rv.status_code == 404

    from io import BytesIO
    rv = client.post(
        f"/api/projects/{pid}/clips/nope/recordings",
        data={"recording": (BytesIO(b"x"), "r.webm")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 404


def test_clip_includes_recordings_field(client):
    """New clips should have an empty recordings array."""
    rv = client.post("/api/projects", json={"name": "RecField"})
    pid = rv.get_json()["id"]
    rv = client.post(f"/api/projects/{pid}/clips", json={
        "tag_type": "Goal", "start": 1, "end": 5
    })
    clip = rv.get_json()
    assert "recordings" in clip
    assert clip["recordings"] == []


# ── Roster Import Tests ───────────────────────────────────────────────

def test_import_roster_csv(client):
    rv = client.post("/api/projects", json={"name": "CSV Import"})
    pid = rv.get_json()["id"]

    from io import BytesIO
    csv_data = b"Name,Number\nAlice Smith,10\nBob Jones,7\nCharlie Brown,3\n"
    rv = client.post(
        f"/api/projects/{pid}/players/import",
        data={"file": (BytesIO(csv_data), "roster.csv")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 201
    data = rv.get_json()
    assert data["imported"] == 3
    assert data["players"][0]["name"] == "Alice Smith"
    assert data["players"][0]["number"] == "10"
    assert data["players"][2]["name"] == "Charlie Brown"

    # Verify they show up in the player list
    rv = client.get(f"/api/projects/{pid}/players")
    assert len(rv.get_json()) == 3


def test_import_roster_csv_auto_detect_columns(client):
    """Headers with different names should still be detected."""
    rv = client.post("/api/projects", json={"name": "AutoDetect"})
    pid = rv.get_json()["id"]

    from io import BytesIO
    csv_data = b"Jersey #,Player Name\n22,Jane Doe\n5,John Doe\n"
    rv = client.post(
        f"/api/projects/{pid}/players/import",
        data={"file": (BytesIO(csv_data), "roster.csv")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 201
    data = rv.get_json()
    assert data["imported"] == 2
    assert data["players"][0]["name"] == "Jane Doe"
    assert data["players"][0]["number"] == "22"


def test_import_roster_csv_no_header(client):
    """When no header matches, fall back to col A=name, col B=number."""
    rv = client.post("/api/projects", json={"name": "NoHeader"})
    pid = rv.get_json()["id"]

    from io import BytesIO
    csv_data = b"Alice,10\nBob,7\n"
    rv = client.post(
        f"/api/projects/{pid}/players/import",
        data={"file": (BytesIO(csv_data), "roster.csv")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 201
    data = rv.get_json()
    assert data["imported"] == 2
    assert data["players"][0]["name"] == "Alice"
    assert data["players"][0]["number"] == "10"


def test_import_roster_xlsx(client):
    import openpyxl
    from io import BytesIO

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Name", "Number"])
    ws.append(["Player One", 9])
    ws.append(["Player Two", 14])
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    rv = client.post("/api/projects", json={"name": "XLSX Import"})
    pid = rv.get_json()["id"]

    rv = client.post(
        f"/api/projects/{pid}/players/import",
        data={"file": (buf, "roster.xlsx")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 201
    data = rv.get_json()
    assert data["imported"] == 2
    assert data["players"][0]["name"] == "Player One"
    assert data["players"][0]["number"] == "9"  # cleaned from 9.0


def test_import_roster_skips_empty_rows(client):
    from io import BytesIO
    csv_data = b"Name,Number\nAlice,10\n,,\n,\nBob,7\n"
    rv = client.post("/api/projects", json={"name": "SkipEmpty"})
    pid = rv.get_json()["id"]

    rv = client.post(
        f"/api/projects/{pid}/players/import",
        data={"file": (BytesIO(csv_data), "roster.csv")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 201
    assert rv.get_json()["imported"] == 2


def test_import_roster_no_file(client):
    rv = client.post("/api/projects", json={"name": "NoFile"})
    pid = rv.get_json()["id"]
    rv = client.post(f"/api/projects/{pid}/players/import",
                     data={}, content_type="multipart/form-data")
    assert rv.status_code == 400


def test_import_roster_unsupported_type(client):
    from io import BytesIO
    rv = client.post("/api/projects", json={"name": "BadType"})
    pid = rv.get_json()["id"]
    rv = client.post(
        f"/api/projects/{pid}/players/import",
        data={"file": (BytesIO(b"data"), "roster.pdf")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 400
    assert "Unsupported" in rv.get_json()["error"]


def test_import_roster_appends_to_existing(client):
    """Imported players should be added to existing roster, not replace it."""
    rv = client.post("/api/projects", json={"name": "Append"})
    pid = rv.get_json()["id"]

    # Add one player manually first
    client.post(f"/api/projects/{pid}/players", json={"name": "Existing", "number": "1"})

    from io import BytesIO
    csv_data = b"Name,Number\nNew Player,99\n"
    client.post(
        f"/api/projects/{pid}/players/import",
        data={"file": (BytesIO(csv_data), "roster.csv")},
        content_type="multipart/form-data",
    )

    rv = client.get(f"/api/projects/{pid}/players")
    assert len(rv.get_json()) == 2


# ── Deduplication Tests ───────────────────────────────────────────────

def test_manual_add_duplicate_rejected(client):
    """Adding a player with the same name and number should return 409."""
    rv = client.post("/api/projects", json={"name": "Dedup Manual"})
    pid = rv.get_json()["id"]

    rv = client.post(f"/api/projects/{pid}/players", json={"name": "Alice", "number": "10"})
    assert rv.status_code == 201

    rv = client.post(f"/api/projects/{pid}/players", json={"name": "Alice", "number": "10"})
    assert rv.status_code == 409
    assert "already exists" in rv.get_json()["error"]

    rv = client.get(f"/api/projects/{pid}/players")
    assert len(rv.get_json()) == 1


def test_manual_add_case_insensitive_duplicate(client):
    """Dedup should be case-insensitive on name."""
    rv = client.post("/api/projects", json={"name": "Dedup Case"})
    pid = rv.get_json()["id"]

    client.post(f"/api/projects/{pid}/players", json={"name": "Bob Jones", "number": "7"})
    rv = client.post(f"/api/projects/{pid}/players", json={"name": "bob jones", "number": "7"})
    assert rv.status_code == 409

    rv = client.get(f"/api/projects/{pid}/players")
    assert len(rv.get_json()) == 1


def test_manual_add_same_name_different_number_allowed(client):
    """Same name but different number should be allowed (e.g., traded player)."""
    rv = client.post("/api/projects", json={"name": "Dedup Diff Num"})
    pid = rv.get_json()["id"]

    rv = client.post(f"/api/projects/{pid}/players", json={"name": "Alice", "number": "10"})
    assert rv.status_code == 201
    rv = client.post(f"/api/projects/{pid}/players", json={"name": "Alice", "number": "22"})
    assert rv.status_code == 201

    rv = client.get(f"/api/projects/{pid}/players")
    assert len(rv.get_json()) == 2


def test_import_skips_duplicates_against_existing(client):
    """Import should skip players already in the roster."""
    rv = client.post("/api/projects", json={"name": "Import Dedup"})
    pid = rv.get_json()["id"]

    # Add existing players
    client.post(f"/api/projects/{pid}/players", json={"name": "Alice", "number": "10"})
    client.post(f"/api/projects/{pid}/players", json={"name": "Bob", "number": "7"})

    from io import BytesIO
    csv_data = b"Name,Number\nAlice,10\nCharlie,3\nBob,7\nDiana,5\n"
    rv = client.post(
        f"/api/projects/{pid}/players/import",
        data={"file": (BytesIO(csv_data), "roster.csv")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 201
    data = rv.get_json()
    assert data["imported"] == 2
    assert data["skipped"] == 2
    names = [p["name"] for p in data["players"]]
    assert "Charlie" in names
    assert "Diana" in names
    assert "Alice" not in names

    rv = client.get(f"/api/projects/{pid}/players")
    assert len(rv.get_json()) == 4


def test_import_skips_duplicates_within_file(client):
    """If the same player appears twice in the import file, only add once."""
    rv = client.post("/api/projects", json={"name": "File Dedup"})
    pid = rv.get_json()["id"]

    from io import BytesIO
    csv_data = b"Name,Number\nAlice,10\nBob,7\nAlice,10\n"
    rv = client.post(
        f"/api/projects/{pid}/players/import",
        data={"file": (BytesIO(csv_data), "roster.csv")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 201
    data = rv.get_json()
    assert data["imported"] == 2
    assert data["skipped"] == 1

    rv = client.get(f"/api/projects/{pid}/players")
    assert len(rv.get_json()) == 2


def test_import_case_insensitive_dedup(client):
    """Import dedup should be case-insensitive."""
    rv = client.post("/api/projects", json={"name": "Case Import"})
    pid = rv.get_json()["id"]

    client.post(f"/api/projects/{pid}/players", json={"name": "Alice Smith", "number": "10"})

    from io import BytesIO
    csv_data = b"Name,Number\nalice smith,10\nBob,7\n"
    rv = client.post(
        f"/api/projects/{pid}/players/import",
        data={"file": (BytesIO(csv_data), "roster.csv")},
        content_type="multipart/form-data",
    )
    data = rv.get_json()
    assert data["imported"] == 1
    assert data["skipped"] == 1
