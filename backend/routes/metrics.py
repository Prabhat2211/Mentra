from __future__ import annotations

from fastapi import APIRouter, Depends
from app.db import Database

router = APIRouter()


def get_db() -> Database:
    db = Database()
    db.init()
    return db


@router.get("/metrics")
async def get_metrics(db: Database = Depends(get_db)):
    agents = db.list_agents()
    workflows = db.list_workflows()
    runs = db.list_runs()
    messages = db.list_messages(limit=500)

    configurable_dimensions = 14

    total = len(runs)
    completed = sum(1 for r in runs if r["status"] == "completed")
    failed = sum(1 for r in runs if r["status"] == "failed")

    agent_messages = [m for m in messages if m["from_agent_id"]]

    durations = [r["duration_ms"] for r in runs if r["duration_ms"] is not None]
    avg_runtime_ms = round(sum(durations) / len(durations), 1) if durations else 0
    total_runtime_ms = sum(durations) if durations else 0

    return {
        "agents_count": len(agents),
        "workflows_count": len(workflows),
        "configurable_dimensions_per_agent": configurable_dimensions,
        "total_runs": total,
        "completed_runs": completed,
        "failed_runs": failed,
        "completion_rate": round(completed / total * 100, 1) if total else 100.0,
        "total_agent_messages": len(agent_messages),
        "total_messages": len(messages),
        "avg_runtime_ms": avg_runtime_ms,
        "total_runtime_ms": total_runtime_ms,
    }
