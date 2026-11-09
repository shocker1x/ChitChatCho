"""SQLite-backed synthetic store data and auditable mock actions."""

import json
import sqlite3
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from app.db import DEFAULT_DB_PATH, initialize_database


MOCK_REFUND_LIMIT = 150.0
CARE_GUIDES = {
    "wool": "Vacuum a new wool rug regularly on a suction-only setting. Light shedding is common at first and usually eases with use.",
    "shedding": "Light shedding from a new wool rug is normal. Vacuum gently with suction only; avoid a beater bar.",
    "color_variation": "Screen and room lighting can make rug colors look slightly different. Compare the rug in the room's natural and evening light.",
    "rolled_edges": "Lay the rug flat and reverse-roll the curled edge briefly if needed. Avoid sharp folds or high heat.",
    "jute": "Blot spills promptly with a clean dry cloth. Avoid soaking jute; moisture can mark natural fibers.",
    "cotton": "Check the rug's care label before washing. Blot spills promptly and avoid color-bleeding cleaners.",
    "synthetic": "Vacuum regularly and blot spills with a mild cleaner tested on an inconspicuous area first.",
    "rug_pads": "Use a rug pad suited to the floor surface and rug size. Check the floor maker's guidance for finish compatibility.",
    "care_kits": "Follow each care product's label and test it on a hidden area before treating the full rug.",
}


