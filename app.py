"""Aura — professional AI assistant with voice notes, database, and kids mode."""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

import ai_engine
import database as db

ROOT = Path(__file__).resolve().parent
app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024

db.init_db()


def title_from(text: str) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if not t:
        return "New chat"
    if len(t) > 42:
        t = t[:40].rsplit(" ", 1)[0] + "…"
    return t


def json_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


@app.after_request
def no_store_app_shell(resp):
    if request.path in {"/", "/api/bootstrap"} or request.path.endswith((".js", ".css", ".html")):
        resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/bootstrap")
def bootstrap():
    settings = db.public_settings()
    convos = db.list_conversations(settings.get("mode") or None)
    return jsonify({"settings": settings, "conversations": convos})


@app.post("/api/onboard")
def onboard():
    data = request.get_json(force=True, silent=True) or {}
    name = str(data.get("user_name") or "").strip()[:40]
    mode = "kids" if data.get("mode") == "kids" else "pro"
    location = str(data.get("location") or "Jaipur").strip()[:60] or "Jaipur"
    pin = str(data.get("pin") or "").strip()
    payload = {
        "user_name": name,
        "mode": mode,
        "location": location,
        "onboarded": "1",
    }
    if mode == "kids" and re.fullmatch(r"\d{4}", pin or ""):
        salt = secrets.token_hex(8)
        payload["pin_salt"] = salt
        payload["pin_hash"] = hashlib.sha256((salt + pin).encode()).hexdigest()
        payload["has_pin"] = "1"
    db.set_settings(payload)
    return jsonify({"settings": db.public_settings()})


@app.put("/api/settings")
def update_settings():
    data = request.get_json(force=True, silent=True) or {}
    allowed = {"user_name", "mode", "auto_speak", "location", "voice_name"}
    values = {}
    for key in allowed:
        if key not in data:
            continue
        val = data[key]
        if key == "auto_speak":
            values[key] = "1" if val in (True, 1, "1", "true") else "0"
        elif key == "mode":
            values[key] = "kids" if val == "kids" else "pro"
        else:
            values[key] = str(val)[:80]
    if values:
        db.set_settings(values)
    return jsonify({"settings": db.public_settings()})


@app.post("/api/pin")
def set_pin():
    data = request.get_json(force=True, silent=True) or {}
    pin = str(data.get("pin") or "").strip()
    if not re.fullmatch(r"\d{4}", pin):
        return json_error("PIN must be 4 digits")
    salt = secrets.token_hex(8)
    db.set_settings(
        {
            "pin_salt": salt,
            "pin_hash": hashlib.sha256((salt + pin).encode()).hexdigest(),
            "has_pin": "1",
        }
    )
    return jsonify({"ok": True, "settings": db.public_settings()})


@app.post("/api/pin/verify")
def verify_pin():
    data = request.get_json(force=True, silent=True) or {}
    pin = str(data.get("pin") or "").strip()
    raw = db.get_settings()
    salt, hashed = raw.get("pin_salt") or "", raw.get("pin_hash") or ""
    if not hashed:
        return jsonify({"ok": True, "unlocked": True})
    guess = hashlib.sha256((salt + pin).encode()).hexdigest()
    if secrets.compare_digest(guess, hashed):
        return jsonify({"ok": True, "unlocked": True})
    return json_error("Incorrect PIN", 403)


@app.get("/api/conversations")
def conversations():
    mode = request.args.get("mode")
    if mode not in {"pro", "kids", None, ""}:
        mode = None
    return jsonify(db.list_conversations(mode or None))


@app.post("/api/conversations")
def new_conversation():
    data = request.get_json(force=True, silent=True) or {}
    mode = "kids" if data.get("mode") == "kids" else "pro"
    title = str(data.get("title") or "New chat")[:80]
    return jsonify(db.create_conversation(title, mode))


@app.get("/api/conversations/<int:cid>")
def get_conversation(cid: int):
    convo = db.get_conversation(cid)
    if not convo:
        return json_error("Conversation not found", 404)
    return jsonify({"conversation": convo, "messages": db.list_messages(cid)})


@app.patch("/api/conversations/<int:cid>")
def patch_conversation(cid: int):
    if not db.get_conversation(cid):
        return json_error("Conversation not found", 404)
    data = request.get_json(force=True, silent=True) or {}
    fields = {}
    if "title" in data:
        fields["title"] = str(data["title"])[:80]
    if "pinned" in data:
        fields["pinned"] = 1 if data["pinned"] else 0
    return jsonify(db.update_conversation(cid, **fields))


