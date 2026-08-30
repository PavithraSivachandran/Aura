"""SQLite persistence for Aura conversations, messages, and settings."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
AUDIO_DIR = DATA_DIR / "audio"
DB_PATH = DATA_DIR / "aura.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT 'New chat',
                mode TEXT NOT NULL DEFAULT 'pro',
                topic TEXT,
                pinned INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                msg_type TEXT NOT NULL DEFAULT 'text',
                audio_file TEXT,
                duration_ms INTEGER,
                meta TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id, id);
            CREATE INDEX IF NOT EXISTS idx_conv_updated ON conversations(updated_at DESC);
            """
        )
        conn.commit()
        defaults = {
            "onboarded": "0",
            "user_name": "",
            "mode": "pro",
            "auto_speak": "0",
            "location": "Jaipur",
            "has_pin": "0",
            "pin_hash": "",
            "pin_salt": "",
            "voice_name": "",
        }
        for key, value in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        conn.commit()
    finally:
        conn.close()


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def get_settings() -> dict[str, str]:
    conn = connect()
    try:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {r["key"]: r["value"] for r in rows}
    finally:
        conn.close()


def public_settings() -> dict[str, Any]:
    raw = get_settings()
    return {
        "onboarded": raw.get("onboarded") == "1",
        "user_name": raw.get("user_name") or "",
        "mode": raw.get("mode") or "pro",
        "auto_speak": raw.get("auto_speak") == "1",
        "location": raw.get("location") or "Jaipur",
        "has_pin": bool(raw.get("pin_hash")),
        "voice_name": raw.get("voice_name") or "",
    }


def set_setting(key: str, value: str) -> None:
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()


def set_settings(values: dict[str, str]) -> None:
    conn = connect()
    try:
        for key, value in values.items():
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value)),
            )
        conn.commit()
    finally:
        conn.close()


def list_conversations(mode: str | None = None) -> list[dict[str, Any]]:
    conn = connect()
    try:
        if mode:
            rows = conn.execute(
                "SELECT * FROM conversations WHERE mode = ? ORDER BY pinned DESC, updated_at DESC",
                (mode,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM conversations ORDER BY pinned DESC, updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_conversation(cid: int) -> dict[str, Any] | None:
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM conversations WHERE id = ?", (cid,)).fetchone()
        return _row(row)
    finally:
        conn.close()


def create_conversation(title: str, mode: str) -> dict[str, Any]:
    now = utcnow()
    conn = connect()
    try:
        cur = conn.execute(
            "INSERT INTO conversations (title, mode, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (title, mode, now, now),
        )
        conn.commit()
        cid = cur.lastrowid
        row = conn.execute("SELECT * FROM conversations WHERE id = ?", (cid,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def update_conversation(cid: int, **fields: Any) -> dict[str, Any] | None:
    if not fields:
        return get_conversation(cid)
    fields["updated_at"] = utcnow()
    keys = ", ".join(f"{k} = ?" for k in fields)
    conn = connect()
    try:
        conn.execute(f"UPDATE conversations SET {keys} WHERE id = ?", (*fields.values(), cid))
        conn.commit()
        row = conn.execute("SELECT * FROM conversations WHERE id = ?", (cid,)).fetchone()
        return _row(row)
    finally:
        conn.close()


def delete_conversation(cid: int) -> None:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT audio_file FROM messages WHERE conversation_id = ? AND audio_file IS NOT NULL",
            (cid,),
        ).fetchall()
        conn.execute("DELETE FROM conversations WHERE id = ?", (cid,))
        conn.commit()
    finally:
        conn.close()
    for row in rows:
        path = AUDIO_DIR / row["audio_file"]
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass


def add_message(
    conversation_id: int,
    role: str,
    content: str,
    msg_type: str = "text",
    audio_file: str | None = None,
    duration_ms: int | None = None,
    meta: dict | None = None,
) -> dict[str, Any]:
    now = utcnow()
    meta_s = json.dumps(meta) if meta else None
    conn = connect()
    try:
        cur = conn.execute(
            """
            INSERT INTO messages (conversation_id, role, content, msg_type, audio_file, duration_ms, meta, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (conversation_id, role, content, msg_type, audio_file, duration_ms, meta_s, now),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (cur.lastrowid,)).fetchone()
        return serialize_message(row)
    finally:
        conn.close()


def list_messages(conversation_id: int) -> list[dict[str, Any]]:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC",
            (conversation_id,),
        ).fetchall()
        return [serialize_message(r) for r in rows]
    finally:
        conn.close()


def last_assistant_meta(conversation_id: int) -> dict[str, Any]:
    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT meta FROM messages
            WHERE conversation_id = ? AND role = 'assistant'
            ORDER BY id DESC LIMIT 1
            """,
            (conversation_id,),
        ).fetchone()
        if not row or not row["meta"]:
            return {}
        try:
            return json.loads(row["meta"])
        except json.JSONDecodeError:
            return {}
    finally:
        conn.close()


def serialize_message(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    if data.get("meta"):
        try:
            data["meta"] = json.loads(data["meta"])
        except json.JSONDecodeError:
            data["meta"] = {}
    else:
        data["meta"] = {}
    return data


def history_for_ai(conversation_id: int, limit: int = 12) -> list[dict[str, Any]]:
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT role, content, meta FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (conversation_id, limit),
        ).fetchall()
    finally:
        conn.close()
    items = []
    for row in reversed(list(rows)):
        meta = {}
        if row["meta"]:
            try:
                meta = json.loads(row["meta"])
            except json.JSONDecodeError:
                meta = {}
        items.append({"role": row["role"], "content": row["content"] or "", "meta": meta})
    return items


def reset_all() -> None:
    conn = connect()
    try:
        conn.execute("DELETE FROM messages")
        conn.execute("DELETE FROM conversations")
        conn.execute("DELETE FROM settings")
        conn.commit()
    finally:
        conn.close()
    for path in AUDIO_DIR.glob("*"):
        if path.is_file():
            try:
                path.unlink()
            except OSError:
                pass
    init_db()
