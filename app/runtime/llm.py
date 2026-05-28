from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from app.config import Settings, settings
from app.db import Database


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model: str
    mode: str
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None


def active_llm_status(active_settings: Settings | None = None) -> dict[str, str | bool]:
    active_settings = active_settings or settings
    provider = getattr(active_settings, "llm_provider", "fallback")
    gemini_api_key = getattr(active_settings, "gemini_api_key", None)
    gemini_model = getattr(active_settings, "gemini_model", "gemini-2.5-flash-lite")
    if provider == "gemini" and gemini_api_key:
        return {
            "provider": "gemini",
            "model": gemini_model,
            "mode": "llm",
            "configured": True,
        }
    if provider == "gemini":
        return {
            "provider": "gemini",
            "model": gemini_model,
            "mode": "fallback",
            "configured": False,
        }
    return {
        "provider": "fallback",
        "model": "deterministic-python",
        "mode": "fallback",
        "configured": True,
    }


def generate_text(
    *,
    node: str,
    task: str,
    prompt: str,
    fallback_text: str,
    db: Database | None = None,
    run_id: str | None = None,
    active_settings: Settings | None = None,
) -> LLMResponse:
    active_settings = active_settings or settings
    status = active_llm_status(active_settings)
    start = time.perf_counter()
    if db:
        db.add_log(
            run_id=run_id,
            event="llm.call.started",
            payload={
                "provider": status["provider"],
                "model": status["model"],
                "mode": status["mode"],
                "node": node,
                "task": task,
            },
        )

    if status["provider"] == "gemini" and status["configured"]:
        response = _generate_with_gemini(prompt, active_settings)
        latency_ms = int((time.perf_counter() - start) * 1000)
        result = LLMResponse(
            text=response["text"],
            provider="gemini",
            model=active_settings.gemini_model,
            mode="llm",
            latency_ms=latency_ms,
            input_tokens=response.get("input_tokens"),
            output_tokens=response.get("output_tokens"),
        )
    else:
        latency_ms = int((time.perf_counter() - start) * 1000)
        result = LLMResponse(
            text=fallback_text,
            provider=str(status["provider"]),
            model=str(status["model"]),
            mode="fallback",
            latency_ms=latency_ms,
        )

    if db:
        db.add_log(
            run_id=run_id,
            event="llm.call.completed",
            payload={
                "provider": result.provider,
                "model": result.model,
                "mode": result.mode,
                "node": node,
                "task": task,
                "latency_ms": result.latency_ms,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            },
        )
    return result


def generate_json(
    *,
    node: str,
    task: str,
    prompt: str,
    fallback_data: dict[str, Any],
    db: Database | None = None,
    run_id: str | None = None,
    active_settings: Settings | None = None,
) -> dict[str, Any]:
    active_settings = active_settings or settings
    response = generate_text(
        node=node,
        task=task,
        prompt=prompt,
        fallback_text=json.dumps(fallback_data),
        db=db,
        run_id=run_id,
        active_settings=active_settings,
    )
    try:
        data = json.loads(_strip_json_fence(response.text))
    except json.JSONDecodeError:
        data = fallback_data
    data["_llm"] = {
        "provider": response.provider,
        "model": response.model,
        "mode": response.mode,
        "latency_ms": response.latency_ms,
    }
    return data


def _generate_with_gemini(prompt: str, active_settings: Settings) -> dict[str, Any]:
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("Install google-genai to use Gemini models.") from exc

    client = genai.Client(api_key=active_settings.gemini_api_key)
    response = client.models.generate_content(
        model=active_settings.gemini_model,
        contents=prompt,
    )
    usage = getattr(response, "usage_metadata", None)
    return {
        "text": getattr(response, "text", "") or "",
        "input_tokens": getattr(usage, "prompt_token_count", None) if usage else None,
        "output_tokens": getattr(usage, "candidates_token_count", None) if usage else None,
    }


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```json"):
        stripped = stripped.removeprefix("```json").strip()
    elif stripped.startswith("```"):
        stripped = stripped.removeprefix("```").strip()
    if stripped.endswith("```"):
        stripped = stripped.removesuffix("```").strip()
    return stripped
