from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db import Database
from app.runtime.graph import run_workflow

router = APIRouter()


class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    template_key: str
    config: dict[str, Any] | None = None
    is_custom: bool = False
    nodes: list[dict[str, Any]] | None = None
    edges: list[dict[str, Any]] | None = None
    agent_assignments: dict[str, str] | None = None


class WorkflowRunRequest(BaseModel):
    user_input: str
    source_channel: str = "ui"
    external_user_id: str | None = None


def get_db() -> Database:
    db = Database()
    db.init()
    return db


@router.get("/")
async def list_workflows(db: Database = Depends(get_db)):
    rows = db.list_workflows()
    return [dict(row) for row in rows]


@router.post("/")
async def create_workflow(workflow: WorkflowCreate, db: Database = Depends(get_db)):
    config = workflow.config or {}
    if workflow.agent_assignments:
        config["agent_assignments"] = workflow.agent_assignments
    workflow_id = db.create_workflow(
        name=workflow.name,
        description=workflow.description,
        template_key=workflow.template_key,
        config=config,
        is_custom=workflow.is_custom,
        nodes=workflow.nodes,
        edges=workflow.edges,
    )
    return {"id": workflow_id, "message": "Workflow created successfully"}


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str, db: Database = Depends(get_db)):
    try:
        row = db.get_workflow(workflow_id)
        return dict(row)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{workflow_id}")
async def update_workflow(workflow_id: str, workflow: WorkflowCreate, db: Database = Depends(get_db)):
    config = workflow.config or {}
    if workflow.agent_assignments:
        config["agent_assignments"] = workflow.agent_assignments
    updated = db.update_workflow(
        workflow_id=workflow_id,
        name=workflow.name,
        description=workflow.description,
        config=config,
        is_custom=workflow.is_custom,
        nodes=workflow.nodes,
        edges=workflow.edges,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"id": workflow_id, "message": "Workflow updated successfully"}


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str, db: Database = Depends(get_db)):
    deleted = db.delete_workflow(workflow_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"message": "Workflow deleted successfully"}


@router.post("/{workflow_id}/run")
async def run_workflow_endpoint(
    workflow_id: str, request: WorkflowRunRequest, db: Database = Depends(get_db)
):
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: run_workflow(
                workflow_id=workflow_id,
                user_input=request.user_input,
                source_channel=request.source_channel,
                external_user_id=request.external_user_id,
                db=db,
            )
        )
        try:
            run_row = db.get_run(result.run_id)
            duration_ms = run_row["duration_ms"] if run_row else None
        except Exception:
            duration_ms = None
        return {
            "run_id": result.run_id,
            "status": result.status,
            "output": result.output,
            "token_count": result.token_count,
            "estimated_cost": result.estimated_cost,
            "duration_ms": duration_ms,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
