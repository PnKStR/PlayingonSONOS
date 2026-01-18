#!/usr/bin/env python3
from flask import Flask, render_template, redirect, url_for, jsonify, request, session
import requests
import json
import os

app = Flask(__name__)
app.secret_key = "change_this_secret_key"

BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

CONFIG = load_config()
SERVER = CONFIG["server"]
ROOMS = CONFIG["rooms"]
DEBUG = CONFIG.get("debug", False)

DISPLAY_WIDTH = CONFIG.get("display_width", 720)
DISPLAY_HEIGHT = CONFIG.get("display_height", 720)
COVER_SIZE = int(min(DISPLAY_WIDTH, DISPLAY_HEIGHT) * 0.5)

APPINFO_PATH = os.path.join(BASE_DIR, "appinfo.json")
if os.path.exists(APPINFO_PATH):
    with open(APPINFO_PATH, "r", encoding="utf-8") as f:
        APPINFO = json.load(f)
else:
    APPINFO = {"app_name": "Playing on SONOS", "version": "0.0", "author": "unknown"}

LAST_STATE = {}
ACTIVE_ROOM = ROOMS[0]["name"] if ROOMS else None


def get_room_state(room_obj):
    room = room_obj["name"]
    alias = room_obj.get("alias", room)
    url = f"{SERVER}{room}/state"

    try:
        resp = requests.get(url, timeout=2)
        data = resp.json() if resp.status_code == 200 else {}
    except Exception:
        old = LAST_STATE.get(room, {})
        return {
            "room": room,
            "alias": alias,
            "title": old.get("title", "—"),
            "artist": old.get("artist", "—"),
            "album_art": old.get("album_art", ""),
            "position": old.get("position", 0),
            "duration": old.get("duration", 0),
            "remaining": old.get("remaining", 0),
            "state": old.get("state", "unknown")
        }

    track = data.get("currentTrack", {}) or {}
    state = data.get("playbackState", "unknown")

    position = data.get("elapsedTime", 0) or 0
    duration = track.get("duration", 0) or 0
    remaining = duration - position if duration > 0 else 0

    title = track.get("title", LAST_STATE.get(room, {}).get("title", "—"))
    if isinstance(title, str) and title.startswith("ZPSTR_"):
        title = "Radio lädt…"

    LAST_STATE[room] = {
        "room": room,
        "alias": alias,
        "title": title,
        "artist": track.get("artist", LAST_STATE.get(room, {}).get("artist", "—")),
        "album_art": track.get("absoluteAlbumArtUri", LAST_STATE.get(room, {}).get("album_art", "")),
        "position": position,
        "duration": duration,
        "remaining": remaining,
        "state": state
    }

    return LAST_STATE[room]


def login_required(f):
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


@app.route("/")
def index():
    states = [get_room_state(r) for r in ROOMS]
    return render_template(
        "index.html",
        rooms=states,
        appinfo=APPINFO,
        display_width=DISPLAY_WIDTH,
        display_height=DISPLAY_HEIGHT,
        cover_size=COVER_SIZE,
        active_room=ACTIVE_ROOM
    )


@app.route("/setroom/<room>")
def set_room(room):
    global ACTIVE_ROOM
    if any(r["name"] == room for r in ROOMS):
        ACTIVE_ROOM = room
    return redirect(url_for("index"))


@app.route("/toggle")
def toggle():
    room = ACTIVE_ROOM
    if not room:
        return redirect(url_for("index"))

    try:
        data = requests.get(f"{SERVER}{room}/state", timeout=2).json()
        state = data.get("playbackState", "unknown")
    except Exception:
        state = "unknown"

    try:
        if state == "PLAYING":
            requests.get(f"{SERVER}{room}/pause")
        else:
            requests.get(f"{SERVER}{room}/play")
    except Exception:
        pass

    return redirect(url_for("index"))


@app.route("/next")
def next_track():
    if ACTIVE_ROOM:
        try:
            requests.get(f"{SERVER}{ACTIVE_ROOM}/next")
        except Exception:
            pass
    return redirect(url_for("index"))


