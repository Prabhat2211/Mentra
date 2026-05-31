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


def test_active_llm_status_reports_groq_when_key_is_configured():
    status = active_llm_status(
        Settings(
            llm_provider="groq",
            groq_api_key="groq-test-key",
            groq_model="gpt-oss-120B",
        )
    )

    assert status == {
        "provider": "groq",
        "model": "gpt-oss-120B",
        "mode": "llm",
        "configured": True,
    }


def test_active_llm_status_reports_unconfigured_when_gemini_key_is_missing():
    status = active_llm_status(
        Settings(
            llm_provider="gemini",
            gemini_api_key=None,
            gemini_model="gemini-2.5-flash-lite",
        )
    )

    assert status["provider"] == "gemini"
    assert status["mode"] == "unconfigured"
    assert status["configured"] is False

