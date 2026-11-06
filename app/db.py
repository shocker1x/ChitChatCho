"""SQLite initialization for synthetic Phase 0 data."""

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

    with sqlite3.connect(target) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                size TEXT NOT NULL,
                material TEXT NOT NULL,
                price REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL REFERENCES customers(customer_id),
                product_id TEXT NOT NULL REFERENCES products(product_id),
                status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                customer_id TEXT REFERENCES customers(customer_id),
                summary TEXT NOT NULL DEFAULT ''
            );
            """
        )
        connection.executemany(
            "INSERT OR IGNORE INTO customers VALUES (:customer_id, :name, :email)",
            seed["customers"],
        )
        connection.executemany(
            "INSERT OR IGNORE INTO products VALUES (:product_id, :name, :size, :material, :price)",
            seed["products"],
        )
        connection.executemany(
            "INSERT OR IGNORE INTO orders VALUES (:order_id, :customer_id, :product_id, :status)",
            seed["orders"],
        )