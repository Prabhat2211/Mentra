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
    provider = getattr(active_settings, "llm_provider", "groq").lower()
    model = getattr(active_settings, f"{provider}_model", "unknown")
    if provider == "groq":
        api_key = getattr(active_settings, "groq_api_key", None)
        model = getattr(active_settings, "groq_model", "gpt-oss-120B")
    elif provider == "gemini":
        api_key = getattr(active_settings, "gemini_api_key", None)
        model = getattr(active_settings, "gemini_model", "gemini-2.5-flash-lite")
    elif provider == "openai":
        api_key = getattr(active_settings, "openai_api_key", None)
        model = getattr(active_settings, "openai_model", "gpt-4o-mini")
    else:
        api_key = None
    return {
        "provider": provider,
        "model": model,
        "mode": "llm" if api_key else "unconfigured",
        "configured": bool(api_key),
    }


def _resolve_llm_config(
    active_settings: Settings | None = None,
    agent_llm_provider: str | None = None,
    agent_llm_api_key: str | None = None,
    agent_llm_model: str | None = None,
) -> tuple[str, str, str]:
    active_settings = active_settings or settings
    provider = (agent_llm_provider or getattr(active_settings, "llm_provider", "groq")).lower()
    if provider == "groq":
        api_key = agent_llm_api_key or getattr(active_settings, "groq_api_key", None) or ""
        model = agent_llm_model or getattr(active_settings, "groq_model", "gpt-oss-120B")
    elif provider == "gemini":
        api_key = agent_llm_api_key or getattr(active_settings, "gemini_api_key", None) or ""
        model = agent_llm_model or getattr(active_settings, "gemini_model", "gemini-2.5-flash-lite")
    elif provider == "openai":
        api_key = agent_llm_api_key or getattr(active_settings, "openai_api_key", None) or ""
        model = agent_llm_model or getattr(active_settings, "openai_model", "gpt-4o-mini")
    else:
        raise RuntimeError(f"Unsupported LLM provider: {provider}")
    if not api_key:
        raise RuntimeError(
            f"No API key configured for LLM provider '{provider}'. "
            f"Set {provider.upper()}_API_KEY in .env or configure per-agent keys."
        )
    return provider, api_key, model


def generate_text(
    *,
    node: str,
    task: str,
    prompt: str,
    db: Database | None = None,
    run_id: str | None = None,
    active_settings: Settings | None = None,
    agent_llm_provider: str | None = None,
    agent_llm_api_key: str | None = None,
    agent_llm_model: str | None = None,
) -> LLMResponse:
    provider, api_key, model = _resolve_llm_config(
        active_settings, agent_llm_provider, agent_llm_api_key, agent_llm_model
    )
    base_url = getattr(active_settings or settings, "groq_base_url", "https://api.groq.com/openai/v1") if provider == "groq" else None

    start = time.perf_counter()
    if db:
        db.add_log(
            run_id=run_id,
            event="llm.call.started",
            payload={"provider": provider, "model": model, "mode": "llm", "node": node, "task": task},
        )

    if provider == "groq":
        response = _generate_with_openai_compat(prompt, model, api_key, base_url or "https://api.groq.com/openai/v1")
    elif provider == "gemini":
        response = _generate_with_gemini(prompt, model, api_key)
    elif provider == "openai":
        response = _generate_with_openai_compat(prompt, model, api_key, "https://api.openai.com/v1")
    else:
        raise RuntimeError(f"Unsupported LLM provider: {provider}")

    latency_ms = int((time.perf_counter() - start) * 1000)
    result = LLMResponse(
        text=response["text"],
        provider=provider,
        model=model,
        mode="llm",
        latency_ms=latency_ms,
        input_tokens=response.get("input_tokens"),
        output_tokens=response.get("output_tokens"),
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
    agent_llm_provider: str | None = None,
    agent_llm_api_key: str | None = None,
    agent_llm_model: str | None = None,
) -> dict[str, Any]:
    active_settings = active_settings or settings
    response = generate_text(
        node=node,
        task=task,
        prompt=prompt,
        db=db,
        run_id=run_id,
        active_settings=active_settings,
        agent_llm_provider=agent_llm_provider,
        agent_llm_api_key=agent_llm_api_key,
        agent_llm_model=agent_llm_model,
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


def _generate_with_openai_compat(prompt: str, model: str, api_key: str, base_url: str) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    choice = response.choices[0]
    return {
        "text": choice.message.content or "",
        "input_tokens": response.usage.prompt_tokens if response.usage else None,
        "output_tokens": response.usage.completion_tokens if response.usage else None,
    }


def _generate_with_gemini(prompt: str, model: str, api_key: str | None = None) -> dict[str, Any]:
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("Install google-genai to use Gemini models.") from exc

    # Use provided API key or fall back to settings
    from app.config import settings as global_settings
    key = api_key or global_settings.gemini_api_key
    
    if not key:
        raise RuntimeError("No Gemini API key provided.")
    
    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model=model,
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
