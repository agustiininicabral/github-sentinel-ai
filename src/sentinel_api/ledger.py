import json
import sqlite3
from pathlib import Path
from typing import Any


class DeliveryLedger:
    """SQLite delivery ledger and transactional outbox for a single local instance."""

    def __init__(self, database_path: str):
        self.database_path = database_path
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS deliveries (
                    delivery_id TEXT PRIMARY KEY,
                    event_name TEXT NOT NULL,
                    action TEXT,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'pending',
                    received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    processed_at TEXT
                )
            """)
            # Lightweight forward migration for databases created by earlier MVP versions.
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(deliveries)")}
            if "payload_json" not in columns:
                connection.execute("ALTER TABLE deliveries ADD COLUMN payload_json TEXT NOT NULL DEFAULT '{}'")
            if "status" not in columns:
                connection.execute("ALTER TABLE deliveries ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'")
            if "processed_at" not in columns:
                connection.execute("ALTER TABLE deliveries ADD COLUMN processed_at TEXT")

    def register(self, delivery_id: str, event_name: str, action: str | None,
                 payload: dict[str, Any]) -> bool:
        """Atomically enqueue a verified delivery once; return False for duplicates."""
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT OR IGNORE INTO deliveries
                   (delivery_id, event_name, action, payload_json)
                   VALUES (?, ?, ?, ?)""",
                (delivery_id, event_name, action, json.dumps(payload, separators=(",", ":"))),
            )
            return cursor.rowcount == 1

    def pending(self, limit: int = 20) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 100))
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT delivery_id, event_name, action, payload_json, received_at
                   FROM deliveries WHERE status = 'pending'
                   ORDER BY received_at, delivery_id LIMIT ?""",
                (safe_limit,),
            ).fetchall()
        return [{
            "delivery_id": row["delivery_id"],
            "event": row["event_name"],
            "action": row["action"],
            "payload": json.loads(row["payload_json"]),
            "received_at": row["received_at"],
        } for row in rows]

    def acknowledge(self, delivery_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE deliveries SET status = 'processed', processed_at = CURRENT_TIMESTAMP
                   WHERE delivery_id = ? AND status = 'pending'""",
                (delivery_id,),
            )
            return cursor.rowcount == 1
