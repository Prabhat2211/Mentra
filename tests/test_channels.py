from __future__ import annotations

import pytest

from app.db import Database
from app.channels.telegram import resolve_default_workflow_id
from app.config import Settings


def test_resolve_default_workflow_id_uses_env_var(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.channels.telegram.settings",
        Settings(default_telegram_workflow_id="custom-id-123"),
    )
    db = Database(tmp_path / "test.db")
    db.init()
    result = resolve_default_workflow_id(db)
    assert result == "custom-id-123"


def test_resolve_default_workflow_id_falls_back_to_first_workflow(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.channels.telegram.settings",
        Settings(default_telegram_workflow_id=None),
    )
    db = Database(tmp_path / "test.db")
    db.init()
    wf_id = db.create_workflow(name="First WF", description="d", template_key="custom")
    result = resolve_default_workflow_id(db)
    assert result == wf_id


def test_resolve_default_workflow_id_raises_when_no_workflows(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.channels.telegram.settings",
        Settings(default_telegram_workflow_id=None),
    )
    db = Database(tmp_path / "test.db")
    db.init()
    with pytest.raises(RuntimeError, match="No workflows found"):
        resolve_default_workflow_id(db)
