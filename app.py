#!/usr/bin/env python3
"""
Sports Video Tagging App - A lightweight clone of SportsCode.
Tag clips in game footage, categorize them, and filter/review by type.
"""

import os
import json
import uuid
from flask import Flask, jsonify, request, send_from_directory, render_template

app = Flask(__name__, static_folder="static", template_folder="templates")

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
VIDEOS_DIR = os.path.join(DATA_DIR, "videos")
PROJECTS_FILE = os.path.join(DATA_DIR, "projects.json")

os.makedirs(VIDEOS_DIR, exist_ok=True)


def _load_projects():
    if os.path.exists(PROJECTS_FILE):
        with open(PROJECTS_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_projects(projects):
    with open(PROJECTS_FILE, "w") as f:
        json.dump(projects, f, indent=2)


# ── Pages ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── Project CRUD ───────────────────────────────────────────────────────────

@app.route("/api/projects", methods=["GET"])
def list_projects():
    projects = _load_projects()
    return jsonify(list(projects.values()))


@app.route("/api/projects", methods=["POST"])
def create_project():
    data = request.json
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Project name is required"}), 400

    projects = _load_projects()
    project_id = str(uuid.uuid4())[:8]
    projects[project_id] = {
        "id": project_id,
        "name": name,
        "video_filename": None,
        "tag_types": [
            {"name": "Goal", "color": "#e74c3c"},
            {"name": "Shot", "color": "#3498db"},
            {"name": "Pass", "color": "#2ecc71"},
            {"name": "Foul", "color": "#f39c12"},
            {"name": "Corner", "color": "#9b59b6"},
            {"name": "Free Kick", "color": "#1abc9c"},
            {"name": "Turnover", "color": "#e67e22"},
            {"name": "Save", "color": "#34495e"},
        ],
        "players": [],
        "clips": [],
    }
    _save_projects(projects)
    return jsonify(projects[project_id]), 201


@app.route("/api/projects/<project_id>", methods=["GET"])
def get_project(project_id):
    projects = _load_projects()
    project = projects.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    return jsonify(project)


@app.route("/api/projects/<project_id>", methods=["DELETE"])
def delete_project(project_id):
    projects = _load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404
    # Remove associated video file
    proj = projects[project_id]
    if proj.get("video_filename"):
        path = os.path.join(VIDEOS_DIR, proj["video_filename"])
        if os.path.exists(path):
            os.remove(path)
    del projects[project_id]
    _save_projects(projects)
    return jsonify({"ok": True})


# ── Video upload ───────────────────────────────────────────────────────────

@app.route("/api/projects/<project_id>/video", methods=["POST"])
def upload_video(project_id):
    projects = _load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404

    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    video = request.files["video"]
    ext = os.path.splitext(video.filename)[1].lower()
    if ext not in (".mp4", ".webm", ".mov", ".mkv", ".avi"):
        return jsonify({"error": "Unsupported video format"}), 400

    filename = f"{project_id}{ext}"
    video.save(os.path.join(VIDEOS_DIR, filename))
    projects[project_id]["video_filename"] = filename
    _save_projects(projects)
    return jsonify({"filename": filename})


@app.route("/videos/<filename>")
def serve_video(filename):
    return send_from_directory(VIDEOS_DIR, filename)


# ── Tag types ──────────────────────────────────────────────────────────────

@app.route("/api/projects/<project_id>/tag_types", methods=["PUT"])
def update_tag_types(project_id):
    projects = _load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404
    tag_types = request.json.get("tag_types", [])
    projects[project_id]["tag_types"] = tag_types
    _save_projects(projects)
    return jsonify(tag_types)


# ── Players CRUD ──────────────────────────────────────────────────────

@app.route("/api/projects/<project_id>/players", methods=["GET"])
def list_players(project_id):
    projects = _load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404
    return jsonify(projects[project_id].get("players", []))


@app.route("/api/projects/<project_id>/players", methods=["POST"])
def create_player(project_id):
    projects = _load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404

    data = request.json
    name = data.get("name", "").strip()
    number = data.get("number", "").strip()
    if not name:
        return jsonify({"error": "Player name is required"}), 400

    player = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "number": number,
    }

    if "players" not in projects[project_id]:
        projects[project_id]["players"] = []
    projects[project_id]["players"].append(player)
    _save_projects(projects)
    return jsonify(player), 201


@app.route("/api/projects/<project_id>/players/<player_id>", methods=["PUT"])
def update_player(project_id, player_id):
    projects = _load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404

    data = request.json
    for player in projects[project_id].get("players", []):
        if player["id"] == player_id:
            player["name"] = data.get("name", player["name"]).strip()
            player["number"] = data.get("number", player["number"]).strip()
            _save_projects(projects)
            return jsonify(player)
    return jsonify({"error": "Player not found"}), 404


@app.route("/api/projects/<project_id>/players/<player_id>", methods=["DELETE"])
def delete_player(project_id, player_id):
    projects = _load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404

    players = projects[project_id].get("players", [])
    projects[project_id]["players"] = [p for p in players if p["id"] != player_id]
    _save_projects(projects)
    return jsonify({"ok": True})


# ── Clips CRUD ─────────────────────────────────────────────────────────────

@app.route("/api/projects/<project_id>/clips", methods=["GET"])
def list_clips(project_id):
    projects = _load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404
    return jsonify(projects[project_id]["clips"])


@app.route("/api/projects/<project_id>/clips", methods=["POST"])
def create_clip(project_id):
    projects = _load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404

    data = request.json
    clip = {
        "id": str(uuid.uuid4())[:8],
        "tag_type": data.get("tag_type", ""),
        "start": data.get("start", 0),
        "end": data.get("end", 0),
        "label": data.get("label", ""),
        "notes": data.get("notes", ""),
        "players": data.get("players", []),
    }

    if clip["end"] <= clip["start"]:
        return jsonify({"error": "End time must be after start time"}), 400

    projects[project_id]["clips"].append(clip)
    _save_projects(projects)
    return jsonify(clip), 201


@app.route("/api/projects/<project_id>/clips/<clip_id>", methods=["PUT"])
def update_clip(project_id, clip_id):
    projects = _load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404

    data = request.json
    for clip in projects[project_id]["clips"]:
        if clip["id"] == clip_id:
            clip["tag_type"] = data.get("tag_type", clip["tag_type"])
            clip["start"] = data.get("start", clip["start"])
            clip["end"] = data.get("end", clip["end"])
            clip["label"] = data.get("label", clip["label"])
            clip["notes"] = data.get("notes", clip["notes"])
            clip["players"] = data.get("players", clip.get("players", []))
            _save_projects(projects)
            return jsonify(clip)
    return jsonify({"error": "Clip not found"}), 404


@app.route("/api/projects/<project_id>/clips/<clip_id>", methods=["DELETE"])
def delete_clip(project_id, clip_id):
    projects = _load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404

    clips = projects[project_id]["clips"]
    projects[project_id]["clips"] = [c for c in clips if c["id"] != clip_id]
    _save_projects(projects)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
