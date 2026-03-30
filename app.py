#!/usr/bin/env python3
"""
Sports Video Tagging App - A lightweight clone of SportsCode.
Tag clips in game footage, categorize them, and filter/review by type.
"""

import os
import io
import csv
import json
import uuid
import subprocess
import tempfile
from flask import Flask, jsonify, request, send_from_directory, send_file, render_template

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


# ── Annotations CRUD ──────────────────────────────────────────────────

@app.route("/api/projects/<project_id>/clips/<clip_id>/annotations", methods=["GET"])
def list_annotations(project_id, clip_id):
    projects = _load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404
    for clip in projects[project_id]["clips"]:
        if clip["id"] == clip_id:
            return jsonify(clip.get("annotations", []))
    return jsonify({"error": "Clip not found"}), 404


@app.route("/api/projects/<project_id>/clips/<clip_id>/annotations", methods=["POST"])
def create_annotation(project_id, clip_id):
    projects = _load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404

    for clip in projects[project_id]["clips"]:
        if clip["id"] == clip_id:
            data = request.json
            ann = {
                "id": str(uuid.uuid4())[:8],
                "type": data.get("type", ""),       # arrow, rect, circle, freehand, text
                "color": data.get("color", "#ff0000"),
                "lineWidth": data.get("lineWidth", 3),
                "startTime": data.get("startTime", clip["start"]),
                "endTime": data.get("endTime", clip["end"]),
                "data": data.get("data", {}),        # shape-specific coords (normalized 0-1)
            }
            if ann["type"] not in ("arrow", "rect", "circle", "freehand", "text"):
                return jsonify({"error": "Invalid annotation type"}), 400
            if "annotations" not in clip:
                clip["annotations"] = []
            clip["annotations"].append(ann)
            _save_projects(projects)
            return jsonify(ann), 201
    return jsonify({"error": "Clip not found"}), 404


@app.route("/api/projects/<project_id>/clips/<clip_id>/annotations/<ann_id>", methods=["PUT"])
def update_annotation(project_id, clip_id, ann_id):
    projects = _load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404

    for clip in projects[project_id]["clips"]:
        if clip["id"] == clip_id:
            for ann in clip.get("annotations", []):
                if ann["id"] == ann_id:
                    data = request.json
                    ann["color"] = data.get("color", ann["color"])
                    ann["lineWidth"] = data.get("lineWidth", ann["lineWidth"])
                    ann["startTime"] = data.get("startTime", ann["startTime"])
                    ann["endTime"] = data.get("endTime", ann["endTime"])
                    ann["data"] = data.get("data", ann["data"])
                    _save_projects(projects)
                    return jsonify(ann)
            return jsonify({"error": "Annotation not found"}), 404
    return jsonify({"error": "Clip not found"}), 404


@app.route("/api/projects/<project_id>/clips/<clip_id>/annotations/<ann_id>", methods=["DELETE"])
def delete_annotation(project_id, clip_id, ann_id):
    projects = _load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404

    for clip in projects[project_id]["clips"]:
        if clip["id"] == clip_id:
            anns = clip.get("annotations", [])
            clip["annotations"] = [a for a in anns if a["id"] != ann_id]
            _save_projects(projects)
            return jsonify({"ok": True})
    return jsonify({"error": "Clip not found"}), 404


@app.route("/api/projects/<project_id>/clips/<clip_id>/annotations", methods=["DELETE"])
def clear_annotations(project_id, clip_id):
    projects = _load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404

    for clip in projects[project_id]["clips"]:
        if clip["id"] == clip_id:
            clip["annotations"] = []
            _save_projects(projects)
            return jsonify({"ok": True})
    return jsonify({"error": "Clip not found"}), 404


# ── Export ─────────────────────────────────────────────────────────────

def _filter_clips(project, params):
    """Filter clips by tag_type, player, and search query string."""
    clips = list(project["clips"])
    tag_type = params.get("tag_type", "")
    player = params.get("player", "")
    search = params.get("search", "").lower()
    clip_ids = params.get("clip_ids", "")

    if clip_ids:
        id_set = set(clip_ids.split(","))
        clips = [c for c in clips if c["id"] in id_set]
    if tag_type:
        clips = [c for c in clips if c["tag_type"] == tag_type]
    if player:
        clips = [c for c in clips if player in c.get("players", [])]
    if search:
        clips = [c for c in clips if
                 search in c.get("label", "").lower() or
                 search in c.get("notes", "").lower() or
                 search in c.get("tag_type", "").lower()]

    clips.sort(key=lambda c: c["start"])
    return clips


