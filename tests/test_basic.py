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
