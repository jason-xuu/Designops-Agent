from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class SqliteStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    brief_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    status TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    node TEXT NOT NULL,
                    input TEXT NOT NULL,
                    output TEXT NOT NULL,
                    confidence TEXT,
                    duration_ms INTEGER NOT NULL
                )
                """
            )

    def insert_run_start(self, run_id: str, brief_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO runs(id, brief_id, started_at, status) VALUES (?, ?, ?, ?)",
                (run_id, brief_id, datetime.utcnow().isoformat(), "running"),
            )

    def insert_step(
        self,
        *,
        run_id: str,
        node: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        confidence: str | None,
        duration_ms: int,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO steps(run_id, node, input, output, confidence, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    node,
                    json.dumps(input_data),
                    json.dumps(output_data),
                    confidence,
                    duration_ms,
                ),
            )

    def complete_run(self, run_id: str, status: str = "completed") -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE runs SET completed_at = ?, status = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), status, run_id),
            )
