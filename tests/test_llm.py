from __future__ import annotations

from app.config import Settings
from app.runtime.llm import active_llm_status


def test_active_llm_status_reports_gemini_when_key_is_configured():
    status = active_llm_status(
        Settings(
            llm_provider="gemini",
            gemini_api_key="test-key",
            gemini_model="gemini-2.5-flash-lite",
        )
    )

    assert status == {
        "provider": "gemini",
        "model": "gemini-2.5-flash-lite",
        "mode": "llm",
        "configured": True,
    }


def test_active_llm_status_reports_fallback_when_gemini_key_is_missing():
    status = active_llm_status(
        Settings(
            llm_provider="gemini",
            gemini_api_key=None,
            gemini_model="gemini-2.5-flash-lite",
        )
    )

    assert status["provider"] == "gemini"
    assert status["mode"] == "fallback"
    assert status["configured"] is False

