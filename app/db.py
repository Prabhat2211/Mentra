from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.config import settings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = str(path or settings.database_path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    system_prompt TEXT NOT NULL,
                    model TEXT NOT NULL,
                    tools_json TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    memory_enabled INTEGER NOT NULL DEFAULT 0,
                    guardrails TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    template_key TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input TEXT NOT NULL,
                    output TEXT NOT NULL DEFAULT '',
                    token_count INTEGER NOT NULL DEFAULT 0,
                    estimated_cost REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    run_id TEXT,
                    workflow_id TEXT NOT NULL,
                    from_agent_id TEXT,
                    to_agent_id TEXT,
                    channel TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id),
                    FOREIGN KEY (run_id) REFERENCES runs(id)
                );

                CREATE TABLE IF NOT EXISTS logs (
                    id TEXT PRIMARY KEY,
                    run_id TEXT,
                    level TEXT NOT NULL,
                    event TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(id)
                );
                """
            )

    def create_agent(
        self,
        *,
        name: str,
        role: str,
        system_prompt: str,
        model: str,
        tools: list[str] | None = None,
        channel: str = "ui",
        memory_enabled: bool = False,
        guardrails: str = "",
    ) -> str:
        agent_id = str(uuid.uuid4())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO agents (
                    id, name, role, system_prompt, model, tools_json,
                    channel, memory_enabled, guardrails, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    agent_id,
                    name,
                    role,
                    system_prompt,
                    model,
                    json.dumps(tools or []),
                    channel,
                    int(memory_enabled),
                    guardrails,
                    utc_now(),
                ),
            )
        return agent_id

    def list_agents(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(conn.execute("SELECT * FROM agents ORDER BY created_at DESC"))

    def create_workflow(
        self,
        *,
        name: str,
        description: str,
        template_key: str,
        config: dict[str, Any] | None = None,
    ) -> str:
        workflow_id = str(uuid.uuid4())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO workflows (id, name, description, template_key, config_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (workflow_id, name, description, template_key, json.dumps(config or {}), utc_now()),
            )
        return workflow_id

    def list_workflows(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(conn.execute("SELECT * FROM workflows ORDER BY created_at DESC"))

    def get_workflow(self, workflow_id: str) -> sqlite3.Row:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        if row is None:
            raise ValueError(f"Workflow not found: {workflow_id}")
        return row

    def create_run(self, *, workflow_id: str, user_input: str) -> str:
        run_id = str(uuid.uuid4())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO runs (id, workflow_id, status, input, created_at)
                VALUES (?, ?, 'running', ?, ?)
                """,
                (run_id, workflow_id, user_input, utc_now()),
            )
        return run_id

    def complete_run(
        self,
        *,
        run_id: str,
        status: str,
        output: str,
        token_count: int,
        estimated_cost: float,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE runs
                SET status = ?, output = ?, token_count = ?, estimated_cost = ?, completed_at = ?
                WHERE id = ?
                """,
                (status, output, token_count, estimated_cost, utc_now(), run_id),
            )

    def list_runs(self, limit: int = 25) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                )
            )

    def add_message(
        self,
        *,
        workflow_id: str,
        content: str,
        channel: str,
        run_id: str | None = None,
        from_agent_id: str | None = None,
        to_agent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        message_id = str(uuid.uuid4())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO messages (
                    id, run_id, workflow_id, from_agent_id, to_agent_id,
                    channel, content, metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    run_id,
                    workflow_id,
                    from_agent_id,
                    to_agent_id,
                    channel,
                    content,
                    json.dumps(metadata or {}),
                    utc_now(),
                ),
            )
        return message_id

    def list_messages(self, limit: int = 100) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    "SELECT * FROM messages ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                )
            )

    def add_log(
        self,
        *,
        event: str,
        level: str = "info",
        run_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> str:
        log_id = str(uuid.uuid4())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO logs (id, run_id, level, event, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (log_id, run_id, level, event, json.dumps(payload or {}), utc_now()),
            )
        return log_id

    def list_logs(self, limit: int = 100) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(conn.execute("SELECT * FROM logs ORDER BY created_at DESC LIMIT ?", (limit,)))

