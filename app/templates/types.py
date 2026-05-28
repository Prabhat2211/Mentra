from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WorkflowTemplate:
    key: str
    name: str
    description: str
    nodes: list[str]
    edges: list[tuple[str, str]]
    sample_input: str
    default_config: dict[str, Any]

