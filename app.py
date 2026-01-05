from flask import Flask, render_template, redirect, url_for, jsonify
import requests
import json

app = Flask(__name__)

with open("config.json", "r") as f:
    CONFIG = json.load(f)

SERVER = CONFIG["server"]
ROOMS = CONFIG["rooms"]
DEBUG = CONFIG.get("debug", False)

DISPLAY_WIDTH = CONFIG.get("display_width", 720)
DISPLAY_HEIGHT = CONFIG.get("display_height", 720)

# Dynamische Covergröße: 50% der kürzeren Displayseite
COVER_SIZE = int(min(DISPLAY_WIDTH, DISPLAY_HEIGHT) * 0.5)

with open("appinfo.json", "r") as f:
    APPINFO = json.load(f)

LAST_STATE = {}

def debug_print(*args):
    if DEBUG:
        print("[DEBUG]", *args)

def get_room_state(room):
    url = f"{SERVER}{room}/state"

    try:
        data = requests.get(url, timeout=2).json()
    except Exception as e:
        old = LAST_STATE.get(room, {})
        return {
            "room": room,
            "title": old.get("title", "—"),
            "artist": old.get("artist", "—"),
            "album_art": old.get("album_art", ""),
            "position": old.get("position", 0),
            "duration": old.get("duration", 0),
            "remaining": old.get("remaining", 0),
            "state": old.get("state", "unknown"),
            "error": str(e)
        }

    track = data.get("currentTrack", {})
    state = data.get("playbackState", "unknown")

    position = data.get("elapsedTime", 0) or 0
    duration = track.get("duration", 0) or 0
    remaining = duration - position if duration > 0 else 0

    if state in ["PLAYING", "PAUSED", "PAUSED_PLAYBACK"]:
        LAST_STATE[room] = {
            "room": room,
            "title": track.get("title", LAST_STATE.get(room, {}).get("title", "—")),
            "artist": track.get("artist", LAST_STATE.get(room, {}).get("artist", "—")),
            "album_art": track.get("absoluteAlbumArtUri", LAST_STATE.get(room, {}).get("album_art", "")),
            "position": position,
            "duration": duration,
            "remaining": remaining,
            "state": state
        }
        return LAST_STATE[room]

    old = LAST_STATE.get(room, {})
    return {
        "room": room,
        "title": old.get("title", "—"),
        "artist": old.get("artist", "—"),
        "album_art": old.get("album_art", ""),
        "position": old.get("position", 0),
        "duration": old.get("duration", 0),
        "remaining": old.get("remaining", 0),
        "state": state
    }

@app.route("/")
def index():
    states = [get_room_state(room) for room in ROOMS]
    return render_template(
        "index.html",
        rooms=states,
        appinfo=APPINFO,
        display_width=DISPLAY_WIDTH,
        display_height=DISPLAY_HEIGHT,
        cover_size=COVER_SIZE
    )

@app.route("/toggle/<room>")
def toggle(room):
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

# --- Neue Buttons ---
@app.route("/next/<room>")
def next_track(room):
    requests.get(f"{SERVER}{room}/next")
    return redirect(url_for("index"))

@app.route("/previous/<room>")
def previous_track(room):
    requests.get(f"{SERVER}{room}/previous")
    return redirect(url_for("index"))

@app.route("/volume_up/<room>")
def volume_up(room):
    requests.get(f"{SERVER}{room}/volume/+5")
    return redirect(url_for("index"))

@app.route("/volume_down/<room>")
def volume_down(room):
    requests.get(f"{SERVER}{room}/volume/-5")
    return redirect(url_for("index"))

@app.route("/api/state")
def api_state():
    states = [get_room_state(room) for room in ROOMS]
    return jsonify(states)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5008)