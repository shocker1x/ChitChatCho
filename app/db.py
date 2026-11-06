"""SQLite initialization for synthetic mock backend data."""

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "data" / "chitchat.sqlite3"
SEED_PATH = ROOT / "data" / "seed.json"


def initialize_database(
    db_path: str | Path | None = None,
    seed_path: str | Path = SEED_PATH,
) -> None:
    target = Path(db_path or os.getenv("CHITCHAT_DB_PATH", DEFAULT_DB_PATH))
    target.parent.mkdir(parents=True, exist_ok=True)
    seed: dict[str, list[dict[str, Any]]] = json.loads(Path(seed_path).read_text(encoding="utf-8"))
    orders = seed.get("orders") or _generate_orders(seed)
    shipments = seed.get("shipments") or _generate_shipments(orders)

    with sqlite3.connect(target) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                postcode TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'rug',
                size TEXT NOT NULL DEFAULT '',
                material TEXT NOT NULL DEFAULT '',
                construction TEXT NOT NULL DEFAULT '',
                pile_height TEXT NOT NULL DEFAULT '',
                color TEXT NOT NULL DEFAULT '',
                style TEXT NOT NULL DEFAULT '',
                price REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL REFERENCES customers(customer_id),
                product_id TEXT NOT NULL REFERENCES products(product_id),
                status TEXT NOT NULL,
                ordered_at TEXT NOT NULL DEFAULT '',
                address TEXT NOT NULL DEFAULT '',
                is_custom INTEGER NOT NULL DEFAULT 0,
                delivered_at TEXT NOT NULL DEFAULT '',
                unused INTEGER NOT NULL DEFAULT 1,
                original_packaging INTEGER NOT NULL DEFAULT 1,
                reported_at TEXT NOT NULL DEFAULT '',
                photo_received INTEGER NOT NULL DEFAULT 0,
                wrong_or_damaged INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                customer_id TEXT REFERENCES customers(customer_id),
                summary TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS conversation_turns (
                turn_id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id),
                turn_number INTEGER NOT NULL,
                customer_message TEXT NOT NULL,
                decision_json TEXT NOT NULL,
                reply TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(conversation_id, turn_number)
            );
            CREATE TABLE IF NOT EXISTS shipments (
                order_id TEXT PRIMARY KEY REFERENCES orders(order_id),
                carrier TEXT NOT NULL,
                tracking_number TEXT NOT NULL,
                status TEXT NOT NULL,
                estimated_delivery TEXT NOT NULL DEFAULT '',
                last_event TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS tool_calls (
                call_id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name TEXT NOT NULL,
                inputs_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                idempotency_key TEXT PRIMARY KEY,
                tool_name TEXT NOT NULL,
                result_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS financial_transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL REFERENCES orders(order_id),
                kind TEXT NOT NULL,
                amount REAL NOT NULL,
                reason TEXT NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS return_labels (
                label_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL UNIQUE REFERENCES orders(order_id),
                idempotency_key TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS escalations (
                escalation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        _ensure_columns(
            connection,
            "customers",
            {"postcode": "TEXT NOT NULL DEFAULT ''"},
        )
        _ensure_columns(
            connection,
            "products",
            {
                "category": "TEXT NOT NULL DEFAULT 'rug'",
                "construction": "TEXT NOT NULL DEFAULT ''",
                "pile_height": "TEXT NOT NULL DEFAULT ''",
                "color": "TEXT NOT NULL DEFAULT ''",
                "style": "TEXT NOT NULL DEFAULT ''",
            },
        )
        _ensure_columns(
            connection,
            "orders",
            {
                "ordered_at": "TEXT NOT NULL DEFAULT ''",
                "address": "TEXT NOT NULL DEFAULT ''",
                "is_custom": "INTEGER NOT NULL DEFAULT 0",
                "delivered_at": "TEXT NOT NULL DEFAULT ''",
                "unused": "INTEGER NOT NULL DEFAULT 1",
                "original_packaging": "INTEGER NOT NULL DEFAULT 1",
                "reported_at": "TEXT NOT NULL DEFAULT ''",
                "photo_received": "INTEGER NOT NULL DEFAULT 0",
                "wrong_or_damaged": "INTEGER NOT NULL DEFAULT 0",
            },
        )

        connection.executemany(
            """INSERT INTO customers (customer_id, name, email, postcode)
               VALUES (:customer_id, :name, :email, :postcode)
               ON CONFLICT(customer_id) DO UPDATE SET
               postcode=CASE WHEN customers.postcode='' THEN excluded.postcode ELSE customers.postcode END""",
            [
                {"postcode": "", **customer}
                for customer in seed.get("customers", [])
            ],
        )
        connection.executemany(
            """INSERT INTO products
               (product_id, name, category, size, material, construction, pile_height, color, style, price)
               VALUES (:product_id, :name, :category, :size, :material, :construction,
                       :pile_height, :color, :style, :price)
               ON CONFLICT(product_id) DO UPDATE SET
               category=CASE WHEN products.category='' THEN excluded.category ELSE products.category END,
               construction=CASE WHEN products.construction='' THEN excluded.construction ELSE products.construction END,
               pile_height=CASE WHEN products.pile_height='' THEN excluded.pile_height ELSE products.pile_height END,
               color=CASE WHEN products.color='' THEN excluded.color ELSE products.color END,
               style=CASE WHEN products.style='' THEN excluded.style ELSE products.style END""",
            [
                {
                    "category": "rug",
                    "construction": "",
                    "pile_height": "",
                    "color": "",
                    "style": "",
                    **product,
                }
                for product in seed.get("products", [])
            ],
        )
        connection.executemany(
            """INSERT INTO orders
               (order_id, customer_id, product_id, status, ordered_at, address, is_custom,
                delivered_at, unused, original_packaging, reported_at, photo_received, wrong_or_damaged)
               VALUES (:order_id, :customer_id, :product_id, :status, :ordered_at, :address,
                       :is_custom, :delivered_at, :unused, :original_packaging, :reported_at,
                       :photo_received, :wrong_or_damaged)
               ON CONFLICT(order_id) DO UPDATE SET
               ordered_at=CASE WHEN orders.ordered_at='' THEN excluded.ordered_at ELSE orders.ordered_at END,
               address=CASE WHEN orders.address='' THEN excluded.address ELSE orders.address END,
               is_custom=CASE WHEN orders.is_custom=0 THEN excluded.is_custom ELSE orders.is_custom END,
               delivered_at=CASE WHEN orders.delivered_at='' THEN excluded.delivered_at ELSE orders.delivered_at END,
               reported_at=CASE WHEN orders.reported_at='' THEN excluded.reported_at ELSE orders.reported_at END,
               photo_received=MAX(orders.photo_received, excluded.photo_received),
               wrong_or_damaged=MAX(orders.wrong_or_damaged, excluded.wrong_or_damaged)""",
            [
                {
                    "ordered_at": "",
                    "address": "",
                    "is_custom": 0,
                    "delivered_at": "",
                    "unused": 1,
                    "original_packaging": 1,
                    "reported_at": "",
                    "photo_received": 0,
                    "wrong_or_damaged": 0,
                    **order,
                }
                for order in orders
            ],
        )
        connection.executemany(
                """INSERT OR IGNORE INTO shipments
               (order_id, carrier, tracking_number, status, estimated_delivery, last_event)
                    VALUES (:order_id, :carrier, :tracking_number, :status, :estimated_delivery, :last_event)""",
            shipments,
        )


def _ensure_columns(
    connection: sqlite3.Connection,
    table: str,
    columns: dict[str, str],
) -> None:
    existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    for column, definition in columns.items():
        if column not in existing:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _generate_orders(seed: dict[str, Any]) -> list[dict[str, Any]]:
    customers = seed["customers"]
    products = seed["products"]
    order_groups = seed.get("order_status_counts", {})
    orders = []
    order_number = 0
    for status, count in order_groups.items():
        for _ in range(count):
            order_number += 1
            if status == "processing":
                ordered_at, delivered_at = "2026-11-01", ""
            elif status == "shipped":
                ordered_at, delivered_at = "2026-10-25", ""
            elif status == "delivered":
                ordered_at, delivered_at = "2026-10-15", "2026-10-25T10:00:00"
            elif status == "delayed":
                ordered_at, delivered_at = "2026-10-20", ""
            else:
                ordered_at, delivered_at = "2026-11-01", "2026-11-04T08:00:00"
            product = products[(order_number - 1) % len(products)]
            damaged = status == "damaged-reported"
            orders.append(
                {
                    "order_id": f"MOCK-ORDER-{order_number:03d}",
                    "customer_id": customers[(order_number - 1) % len(customers)]["customer_id"],
                    "product_id": product["product_id"],
                    "status": status,
                    "ordered_at": ordered_at,
                    "address": f"{100 + order_number} Sample Street, Mock City",
                    "is_custom": int(product["size"] == "cut-to-size" or order_number == 20),
                    "delivered_at": delivered_at,
                    "unused": 1,
                    "original_packaging": 1,
                    "reported_at": "2026-11-04T15:00:00" if damaged else "",
                    "photo_received": int(damaged),
                    "wrong_or_damaged": int(damaged),
                }
            )
    return orders


def _generate_shipments(orders: list[dict[str, Any]]) -> list[dict[str, str]]:
    shipments = []
    for order in orders:
        status = order["status"]
        if status == "processing":
            continue
        if status == "delayed":
            shipment_status = "delayed"
            estimated_delivery = "2026-11-08"
            last_event = "Transit delay reported at mock regional hub"
        elif status in {"delivered", "damaged-reported"}:
            shipment_status = "delivered"
            estimated_delivery = order["delivered_at"][:10]
            last_event = f"Delivered on {estimated_delivery} (mock event)"
        else:
            shipment_status = "in_transit"
            estimated_delivery = "2026-11-10"
            last_event = "Departed mock sorting facility"
        number = int(order["order_id"][-3:])
        shipments.append(
            {
                "order_id": order["order_id"],
                "carrier": "Mock Parcel" if number % 2 else "Fictional Freight",
                "tracking_number": f"MOCKTRACK{number:08d}",
                "status": shipment_status,
                "estimated_delivery": estimated_delivery,
                "last_event": last_event,
            }
        )
    return shipments