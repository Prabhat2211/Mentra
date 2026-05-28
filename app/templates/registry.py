from __future__ import annotations

import json
from typing import Any

from app.db import Database
from app.templates.financial_assistant import FINANCIAL_ASSISTANT_TEMPLATE
from app.templates.research_summary import RESEARCH_SUMMARY_TEMPLATE
from app.templates.types import WorkflowTemplate


TEMPLATES: dict[str, WorkflowTemplate] = {
    RESEARCH_SUMMARY_TEMPLATE.key: RESEARCH_SUMMARY_TEMPLATE,
    FINANCIAL_ASSISTANT_TEMPLATE.key: FINANCIAL_ASSISTANT_TEMPLATE,
}


def get_template(template_key: str) -> WorkflowTemplate:
    try:
        return TEMPLATES[template_key]
    except KeyError as exc:
        raise ValueError(f"Unknown workflow template: {template_key}") from exc


def seed_default_workflows(db: Database) -> None:
    existing = {row["template_key"] for row in db.list_workflows()}
    for template in TEMPLATES.values():
        if template.key not in existing:
            db.create_workflow(
                name=template.name,
                description=template.description,
                template_key=template.key,
                config=template.default_config,
            )


def decode_workflow_config(row: Any) -> dict[str, Any]:
    return json.loads(row["config_json"] or "{}")
