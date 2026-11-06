"""Conversation and verified customer-profile memory backed by SQLite."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.db import DEFAULT_DB_PATH, initialize_database


class MemoryStore:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        initialize_database(self.db_path)

    def load_context(
        self,
        conversation_id: str,
        *,
        order_id: str | None = None,
        email: str | None = None,
        postcode: str | None = None,
    ) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            conversation = connection.execute(
                "SELECT known_facts_json, customer_id FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
            known_facts = json.loads(conversation["known_facts_json"]) if conversation else []
            turn_rows = connection.execute(
                """SELECT customer_message, reply FROM conversation_turns
                   WHERE conversation_id = ? ORDER BY turn_number""",
                (conversation_id,),
            ).fetchall()
            identity = self._verified_customer(connection, order_id, email, postcode)
            if conversation and conversation["customer_id"] and identity:
                if conversation["customer_id"] != identity["customer_id"]:
                    identity = None
            profile = self._load_profile(connection, identity["customer_id"]) if identity else None

        if profile:
            profile_facts = [
                f"Customer preference: {key}={value}"
                for key, value in profile["preferences"].items()
            ]
            if profile["last_conversation_summary"]:
                profile_facts.append(
                    f"Previous conversation summary: {profile['last_conversation_summary']}"
                )
            seen = {fact.casefold() for fact in known_facts}
            for fact in profile_facts:
                if fact.casefold() not in seen:
                    known_facts.append(fact)
                    seen.add(fact.casefold())

        history = []
        for row in turn_rows:
            history.append({"role": "user", "content": row["customer_message"]})
            history.append({"role": "assistant", "content": row["reply"]})

        return {
            "conversation_id": conversation_id,
            "history": history,
            "known_facts": known_facts,
            "identity_verified": identity is not None,
            "customer_profile": profile,
        }

    def record_turn(
        self,
        conversation_id: str,
        customer_message: str,
        decision: Any,
        reply: str,
        *,
        known_facts: list[str] | None = None,
    ) -> dict[str, Any]:
        initialize_database(self.db_path)
        decision_data = decision.model_dump(mode="json")
        facts = list(dict.fromkeys([*(decision.known or []), *(known_facts or [])]))
        with sqlite3.connect(self.db_path) as connection:
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
            row = connection.execute(
                "SELECT known_facts_json FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
            current = json.loads(row[0]) if row else []
            seen = {fact.casefold() for fact in current}
            for fact in facts:
                normalized = fact.casefold()
                if normalized not in seen:
                    current.append(fact)
                    seen.add(normalized)
            connection.execute(
                "UPDATE conversations SET known_facts_json = ? WHERE conversation_id = ?",
                (json.dumps(current), conversation_id),
            )
        return {
            "conversation_id": conversation_id,
            "turn_number": next_number,
            "customer_message": customer_message,
            "decision": decision_data,
            "reply": reply,
        }

    def complete_conversation(
        self,
        conversation_id: str,
        summary: str,
        *,
        order_id: str,
        email: str | None = None,
        postcode: str | None = None,
        preferences: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not summary.strip():
            raise ValueError("A concise conversation summary is required.")

        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            identity = self._verified_customer(connection, order_id, email, postcode)
            if identity is None:
                raise PermissionError("Identity verification failed.")

            customer_id = identity["customer_id"]
            conversation = connection.execute(
                "SELECT customer_id FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
            if conversation and conversation["customer_id"] not in (None, customer_id):
                raise PermissionError("Conversation belongs to a different verified customer.")
            connection.execute(
                "INSERT OR IGNORE INTO conversations (conversation_id) VALUES (?)",
                (conversation_id,),
            )
            existing = connection.execute(
                "SELECT preferences_json FROM customer_profiles WHERE customer_id = ?",
                (customer_id,),
            ).fetchone()
            saved_preferences = json.loads(existing["preferences_json"]) if existing else {}
            saved_preferences.update(preferences or {})
            issues = [
                {
                    "order_id": row["order_id"],
                    "status": row["status"],
                    "reported_at": row["reported_at"],
                }
                for row in connection.execute(
                    """SELECT order_id, status, reported_at FROM orders
                       WHERE customer_id = ? AND (wrong_or_damaged = 1 OR status = 'damaged-reported')
                       ORDER BY order_id""",
                    (customer_id,),
                ).fetchall()
            ]
            completed_at = datetime.now(timezone.utc).isoformat()
            connection.execute(
                """INSERT INTO customer_profiles
                   (customer_id, preferences_json, past_issues_json, last_conversation_summary, updated_at)
                   VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(customer_id) DO UPDATE SET
                   preferences_json=excluded.preferences_json,
                   past_issues_json=excluded.past_issues_json,
                   last_conversation_summary=excluded.last_conversation_summary,
                   updated_at=CURRENT_TIMESTAMP""",
                (customer_id, json.dumps(saved_preferences), json.dumps(issues), summary.strip()),
            )
            connection.execute(
                """UPDATE conversations SET customer_id = ?, summary = ?, completed_at = ?
                   WHERE conversation_id = ?""",
                (customer_id, summary.strip(), completed_at, conversation_id),
            )
            order_rows = connection.execute(
                """SELECT o.order_id, o.status, p.name AS product_name
                   FROM orders o JOIN products p ON p.product_id = o.product_id
                   WHERE o.customer_id = ? ORDER BY o.order_id""",
                (customer_id,),
            ).fetchall()

        return {
            "customer_id": customer_id,
            "last_conversation_summary": summary.strip(),
            "past_orders": [dict(row) for row in order_rows],
            "past_issues": issues,
            "preferences": saved_preferences,
        }

    def _verified_customer(
        self,
        connection: sqlite3.Connection,
        order_id: str | None,
        email: str | None,
        postcode: str | None,
    ) -> dict[str, Any] | None:
        if not order_id or (not email and not postcode):
            return None
        row = connection.execute(
            """SELECT c.customer_id, c.name, c.email FROM orders o
               JOIN customers c ON c.customer_id = o.customer_id
               WHERE o.order_id = ? AND ((? IS NOT NULL AND lower(c.email) = lower(?))
               OR (? IS NOT NULL AND upper(c.postcode) = upper(?)))""",
            (order_id, email, email, postcode, postcode),
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def _load_profile(connection: sqlite3.Connection, customer_id: str) -> dict[str, Any]:
        customer = connection.execute(
            "SELECT customer_id, name FROM customers WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()
        profile = connection.execute(
            "SELECT * FROM customer_profiles WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()
        orders = connection.execute(
            """SELECT o.order_id, o.status, p.name AS product_name
               FROM orders o JOIN products p ON p.product_id = o.product_id
               WHERE o.customer_id = ? ORDER BY o.order_id""",
            (customer_id,),
        ).fetchall()
        if profile:
            preferences = json.loads(profile["preferences_json"])
            issues = json.loads(profile["past_issues_json"])
            summary = profile["last_conversation_summary"]
        else:
            preferences = {}
            issues = [
                {"order_id": row["order_id"], "status": row["status"], "reported_at": row["reported_at"]}
                for row in connection.execute(
                    """SELECT order_id, status, reported_at FROM orders
                       WHERE customer_id = ? AND (wrong_or_damaged = 1 OR status = 'damaged-reported')
                       ORDER BY order_id""",
                    (customer_id,),
                ).fetchall()
            ]
            summary = ""
        return {
            "customer_id": customer["customer_id"],
            "name": customer["name"],
            "past_orders": [dict(row) for row in orders],
            "past_issues": issues,
            "preferences": preferences,
            "last_conversation_summary": summary,
        }
