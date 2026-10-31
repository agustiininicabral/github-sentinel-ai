import sqlite3
from pathlib import Path


class DeliveryLedger:
    """SQLite idempotency ledger for a single local service instance."""

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
                    received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def register(self, delivery_id: str, event_name: str, action: str | None) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO deliveries(delivery_id, event_name, action) VALUES (?, ?, ?)",
                (delivery_id, event_name, action),
            )
            return cursor.rowcount == 1