@app.route("/api/projects/<project_id>/export/csv")
def export_csv(project_id):
    projects = _load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404

    project = projects[project_id]
    clips = _filter_clips(project, request.args)
    players_map = {p["id"]: p for p in project.get("players", [])}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Clip ID", "Tag Type", "Start (s)", "End (s)",
                      "Duration (s)", "Label", "Notes", "Players"])

    for c in clips:
        player_names = []
        for pid in c.get("players", []):
            p = players_map.get(pid)
            if p:
                player_names.append(f"#{p['number']} {p['name']}" if p.get("number") else p["name"])
        writer.writerow([
            c["id"],
            c["tag_type"],
            round(c["start"], 2),
            round(c["end"], 2),
            round(c["end"] - c["start"], 2),
            c.get("label", ""),
            c.get("notes", ""),
            "; ".join(player_names),
        ])

    output.seek(0)
    safe_name = project["name"].replace(" ", "_")
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"{safe_name}_clips.csv",
    )


@app.route("/api/projects/<project_id>/export/json")
def export_json(project_id):
    projects = _load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404

    project = projects[project_id]
    clips = _filter_clips(project, request.args)
    players_map = {p["id"]: p for p in project.get("players", [])}

    export_clips = []
    for c in clips:
        player_names = []
        for pid in c.get("players", []):
            p = players_map.get(pid)
            if p:
                player_names.append({"id": p["id"], "name": p["name"], "number": p.get("number", "")})
        export_clips.append({
            "id": c["id"],
            "tag_type": c["tag_type"],
            "start": round(c["start"], 2),
            "end": round(c["end"], 2),
            "duration": round(c["end"] - c["start"], 2),
            "label": c.get("label", ""),
            "notes": c.get("notes", ""),
            "players": player_names,
        })

    payload = json.dumps({
        "project": project["name"],
        "clip_count": len(export_clips),
        "clips": export_clips,
    }, indent=2)

    safe_name = project["name"].replace(" ", "_")
    return send_file(
        io.BytesIO(payload.encode("utf-8")),
        mimetype="application/json",
        as_attachment=True,
        download_name=f"{safe_name}_clips.json",
    )


@app.route("/api/projects/<project_id>/export/video", methods=["POST"])
def export_video(project_id):
    projects = _load_projects()
    if project_id not in projects:
        return jsonify({"error": "Project not found"}), 404

    project = projects[project_id]
    if not project.get("video_filename"):
        return jsonify({"error": "No video uploaded for this project"}), 400

    video_path = os.path.join(VIDEOS_DIR, project["video_filename"])
    if not os.path.exists(video_path):
        return jsonify({"error": "Video file not found on disk"}), 404

    params = request.json or {}
    clips = _filter_clips(project, params)

    if not clips:
        return jsonify({"error": "No clips match the current filters"}), 400

    try:
        tmpdir = tempfile.mkdtemp()
        segment_files = []

        # Cut each clip segment
        for i, c in enumerate(clips):
            seg_path = os.path.join(tmpdir, f"seg_{i:04d}.mp4")
            duration = c["end"] - c["start"]
            result = subprocess.run([
                "ffmpeg", "-y",
                "-ss", str(c["start"]),
                "-i", video_path,
                "-t", str(duration),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-movflags", "+faststart",
                "-avoid_negative_ts", "make_zero",
                seg_path,
            ], capture_output=True, timeout=120)
            if result.returncode != 0:
                return jsonify({"error": f"ffmpeg segment cut failed: {result.stderr.decode()[-200:]}"}), 500
            segment_files.append(seg_path)

        # Build concat list
        concat_list_path = os.path.join(tmpdir, "concat.txt")
        with open(concat_list_path, "w") as f:
            for seg in segment_files:
                f.write(f"file '{seg}'\n")

        # Concatenate
        output_path = os.path.join(tmpdir, "export.mp4")
        result = subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            "-movflags", "+faststart",
            output_path,
        ], capture_output=True, timeout=300)
        if result.returncode != 0:
            return jsonify({"error": f"ffmpeg concat failed: {result.stderr.decode()[-200:]}"}), 500

        safe_name = project["name"].replace(" ", "_")
        return send_file(
            output_path,
            mimetype="video/mp4",
            as_attachment=True,
            download_name=f"{safe_name}_playlist.mp4",
        )
    except FileNotFoundError:
        return jsonify({"error": "ffmpeg not found. Install ffmpeg to export video compilations."}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Video export timed out"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
