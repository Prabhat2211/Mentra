from __future__ import annotations

from fastapi import APIRouter, Depends
from app.db import Database

router = APIRouter()


def get_db() -> Database:
    db = Database()
    db.init()
    return db


@router.get("/")
async def list_runs(limit: int = 25, db: Database = Depends(get_db)):
    rows = db.list_runs(limit=limit)
    return [dict(row) for row in rows]
