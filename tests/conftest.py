from __future__ import annotations

import json

import pytest

from app.config import Settings


def _mock_gemini(prompt: str, model: str, api_key: str | None = None) -> dict:
    prompt_lower = prompt.lower()
    is_asml = "asml" in prompt_lower and "apple" not in prompt_lower
    if "is_stock_query" in prompt:
        return {"text": '{"is_stock_query": true, "reason": "mocked"}', "input_tokens": 5, "output_tokens": 5}
    if "company_or_ticker" in prompt:
        if is_asml:
            return {"text": '{"company_or_ticker": "ASML", "confidence": 0.95}', "input_tokens": 5, "output_tokens": 5}
        return {"text": '{"company_or_ticker": "Apple", "confidence": 0.95}', "input_tokens": 5, "output_tokens": 5}
    if "ticker" in prompt and "company_name" in prompt:
        if is_asml:
            return {"text": '{"ticker": "ASML", "company_name": "ASML Holding N.V.", "confidence": 0.95}', "input_tokens": 5, "output_tokens": 5}
        return {"text": '{"ticker": "AAPL", "company_name": "Apple Inc.", "confidence": 0.95}', "input_tokens": 5, "output_tokens": 5}
    if "research summarizer" in prompt_lower:
        return {"text": "Research summary for: the user query", "input_tokens": 5, "output_tokens": 5}
    if "format this stock quote" in prompt_lower:
        name = "ASML Holding N.V. (ASML)" if is_asml else "Apple Inc. (AAPL)"
        return {
            "text": f"{name}\n\nPrice: $189.98\nToday: +1.24%\nThis is market data only, not financial advice.",
            "input_tokens": 5,
            "output_tokens": 5,
        }
    return {"text": f"Mocked response", "input_tokens": 5, "output_tokens": 5}


@pytest.fixture(autouse=True)
def mock_gemini(monkeypatch):
    monkeypatch.setattr(
        "app.runtime.llm.settings",
        Settings(llm_provider="gemini", gemini_api_key="test-key"),
    )
    monkeypatch.setattr("app.runtime.llm._generate_with_gemini", _mock_gemini)

