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
            # Create tables if they don't exist
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
            
            # Add new columns if they don't exist (for existing databases)
            try:
                conn.execute("ALTER TABLE agents ADD COLUMN llm_provider TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                conn.execute("ALTER TABLE agents ADD COLUMN llm_api_key_encrypted BLOB")
            except sqlite3.OperationalError:
                pass
            
            try:
                conn.execute("ALTER TABLE agents ADD COLUMN llm_model TEXT")
            except sqlite3.OperationalError:
                pass
            
            try:
                conn.execute("ALTER TABLE agents ADD COLUMN personality TEXT NOT NULL DEFAULT 'professional'")
            except sqlite3.OperationalError:
                pass
            
            try:
                conn.execute("ALTER TABLE workflows ADD COLUMN is_custom INTEGER NOT NULL DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            
            try:
                conn.execute("ALTER TABLE workflows ADD COLUMN nodes_json TEXT")
            except sqlite3.OperationalError:
                pass
            
            try:
                conn.execute("ALTER TABLE workflows ADD COLUMN edges_json TEXT")
            except sqlite3.OperationalError:
                pass

            try:
                conn.execute("ALTER TABLE runs ADD COLUMN duration_ms INTEGER")
            except sqlite3.OperationalError:
                pass

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schedules (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    interval_minutes INTEGER NOT NULL,
                    input_text TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_run_at TEXT,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
                )
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
        personality: str = "professional",
        llm_provider: str | None = None,
        llm_api_key_encrypted: bytes | None = None,
        llm_model: str | None = None,
    ) -> str:
        agent_id = str(uuid.uuid4())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO agents (
                    id, name, role, system_prompt, model, tools_json,
                    channel, memory_enabled, guardrails, personality,
                    llm_provider, llm_api_key_encrypted, llm_model, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    personality,
                    llm_provider,
                    llm_api_key_encrypted,
                    llm_model,
                    utc_now(),
                ),
            )
        return agent_id

    def list_agents(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(conn.execute("SELECT * FROM agents ORDER BY created_at DESC"))

    def delete_agent(self, agent_id: str) -> bool:
        with self.connect() as conn:
            cursor = conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
            return cursor.rowcount > 0

    def update_agent(
        self,
        *,
        agent_id: str,
        name: str,
        role: str,
        system_prompt: str,
        model: str,
        tools: list[str] | None = None,
        channel: str = "ui",
        memory_enabled: bool = False,
        guardrails: str = "",
        personality: str = "professional",
        llm_provider: str | None = None,
        llm_api_key_encrypted: bytes | None = None,
        llm_model: str | None = None,
    ) -> bool:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE agents SET
                    name = ?, role = ?, system_prompt = ?, model = ?,
                    tools_json = ?, channel = ?, memory_enabled = ?, guardrails = ?,
                    personality = ?, llm_provider = ?, llm_api_key_encrypted = ?,
                    llm_model = ?
                WHERE id = ?
                """,
                (
                    name, role, system_prompt, model,
                    json.dumps(tools or []), channel, int(memory_enabled), guardrails,
                    personality, llm_provider, llm_api_key_encrypted,
                    llm_model,
                    agent_id,
                ),
            )
            return cursor.rowcount > 0

    def create_workflow(
        self,
        *,
        name: str,
        description: str,
        template_key: str,
        config: dict[str, Any] | None = None,
        is_custom: bool = False,
        nodes: list[dict] | None = None,
        edges: list[dict] | None = None,
    ) -> str:
        workflow_id = str(uuid.uuid4())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO workflows (id, name, description, template_key, config_json, is_custom, nodes_json, edges_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workflow_id,
                    name,
                    description,
                    template_key,
                    json.dumps(config or {}),
                    int(is_custom),
                    json.dumps(nodes or []),
                    json.dumps(edges or []),
                    utc_now(),
                ),
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

    def delete_workflow(self, workflow_id: str) -> bool:
        with self.connect() as conn:
            conn.execute("DELETE FROM logs WHERE run_id IN (SELECT id FROM runs WHERE workflow_id = ?)", (workflow_id,))
            conn.execute("DELETE FROM messages WHERE run_id IN (SELECT id FROM runs WHERE workflow_id = ?)", (workflow_id,))
            conn.execute("DELETE FROM messages WHERE workflow_id = ?", (workflow_id,))
            conn.execute("DELETE FROM runs WHERE workflow_id = ?", (workflow_id,))
            cursor = conn.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
            return cursor.rowcount > 0

    def update_workflow(
        self,
        *,
        workflow_id: str,
        name: str,
        description: str,
        config: dict[str, Any] | None = None,
        is_custom: bool = False,
        nodes: list[dict] | None = None,
        edges: list[dict] | None = None,
    ) -> bool:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE workflows SET
                    name = ?, description = ?, config_json = ?,
                    is_custom = ?, nodes_json = ?, edges_json = ?
                WHERE id = ?
                """,
                (
                    name,
                    description,
                    json.dumps(config or {}),
                    int(is_custom),
                    json.dumps(nodes or []),
                    json.dumps(edges or []),
                    workflow_id,
                ),
            )
            return cursor.rowcount > 0

    # --- Schedule methods ---

    def create_schedule(
        self,
        *,
        workflow_id: str,
        name: str,
        interval_minutes: int,
        input_text: str = "",
    ) -> str:
        schedule_id = str(uuid.uuid4())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO schedules (id, workflow_id, name, interval_minutes, input_text, enabled, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (schedule_id, workflow_id, name, interval_minutes, input_text, utc_now()),
            )
        return schedule_id

    def list_schedules(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(conn.execute("SELECT * FROM schedules ORDER BY created_at DESC"))

    def update_schedule(
        self,
        *,
        schedule_id: str,
        name: str,
        interval_minutes: int,
        input_text: str = "",
        enabled: bool = True,
    ) -> bool:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE schedules SET name = ?, interval_minutes = ?, input_text = ?, enabled = ?
                WHERE id = ?
                """,
                (name, interval_minutes, input_text, int(enabled), schedule_id),
            )
            return cursor.rowcount > 0

    def delete_schedule(self, schedule_id: str) -> bool:
        with self.connect() as conn:
            cursor = conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
            return cursor.rowcount > 0

    def mark_schedule_run(self, schedule_id: str) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE schedules SET last_run_at = ? WHERE id = ?", (utc_now(), schedule_id))

    def get_due_schedules(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM schedules WHERE enabled = 1 ORDER BY last_run_at ASC"
            ).fetchall()
        now = utc_now()
        from datetime import datetime, timezone

        now_dt = datetime.fromisoformat(now)
        due: list[sqlite3.Row] = []
        for row in rows:
            last = row["last_run_at"]
            if last is None:
                due.append(row)
                continue
            last_dt = datetime.fromisoformat(last)
            elapsed = (now_dt - last_dt).total_seconds() / 60
            if elapsed >= row["interval_minutes"]:
                due.append(row)
        return due

    # --- Run methods ---

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
        duration_ms: int | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE runs
                SET status = ?, output = ?, token_count = ?, estimated_cost = ?, duration_ms = ?, completed_at = ?
                WHERE id = ?
                """,
                (status, output, token_count, estimated_cost, duration_ms, utc_now(), run_id),
            )

    def get_run(self, run_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()

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

