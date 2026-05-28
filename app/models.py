from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


JsonDict = dict[str, Any]


@dataclass(frozen=True)
class Agent:
    id: str
    name: str
    role: str
    system_prompt: str
    model: str
    tools: list[str]
    channel: str
    memory_enabled: bool
    guardrails: str
    created_at: datetime


@dataclass(frozen=True)
class Workflow:
    id: str
    name: str
    description: str
    template_key: str
    config: JsonDict
    created_at: datetime


@dataclass(frozen=True)
class WorkflowRunResult:
    run_id: str
    workflow_id: str
    status: str
    output: str
    token_count: int
    estimated_cost: float

