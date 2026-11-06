"""Append-only transcript storage and a compact HTML viewer."""

import html
import json
import sqlite3
from pathlib import Path
from typing import Any

from agent.decision import DecisionRecord
from app.db import DEFAULT_DB_PATH, initialize_database


def append_turn(
    conversation_id: str,
    customer_message: str,
    decision: DecisionRecord,
    reply: str,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    initialize_database(db_path)
    decision_data = decision.model_dump(mode="json")
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "INSERT OR IGNORE INTO conversations (conversation_id) VALUES (?)",
            (conversation_id,),
        )
        next_number = connection.execute(
            "SELECT COALESCE(MAX(turn_number), 0) + 1 FROM conversation_turns WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO conversation_turns
               (conversation_id, turn_number, customer_message, decision_json, reply)
               VALUES (?, ?, ?, ?, ?)""",
            (conversation_id, next_number, customer_message, json.dumps(decision_data), reply),
        )
    return {
        "conversation_id": conversation_id,
        "turn_number": next_number,
        "customer_message": customer_message,
        "decision": decision_data,
        "reply": reply,
    }


def get_transcript(
    conversation_id: str,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT turn_number, customer_message, decision_json, reply, created_at
               FROM conversation_turns WHERE conversation_id = ? ORDER BY turn_number""",
            (conversation_id,),
        ).fetchall()
    return [
        {
            "turn_number": row["turn_number"],
            "customer_message": row["customer_message"],
            "decision": json.loads(row["decision_json"]),
            "reply": row["reply"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def render_transcript_html(conversation_id: str, turns: list[dict[str, Any]]) -> str:
    if not turns:
        body = '<p class="empty">No transcript turns found.</p>'
    else:
        rendered_turns = []
        for turn in turns:
            decision_json = json.dumps(turn["decision"], indent=2, ensure_ascii=True)
            rendered_turns.append(
                "<article class=\"turn\">"
                f"<h2>Turn {int(turn['turn_number'])}</h2>"
                "<div class=\"columns\">"
                "<section><h3>Decision record</h3>"
                f"<pre>{html.escape(decision_json)}</pre></section>"
                "<section><h3>Conversation</h3>"
                f"<p><strong>Customer</strong><br>{html.escape(turn['customer_message'])}</p>"
                f"<p><strong>Reply</strong><br>{html.escape(turn['reply'])}</p>"
                "</section></div></article>"
            )
        body = "".join(rendered_turns)

    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>Transcript {html.escape(conversation_id)}</title>"
        "<style>"
        "body{margin:0;background:#f3f5f4;color:#202825;font:15px/1.5 system-ui,sans-serif}"
        "main{max-width:1100px;margin:0 auto;padding:24px}"
        "h1{font-size:24px;margin:0 0 20px}h2{font-size:16px;margin:0 0 12px}"
        "h3{font-size:13px;text-transform:uppercase;color:#52615b;margin:0 0 8px}"
        ".turn{border-top:1px solid #cbd4cf;padding:18px 0}"
        ".columns{display:grid;grid-template-columns:minmax(300px,1fr) minmax(300px,1fr);gap:20px}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#e7ece9;padding:12px;border-radius:4px;margin:0}"
        "p{margin:0 0 14px;overflow-wrap:anywhere}.empty{color:#52615b}"
        "@media(max-width:700px){main{padding:16px}.columns{grid-template-columns:1fr}}"
        "</style></head><body><main>"
        f"<h1>Conversation transcript: {html.escape(conversation_id)}</h1>"
        f"{body}</main></body></html>"
    )