class MockTools:
    def __init__(
        self,
        db_path: str | Path | None = None,
        failure_hook: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        initialize_database(self.db_path)
        self.failure_hook = failure_hook

    def search_catalog(
        self,
        query: str = "",
        category: str | None = None,
        material: str | None = None,
        size: str | None = None,
        max_results: int = 10,
    ) -> dict[str, Any]:
        inputs = locals().copy()
        inputs.pop("self")

        def action(connection: sqlite3.Connection) -> dict[str, Any]:
            clauses = []
            values: list[Any] = []
            if query.strip():
                clauses.append("(name LIKE ? OR color LIKE ? OR style LIKE ?)")
                like_query = f"%{query.strip()}%"
                values.extend([like_query] * 3)
            for column, value in (("category", category), ("material", material), ("size", size)):
                if value:
                    clauses.append(f"{column} = ? COLLATE NOCASE")
                    values.append(value)
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            products = connection.execute(
                f"SELECT * FROM products {where} ORDER BY product_id LIMIT ?",
                [*values, max(1, min(int(max_results), 50))],
            ).fetchall()
            return {"ok": True, "products": [dict(product) for product in products]}

        return self._invoke("search_catalog", inputs, action)

    def lookup_order(
        self,
        order_id: str,
        email: str | None = None,
        postcode: str | None = None,
    ) -> dict[str, Any]:
        inputs = {"order_id": order_id, "email": email, "postcode": postcode}

        def action(connection: sqlite3.Connection) -> dict[str, Any]:
            row = self._verified_order(connection, order_id, email, postcode)
            if row is None:
                raise ValueError("Order not found or verification did not match.")
            return {"ok": True, "order": row}

        return self._invoke("lookup_order", inputs, action)

    def order_exists(self, order_id: str) -> dict[str, Any]:
        inputs = {"order_id": order_id}

        def action(connection: sqlite3.Connection) -> dict[str, Any]:
            exists = connection.execute(
                "SELECT 1 FROM orders WHERE order_id = ?",
                (order_id,),
            ).fetchone() is not None
            return {"ok": True, "exists": exists}

        return self._invoke("order_exists", inputs, action)

    def track_shipment(
        self,
        order_id: str,
        email: str | None = None,
        postcode: str | None = None,
    ) -> dict[str, Any]:
        inputs = {"order_id": order_id, "email": email, "postcode": postcode}

        def action(connection: sqlite3.Connection) -> dict[str, Any]:
            if self._verified_order(connection, order_id, email, postcode) is None:
                raise ValueError("Order not found or verification did not match.")
            shipment = connection.execute(
                "SELECT * FROM shipments WHERE order_id = ?", (order_id,)
            ).fetchone()
            if shipment is None:
                raise ValueError("Shipment data is not available for this order.")
            return {"ok": True, "shipment": dict(shipment)}

        return self._invoke("track_shipment", inputs, action)

    def check_return_eligibility(
        self,
        order_id: str,
        email: str | None = None,
        postcode: str | None = None,
        today: date | None = None,
    ) -> dict[str, Any]:
        inputs = {
            "order_id": order_id,
            "email": email,
            "postcode": postcode,
            "today": (today or date.today()).isoformat(),
        }

        def action(connection: sqlite3.Connection) -> dict[str, Any]:
            order = self._verified_order(connection, order_id, email, postcode)
            if order is None:
                raise ValueError("Order not found or verification did not match.")
            return self._return_eligibility(order, today or date.today())

        return self._invoke("check_return_eligibility", inputs, action)

    def get_care_guide(self, topic: str) -> dict[str, Any]:
        inputs = {"topic": topic}

        def action(connection: sqlite3.Connection) -> dict[str, Any]:
            del connection
            normalized_topic = topic.strip().lower()
            guide = CARE_GUIDES.get(normalized_topic)
            if guide is None:
                raise ValueError(f"No care guide is available for '{topic}'.")
            return {"ok": True, "topic": normalized_topic, "guide": guide, "mock": True}

        return self._invoke("get_care_guide", inputs, action)

    def issue_refund(
        self,
        order_id: str,
        amount: float,
        reason: str,
        email: str | None = None,
        postcode: str | None = None,
        confirmed: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return self._issue_value("issue_refund", order_id, amount, reason, email, postcode, confirmed, idempotency_key)

    def issue_store_credit(
        self,
        order_id: str,
        amount: float,
        reason: str,
        email: str | None = None,
        postcode: str | None = None,
        confirmed: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return self._issue_value("issue_store_credit", order_id, amount, reason, email, postcode, confirmed, idempotency_key)

    def _issue_value(
        self,
        tool_name: str,
        order_id: str,
        amount: float,
        reason: str,
        email: str | None,
        postcode: str | None,
        confirmed: bool,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        inputs = {
            "order_id": order_id,
            "amount": amount,
            "reason": reason,
            "email": email,
            "postcode": postcode,
            "confirmed": confirmed,
            "idempotency_key": idempotency_key,
        }

        def action(connection: sqlite3.Connection) -> dict[str, Any]:
            if self._verified_order(connection, order_id, email, postcode) is None:
                raise ValueError("Order not found or verification did not match.")
            numeric_amount = float(amount)
            if numeric_amount <= 0:
                raise ValueError("Amount must be greater than zero.")
            if numeric_amount > MOCK_REFUND_LIMIT:
                raise ValueError("Amount exceeds the mock authority limit; human escalation is required.")
            cursor = connection.execute(
                """INSERT INTO financial_transactions
                   (order_id, kind, amount, reason, idempotency_key) VALUES (?, ?, ?, ?, ?)""",
                (order_id, tool_name, numeric_amount, reason, idempotency_key),
            )
            return {
                "ok": True,
                "transaction_id": cursor.lastrowid,
                "order_id": order_id,
                "kind": tool_name,
                "amount": numeric_amount,
                "mock": True,
            }

        return self._invoke(
            tool_name,
            inputs,
            action,
            idempotency_key=idempotency_key,
            confirmed=confirmed,
            risky=True,
        )

    def cancel_order(
        self,
        order_id: str,
        email: str | None = None,
        postcode: str | None = None,
        confirmed: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        inputs = {
            "order_id": order_id,
            "email": email,
            "postcode": postcode,
            "confirmed": confirmed,
            "idempotency_key": idempotency_key,
        }

        def action(connection: sqlite3.Connection) -> dict[str, Any]:
            order = self._verified_order(connection, order_id, email, postcode)
            if order is None:
                raise ValueError("Order not found or verification did not match.")
            if order["status"] == "cancelled":
                return {"ok": True, "order_id": order_id, "status": "cancelled", "already_done": True}
            if order["status"] != "processing":
                raise ValueError("Only orders that have not shipped can be cancelled.")
            connection.execute("UPDATE orders SET status = 'cancelled' WHERE order_id = ?", (order_id,))
            return {"ok": True, "order_id": order_id, "status": "cancelled", "mock": True}

        return self._invoke(
            "cancel_order", inputs, action, idempotency_key=idempotency_key,
            confirmed=confirmed, risky=True,
        )

    def create_return_label(
        self,
        order_id: str,
        email: str | None = None,
        postcode: str | None = None,
        confirmed: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        inputs = {
            "order_id": order_id,
            "email": email,
            "postcode": postcode,
            "confirmed": confirmed,
            "idempotency_key": idempotency_key,
        }

        def action(connection: sqlite3.Connection) -> dict[str, Any]:
            order = self._verified_order(connection, order_id, email, postcode)
            if order is None:
                raise ValueError("Order not found or verification did not match.")
            eligibility = self._return_eligibility(order, date.today())
            if not eligibility["eligible"]:
                raise ValueError(f"Return label cannot be created: {eligibility['reason']}")
            existing = connection.execute(
                "SELECT label_id FROM return_labels WHERE order_id = ?", (order_id,)
            ).fetchone()
            if existing:
                return {"ok": True, "order_id": order_id, "label_id": existing["label_id"], "already_done": True}
            label_id = f"MOCK-LABEL-{uuid.uuid4().hex[:12].upper()}"
            connection.execute(
                "INSERT INTO return_labels (label_id, order_id, idempotency_key) VALUES (?, ?, ?)",
                (label_id, order_id, idempotency_key),
            )
            return {"ok": True, "order_id": order_id, "label_id": label_id, "mock": True}

        return self._invoke(
            "create_return_label", inputs, action, idempotency_key=idempotency_key,
            confirmed=confirmed, risky=True,
        )

    def update_address(
        self,
        order_id: str,
        new_address: str,
        email: str | None = None,
        postcode: str | None = None,
        confirmed: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        inputs = {
            "order_id": order_id,
            "new_address": new_address,
            "email": email,
            "postcode": postcode,
            "confirmed": confirmed,
            "idempotency_key": idempotency_key,
        }

        def action(connection: sqlite3.Connection) -> dict[str, Any]:
            order = self._verified_order(connection, order_id, email, postcode)
            if order is None:
                raise ValueError("Order not found or verification did not match.")
            if order["status"] != "processing":
                raise ValueError("Address can only be updated before the order ships.")
            if not new_address.strip():
                raise ValueError("A new address is required.")
            connection.execute("UPDATE orders SET address = ? WHERE order_id = ?", (new_address.strip(), order_id))
            return {"ok": True, "order_id": order_id, "address": new_address.strip(), "mock": True}

        return self._invoke(
            "update_address", inputs, action, idempotency_key=idempotency_key,
            confirmed=confirmed, risky=True,
        )

    def escalate_to_human(self, summary: str) -> dict[str, Any]:
        inputs = {"summary": summary}

        def action(connection: sqlite3.Connection) -> dict[str, Any]:
            if not summary.strip():
                raise ValueError("An escalation summary is required.")
            cursor = connection.execute("INSERT INTO escalations (summary) VALUES (?)", (summary.strip(),))
            return {"ok": True, "escalation_id": cursor.lastrowid, "mock": True}

        return self._invoke("escalate_to_human", inputs, action)

    def get_tool_logs(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute("SELECT * FROM tool_calls ORDER BY call_id").fetchall()
        return [
            {
                "call_id": row["call_id"],
                "tool_name": row["tool_name"],
                "inputs": json.loads(row["inputs_json"]),
                "result": json.loads(row["result_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def _verified_order(
        self,
        connection: sqlite3.Connection,
        order_id: str,
        email: str | None,
        postcode: str | None,
    ) -> dict[str, Any] | None:
        if not email and not postcode:
            raise ValueError("Identity verification requires email or postcode with the order number.")
        row = connection.execute(
            """SELECT o.*, p.name AS product_name, p.size, p.material, p.price
               FROM orders o JOIN customers c ON c.customer_id = o.customer_id
               JOIN products p ON p.product_id = o.product_id
               WHERE o.order_id = ? AND ((? IS NOT NULL AND lower(c.email) = lower(?))
               OR (? IS NOT NULL AND upper(c.postcode) = upper(?)))""",
            (order_id, email, email, postcode, postcode),
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def _return_eligibility(order: dict[str, Any], today: date) -> dict[str, Any]:
        if order["is_custom"]:
            return {"ok": True, "eligible": False, "reason": "Custom or cut-to-size items are final sale."}
        delivered_at = order["delivered_at"]
        if not delivered_at:
            return {"ok": True, "eligible": False, "reason": "Delivery has not been recorded."}
        delivered_date = date.fromisoformat(delivered_at[:10])
        days_since_delivery = (today - delivered_date).days
        if order["wrong_or_damaged"]:
            reported_at = order["reported_at"]
            if not reported_at:
                return {"ok": True, "eligible": False, "reason": "A damage report date is required."}
            hours_to_report = (datetime.fromisoformat(reported_at) - datetime.fromisoformat(delivered_at)).total_seconds() / 3600
            if hours_to_report < 0 or hours_to_report > 48:
                return {"ok": True, "eligible": False, "reason": "Damage or wrong items must be reported within 48 hours of delivery."}
            if not order["photo_received"]:
                return {"ok": True, "eligible": False, "reason": "At least one photo is required for a damage or wrong-item report."}
            return {"ok": True, "eligible": True, "reason": "Damage or wrong item reported within policy requirements."}
        if days_since_delivery < 0 or days_since_delivery > 30:
            return {"ok": True, "eligible": False, "reason": "Standard returns are limited to 30 days after delivery."}
        if not order["unused"]:
            return {"ok": True, "eligible": False, "reason": "The rug must be unused for a standard return."}
        if not order["original_packaging"]:
            return {"ok": True, "eligible": False, "reason": "Original packaging is required for a standard return."}
        return {"ok": True, "eligible": True, "reason": "Meets the mock standard return conditions; customer pays return shipping."}

    def _invoke(
        self,
        tool_name: str,
        inputs: dict[str, Any],
        action: Callable[[sqlite3.Connection], dict[str, Any]],
        idempotency_key: str | None = None,
        confirmed: bool = True,
        risky: bool = False,
    ) -> dict[str, Any]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                if risky and not confirmed:
                    raise ValueError("Explicit customer confirmation is required before this action.")
                if risky and not idempotency_key:
                    raise ValueError("An idempotency key is required for this action.")
                if idempotency_key:
                    previous = connection.execute(
                        "SELECT tool_name, result_json FROM idempotency_keys WHERE idempotency_key = ?",
                        (idempotency_key,),
                    ).fetchone()
                    if previous:
                        if previous["tool_name"] != tool_name:
                            raise ValueError("This idempotency key was already used for a different action.")
                        result = json.loads(previous["result_json"])
                        result["replayed"] = True
                        self._write_log(connection, tool_name, inputs, result)
                        return result
                if self.failure_hook:
                    self.failure_hook(tool_name, inputs)
                result = action(connection)
                if idempotency_key:
                    connection.execute(
                        "INSERT INTO idempotency_keys (idempotency_key, tool_name, result_json) VALUES (?, ?, ?)",
                        (idempotency_key, tool_name, json.dumps(result)),
                    )
                self._write_log(connection, tool_name, inputs, result)
                return result
        except Exception as error:
            result = {"ok": False, "error": str(error)}
            with connection:
                self._write_log(connection, tool_name, inputs, result)
            return result
        finally:
            connection.close()

    @staticmethod
    def _write_log(
        connection: sqlite3.Connection,
        tool_name: str,
        inputs: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        connection.execute(
            "INSERT INTO tool_calls (tool_name, inputs_json, result_json) VALUES (?, ?, ?)",
            (tool_name, json.dumps(inputs, default=str), json.dumps(result, default=str)),
        )