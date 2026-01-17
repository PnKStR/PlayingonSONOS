from flask import Flask, render_template, redirect, url_for, jsonify, request, session
import requests
import json

app = Flask(__name__)
app.secret_key = "change_this_secret_key"

# Load config
with open("config.json", "r") as f:
    CONFIG = json.load(f)

SERVER = CONFIG["server"]
ROOMS = CONFIG["rooms"]          # Liste von Objekten: {name, alias}
DEBUG = CONFIG.get("debug", False)

DISPLAY_WIDTH = CONFIG.get("display_width", 720)
DISPLAY_HEIGHT = CONFIG.get("display_height", 720)

COVER_SIZE = int(min(DISPLAY_WIDTH, DISPLAY_HEIGHT) * 0.5)

with open("appinfo.json", "r") as f:
    APPINFO = json.load(f)

LAST_STATE = {}

# Active room = Name des ersten Raums
ACTIVE_ROOM = ROOMS[0]["name"]


def get_room_state(room_obj):
    room = room_obj["name"]
    alias = room_obj["alias"]
    url = f"{SERVER}{room}/state"

    try:
        data = requests.get(url, timeout=2).json()
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

    track = data.get("currentTrack", {})
    state = data.get("playbackState", "unknown")

    position = data.get("elapsedTime", 0) or 0
    duration = track.get("duration", 0) or 0
    remaining = duration - position if duration > 0 else 0

    LAST_STATE[room] = {
        "room": room,
        "alias": alias,
        "title": track.get("title", LAST_STATE.get(room, {}).get("title", "—")),
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
    # Prüfen, ob Raum existiert
    if any(r["name"] == room for r in ROOMS):
        ACTIVE_ROOM = room
    return redirect(url_for("index"))


@app.route("/toggle")
def toggle():
    room = ACTIVE_ROOM
    try:
        data = requests.get(f"{SERVER}{room}/state", timeout=2).json()
        state = data.get("playbackState", "unknown")
    except:
        state = "unknown"

    if state == "PLAYING":
        requests.get(f"{SERVER}{room}/pause")
    else:
        requests.get(f"{SERVER}{room}/play")

    return redirect(url_for("index"))


@app.route("/next")
def next_track():
    requests.get(f"{SERVER}{ACTIVE_ROOM}/next")
    return redirect(url_for("index"))


@app.route("/previous")
def previous_track():
    requests.get(f"{SERVER}{ACTIVE_ROOM}/previous")
    return redirect(url_for("index"))


@app.route("/volume_up")
def volume_up():
    requests.get(f"{SERVER}{ACTIVE_ROOM}/volume/+5")
    return redirect(url_for("index"))


@app.route("/volume_down")
def volume_down():
    requests.get(f"{SERVER}{ACTIVE_ROOM}/volume/-5")
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

        if user == CONFIG["admin"]["username"] and pw == CONFIG["admin"]["password"]:
            session["logged_in"] = True
            return redirect("/admin")

        return render_template("login.html", error="Falsche Zugangsdaten")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/admin")
@login_required
def admin():
    return render_template("admin.html", rooms=ROOMS)


@app.route("/admin/save", methods=["POST"])
@login_required
def admin_save():
    global CONFIG, ROOMS

    new_rooms = []

    # Bestehende Räume bearbeiten
    count = int(request.form.get("room_count", "0"))
    for i in range(1, count + 1):
        name = request.form.get(f"name_{i}", "").strip()
        alias = request.form.get(f"alias_{i}", "").strip()
        delete_flag = request.form.get(f"delete_{i}", "") == "on"

        if not name:
            continue
        if delete_flag:
            continue

        new_rooms.append({
            "name": name,
            "alias": alias or name
        })

    # Neuen Raum hinzufügen
    new_name = request.form.get("new_name", "").strip()
    new_alias = request.form.get("new_alias", "").strip()
    if new_name:
        new_rooms.append({
            "name": new_name,
            "alias": new_alias or new_name
        })

    CONFIG["rooms"] = new_rooms
    ROOMS = new_rooms

    with open("config.json", "w") as f:
        json.dump(CONFIG, f, indent=4)

    return redirect("/admin")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5008, debug=DEBUG)
