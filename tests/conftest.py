from __future__ import annotations

import pytest

from app.config import Settings


@pytest.fixture(autouse=True)
def force_fallback_llm(monkeypatch):
    monkeypatch.setattr(
        "app.runtime.llm.settings",
        Settings(llm_provider="fallback"),
    )