@app.delete("/api/conversations/<int:cid>")
def remove_conversation(cid: int):
    db.delete_conversation(cid)
    return jsonify({"ok": True})


@app.post("/api/chat")
def chat():
    data = request.get_json(force=True, silent=True) or {}
    content = str(data.get("content") or "").strip()
    if not content:
        return json_error("Message is empty")
    mode = "kids" if data.get("mode") == "kids" else "pro"
    cid = data.get("conversation_id")
    settings = db.public_settings()
    user_name = settings.get("user_name") or ""
    location = settings.get("location") or "Jaipur"
    source = str((data.get("client_meta") or {}).get("source") or "text")

    if cid:
        convo = db.get_conversation(int(cid))
        if not convo:
            return json_error("Conversation not found", 404)
    else:
        convo = db.create_conversation(title_from(content), mode)
        cid = convo["id"]

    user_msg = db.add_message(
        cid,
        "user",
        content,
        msg_type="voice" if source in {"voice", "voice_note"} else "text",
        meta={"source": source},
    )
    history = db.history_for_ai(cid)
    result = ai_engine.generate(
        content,
        history=history[:-1],
        kids_mode=(mode == "kids"),
        user_name=user_name,
        location=location,
    )
    assistant = db.add_message(cid, "assistant", result["text"], meta=result.get("meta") or {})
    if convo.get("title") in {"New chat", ""}:
        convo = db.update_conversation(cid, title=title_from(content)) or convo
    return jsonify(
        {
            "conversation": db.get_conversation(cid),
            "user_message": user_msg,
            "assistant_message": assistant,
        }
    )


@app.post("/api/chat/voice")
def chat_voice():
    audio = request.files.get("audio")
    transcript = str(request.form.get("transcript") or "").strip()
    mode = "kids" if request.form.get("mode") == "kids" else "pro"
    cid_raw = request.form.get("conversation_id")
    duration_ms = int(request.form.get("duration_ms") or 0)
    peaks = request.form.get("peaks")
    settings = db.public_settings()

    if not audio and not transcript:
        return json_error("Missing audio")

    audio_file = None
    if audio:
        ext = os.path.splitext(audio.filename or "")[1].lower()
        if ext not in {".webm", ".ogg", ".mp3", ".wav", ".m4a", ".mp4"}:
            ext = ".webm"
        audio_file = f"{uuid.uuid4().hex}{ext}"
        audio.save(db.AUDIO_DIR / audio_file)

    content = transcript or "Voice note"
    if cid_raw:
        cid = int(cid_raw)
        convo = db.get_conversation(cid)
        if not convo:
            return json_error("Conversation not found", 404)
    else:
        convo = db.create_conversation(title_from(content), mode)
        cid = convo["id"]

    meta = {"source": "voice_note"}
    if peaks:
        meta["peaks"] = peaks
    user_msg = db.add_message(
        cid,
        "user",
        content,
        msg_type="voice",
        audio_file=audio_file,
        duration_ms=duration_ms or None,
        meta=meta,
    )

    if transcript:
        history = db.history_for_ai(cid)
        result = ai_engine.generate(
            transcript,
            history=history[:-1],
            kids_mode=(mode == "kids"),
            user_name=settings.get("user_name") or "",
            location=settings.get("location") or "Jaipur",
        )
        text = result["text"]
        ameta = result.get("meta") or {}
    else:
        text = (
            "I saved your voice note. I couldn't transcribe it this time — "
            "use the live mic for speech-to-text, or type what you said."
        )
        ameta = {}
    assistant = db.add_message(cid, "assistant", text, meta=ameta)
    if convo.get("title") in {"New chat", ""}:
        db.update_conversation(cid, title=title_from(content))
    return jsonify(
        {
            "conversation": db.get_conversation(cid),
            "user_message": user_msg,
            "assistant_message": assistant,
        }
    )


@app.get("/api/media/<path:filename>")
def media(filename: str):
    safe = Path(filename).name
    return send_from_directory(db.AUDIO_DIR, safe)


@app.post("/api/reset")
def reset():
    db.reset_all()
    return jsonify({"ok": True, "settings": db.public_settings()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