@app.route("/previous")
def previous_track():
    if ACTIVE_ROOM:
        try:
            requests.get(f"{SERVER}{ACTIVE_ROOM}/previous")
        except Exception:
            pass
    return redirect(url_for("index"))


@app.route("/volume_up")
def volume_up():
    if ACTIVE_ROOM:
        try:
            requests.get(f"{SERVER}{ACTIVE_ROOM}/volume/+5")
        except Exception:
            pass
    return redirect(url_for("index"))


@app.route("/volume_down")
def volume_down():
    if ACTIVE_ROOM:
        try:
            requests.get(f"{SERVER}{ACTIVE_ROOM}/volume/-5")
        except Exception:
            pass
    return redirect(url_for("index"))


@app.route("/api/state")
def api_state():
    states = [get_room_state(r) for r in ROOMS]
    return jsonify({
        "active": ACTIVE_ROOM,
        "rooms": states
    })


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        pw = request.form.get("password")

        admin_cfg = CONFIG.get("admin", {})
        if user == admin_cfg.get("username") and pw == admin_cfg.get("password"):
            session["logged_in"] = True
            return redirect("/admin")

        return render_template("login.html", error="Falsche Zugangsdaten", appinfo=APPINFO)

    return render_template("login.html", appinfo=APPINFO)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/admin")
@login_required
def admin():
    admin_cfg = CONFIG.get("admin", {})
    return render_template(
        "admin.html",
        rooms=ROOMS,
        server=SERVER,
        display_width=DISPLAY_WIDTH,
        display_height=DISPLAY_HEIGHT,
        admin_username=admin_cfg.get("username", ""),
        admin_password=admin_cfg.get("password", ""),
        appinfo=APPINFO
    )


@app.route("/admin/save", methods=["POST"])
@login_required
def admin_save():
    global CONFIG, ROOMS, SERVER, DISPLAY_WIDTH, DISPLAY_HEIGHT

    new_rooms = []

    try:
        count = int(request.form.get("room_count", "0"))
    except ValueError:
        count = 0

    for i in range(1, count + 1):
        name = request.form.get(f"name_{i}", "").strip()
        alias = request.form.get(f"alias_{i}", "").strip()
        delete_flag = request.form.get(f"delete_{i}", "") == "on"

        old_name = request.form.get(f"old_name_{i}", "").strip()

        if delete_flag:
            continue

        if not name:
            name = old_name

        if not alias:
            alias = name

        new_rooms.append({
            "name": name,
            "alias": alias
        })

    new_name = request.form.get("new_name", "").strip()
    new_alias = request.form.get("new_alias", "").strip()

    if new_name:
        new_rooms.append({
            "name": new_name,
            "alias": new_alias or new_name
        })

    CONFIG["rooms"] = new_rooms
    ROOMS = new_rooms

    # System‑Einstellungen speichern
    new_server = request.form.get("server", "").strip()
    new_width = request.form.get("display_width", "").strip()
    new_height = request.form.get("display_height", "").strip()

    if new_server:
        CONFIG["server"] = new_server
        SERVER = new_server

    if new_width.isdigit():
        CONFIG["display_width"] = int(new_width)
        DISPLAY_WIDTH = int(new_width)

    if new_height.isdigit():
        CONFIG["display_height"] = int(new_height)
        DISPLAY_HEIGHT = int(new_height)

    # Admin‑Zugang speichern
    new_admin_user = request.form.get("admin_username", "").strip()
    new_admin_pass = request.form.get("admin_password", "").strip()

    if "admin" not in CONFIG:
        CONFIG["admin"] = {}

    if new_admin_user:
        CONFIG["admin"]["username"] = new_admin_user

    if new_admin_pass:
        CONFIG["admin"]["password"] = new_admin_pass

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(CONFIG, f, indent=4, ensure_ascii=False)

    return redirect("/admin")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5008, debug=DEBUG)
