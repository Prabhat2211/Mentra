from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db import Database

router = APIRouter()


class ScheduleCreate(BaseModel):
    workflow_id: str
    name: str
    interval_minutes: int
    input_text: str = ""


class ScheduleUpdate(BaseModel):
    name: str
    interval_minutes: int
    input_text: str = ""
    enabled: bool = True


def get_db() -> Database:
    db = Database()
    db.init()
    return db


@router.get("/")
async def list_schedules(db: Database = Depends(get_db)):
    return [dict(row) for row in db.list_schedules()]


@router.post("/")
async def create_schedule(schedule: ScheduleCreate, db: Database = Depends(get_db)):
    try:
        db.get_workflow(schedule.workflow_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    schedule_id = db.create_schedule(
        workflow_id=schedule.workflow_id,
        name=schedule.name,
        interval_minutes=schedule.interval_minutes,
        input_text=schedule.input_text,
    )
    return {"id": schedule_id, "message": "Schedule created successfully"}


@router.put("/{schedule_id}")
async def update_schedule(schedule_id: str, schedule: ScheduleUpdate, db: Database = Depends(get_db)):
    updated = db.update_schedule(
        schedule_id=schedule_id,
        name=schedule.name,
        interval_minutes=schedule.interval_minutes,
        input_text=schedule.input_text,
        enabled=schedule.enabled,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"message": "Schedule updated successfully"}


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: str, db: Database = Depends(get_db)):
    deleted = db.delete_schedule(schedule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"message": "Schedule deleted successfully"}
