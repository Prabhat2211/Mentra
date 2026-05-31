from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from app.db import Database
from app.models import WorkflowRunResult
from app.runtime.llm import generate_json, generate_text
from app.runtime.tools import (
    get_stock_quote,
    save_note,
    web_search_stub,
)
from app.templates.registry import decode_workflow_config, get_template


@dataclass
class WorkflowState:
    workflow_id: str
    run_id: str
    user_input: str
    source_channel: str
    external_user_id: str | None = None
    notes: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    output: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


Node = Callable[[WorkflowState, Database], WorkflowState]


def run_workflow(
    workflow_id: str,
    user_input: str,
    source_channel: str = "ui",
    external_user_id: str | None = None,
    db: Database | None = None,
) -> WorkflowRunResult:
    database = db or Database()
    database.init()
    workflow = database.get_workflow(workflow_id)
    is_custom = bool(workflow["is_custom"])
    template_key = workflow["template_key"]

    if is_custom:
        nodes_json = workflow["nodes_json"]
        if not nodes_json:
            raise ValueError("Custom workflow has no nodes")
        import json as _json
        custom_nodes = _json.loads(nodes_json)
        if not custom_nodes:
            raise ValueError("Custom workflow has no nodes")
        node_pairs = _build_custom_nodes(custom_nodes, database)
    else:
        template = get_template(template_key)
        config = decode_workflow_config(workflow)
        agent_assignments = config.get("agent_assignments", {})
        node_pairs = _nodes_for_template(template_key, agent_assignments, database)

    run_id = database.create_run(workflow_id=workflow_id, user_input=user_input)
    state = WorkflowState(
        workflow_id=workflow_id,
        run_id=run_id,
        user_input=user_input,
        source_channel=source_channel,
        external_user_id=external_user_id,
    )
    database.add_message(
        workflow_id=workflow_id,
        run_id=run_id,
        channel=source_channel,
        content=user_input,
        metadata={"direction": "inbound", "external_user_id": external_user_id},
    )

    wf_t0 = time.perf_counter()
    try:
        tmpl = template_key if not is_custom else "custom"
        database.add_log(run_id=run_id, event="workflow.started", payload={"template": tmpl})
        final_state = _coerce_state(_run_with_langgraph_if_available(node_pairs, state, database))
        duration_ms = int((time.perf_counter() - wf_t0) * 1000)
        token_count = _estimate_tokens(user_input + " " + final_state.output)
        estimated_cost = token_count * 0.00000015
        database.complete_run(
            run_id=run_id,
            status="completed",
            output=final_state.output,
            token_count=token_count,
            estimated_cost=estimated_cost,
            duration_ms=duration_ms,
        )
        database.add_log(
            run_id=run_id,
            event="workflow.completed",
            payload={"token_count": token_count, "estimated_cost": estimated_cost, "duration_ms": duration_ms},
        )
        return WorkflowRunResult(
            run_id=run_id,
            workflow_id=workflow_id,
            status="completed",
            output=final_state.output,
            token_count=token_count,
            estimated_cost=estimated_cost,
        )
    except Exception as exc:
        duration_ms = int((time.perf_counter() - wf_t0) * 1000)
        database.complete_run(
            run_id=run_id,
            status="failed",
            output=str(exc),
            token_count=0,
            estimated_cost=0,
            duration_ms=duration_ms,
        )
        database.add_log(run_id=run_id, event="workflow.failed", level="error", payload={"error": str(exc), "duration_ms": duration_ms})
        raise


def _run_with_langgraph_if_available(
    nodes: list[tuple[str, Node]], state: WorkflowState, db: Database
) -> WorkflowState | dict[str, Any]:
    try:
        from langgraph.graph import END, StateGraph

        graph = StateGraph(WorkflowState)
        for name, node in nodes:
            graph.add_node(name, lambda current_state, node=node: node(current_state, db))
        graph.set_entry_point(nodes[0][0])
        for (current_name, _), (next_name, _) in zip(nodes, nodes[1:], strict=False):
            graph.add_edge(current_name, next_name)
        graph.add_edge(nodes[-1][0], END)
        compiled = graph.compile()
        return compiled.invoke(state)
    except Exception:
        current = state
        for node_name, node in nodes:
            t0 = time.perf_counter()
            db.add_log(run_id=state.run_id, event="node.started", payload={"node": node_name})
            current = node(current, db)
            duration_ms = int((time.perf_counter() - t0) * 1000)
            db.add_log(run_id=state.run_id, event="node.completed", payload={"node": node_name, "duration_ms": duration_ms})
        return current


def _build_custom_nodes(custom_nodes: list[dict[str, Any]], database: Database) -> list[tuple[str, Node]]:
    agents = {dict(row)["id"]: dict(row) for row in database.list_agents()}
    pairs: list[tuple[str, Node]] = []
    for node_info in custom_nodes:
        agent_id = node_info.get("agent_id")
        node_id = node_info.get("id", f"agent-{agent_id}")
        agent = agents.get(agent_id)
        if agent is None:
            raise ValueError(f"Agent {agent_id} not found for node '{node_info.get('label', 'Agent')}'")
        pairs.append(_build_agent_node(node_id, agent))
    return pairs


def _coerce_state(state: WorkflowState | dict[str, Any]) -> WorkflowState:
    if isinstance(state, WorkflowState):
        return state
    return WorkflowState(**state)


def _nodes_for_template(
    template_key: str,
    agent_assignments: dict[str, str] | None = None,
    database: Database | None = None,
) -> list[tuple[str, Node]]:
    if agent_assignments and database:
        agents = {dict(row)["id"]: dict(row) for row in database.list_agents()}
        pairs: list[tuple[str, Node]] = []
        template = get_template(template_key)
        for node_name in template.nodes:
            agent_id = agent_assignments.get(node_name)
            if agent_id and agent_id in agents:
                pairs.append(_build_agent_node(node_name, agents[agent_id]))
            else:
                pairs.append(_hardcoded_node(template_key, node_name))
        return pairs

    if template_key == "research_summary":
        return [
            ("research_agent", _research_agent),
            ("summarizer_agent", _summarizer_agent),
        ]
    if template_key == "financial_assistant":
        return [
            ("query_detector_agent", _query_detector_agent),
            ("company_extractor_agent", _company_extractor_agent),
            ("ticker_resolver_agent", _ticker_resolver_agent),
            ("market_data_agent", _market_data_agent),
            ("response_formatter_agent", _response_formatter_agent),
        ]
    raise ValueError(f"Unsupported template: {template_key}")


def _hardcoded_node(template_key: str, node_name: str) -> Node:
    _map: dict[str, dict[str, Node]] = {
        "research_summary": {
            "research_agent": _research_agent,
            "summarizer_agent": _summarizer_agent,
        },
        "financial_assistant": {
            "query_detector_agent": _query_detector_agent,
            "company_extractor_agent": _company_extractor_agent,
            "ticker_resolver_agent": _ticker_resolver_agent,
            "market_data_agent": _market_data_agent,
            "response_formatter_agent": _response_formatter_agent,
        },
    }
    return _map[template_key][node_name]


def _pick_tool_query(state: WorkflowState) -> str:
    out = state.output.strip() if state.output else ""
    if out and (out.isupper() or len(out.split()) <= 5):
        return out
    return state.user_input


PERSONALITY_TONE_MAP = {
    "polite":       "Use a polite tone. Say please and thank you. Be courteous.",
    "rude":         "Be direct and blunt. Skip pleasantries. Be concise.",
    "formal":       "Use formal language. Avoid slang, contractions, or casual expressions.",
    "casual":       "Use a casual, conversational tone. Be relaxed and friendly.",
    "friendly":     "Be warm, approachable, and encouraging.",
    "professional": "Maintain a neutral, business-appropriate tone. Be clear and precise.",
    "sarcastic":    "Use light sarcasm and wit, but keep the information accurate.",
}


def _execute_tools(agent: dict[str, Any], state: WorkflowState, db: Database) -> str:
    """Execute tools configured for an agent and return formatted results."""
    import json

    tools = json.loads(agent.get("tools_json") or "[]")
    results: list[str] = []

    for tool_name in tools:
        try:
            if tool_name == "web_search_stub":
                out = web_search_stub(state.user_input)
                results.append(f"[web_search_stub]\n" + "\n".join(f"- {r}" for r in out))
                db.add_log(run_id=state.run_id, event="tool.call.completed", payload={"tool": tool_name, "result_count": len(out)})
            elif tool_name == "get_stock_quote":
                query = _pick_tool_query(state)
                out = get_stock_quote(query)
                results.append(f"[get_stock_quote]\n{out.name} ({out.symbol}): ${out.price}" if out.price else f"[get_stock_quote]\n{out.symbol}: no data")
                db.add_log(run_id=state.run_id, event="tool.call.completed", payload={"tool": tool_name, "symbol": out.symbol})
            elif tool_name == "save_note":
                content = state.output or state.user_input
                out = save_note(content)
                results.append(f"[save_note]\n{out}")
                db.add_log(run_id=state.run_id, event="tool.call.completed", payload={"tool": tool_name})
        except Exception as exc:
            results.append(f"[{tool_name}]\nError: {exc}")
            db.add_log(run_id=state.run_id, event="tool.call.failed", level="error", payload={"tool": tool_name, "error": str(exc)})

    if not results:
        return ""
    return "\n\n=== Tool Results ===\n" + "\n\n".join(results)


def _build_agent_node(node_name: str, agent: dict[str, Any]) -> tuple[str, Node]:
    node_id = node_name
    node_label = agent.get("name", node_name)
    system_prompt = agent.get("system_prompt", "")
    personality = agent.get("personality", "professional")
    guardrails = agent.get("guardrails", "")
    memory_enabled = bool(agent.get("memory_enabled", False))

    def _exec(state: WorkflowState, db: Database) -> WorkflowState:
        tool_results = _execute_tools(agent, state, db)
        prompt_parts: list[str] = []

        personality_instruction = PERSONALITY_TONE_MAP.get(personality, PERSONALITY_TONE_MAP["professional"])
        prompt_parts.append(personality_instruction)

        prompt_parts.append(system_prompt or f"You are a {node_label}.")

        if guardrails:
            prompt_parts.append(f"Guardrails: {guardrails}")

        if memory_enabled and hasattr(state, "messages") and state.messages:
            history = "\n".join(f"- {m}" for m in state.messages[-5:])
            prompt_parts.append(f"Conversation history:\n{history}")

        prompt_parts.append(f"User input: {state.user_input}")
        prompt_parts.append(f"Previous output: {state.output or '(none)'}")
        if tool_results:
            prompt_parts.append(tool_results)
        prompt_parts.append("Respond helpfully based on your role and the tool results above.")

        response = generate_text(
            node=node_id,
            task=node_label,
            prompt="\n\n".join(prompt_parts),
            db=db,
            run_id=state.run_id,
        )
        state.output = response.text
        if memory_enabled:
            state.messages.append(f"{node_label}: {response.text}")
        db.add_message(
            workflow_id=state.workflow_id,
            run_id=state.run_id,
            channel="agent",
            from_agent_id=node_id,
            content=state.output,
            metadata={
                "node": node_id,
                "label": node_label,
                "agent_id": agent.get("id"),
                "personality": personality,
                "llm": {"provider": response.provider, "model": response.model, "mode": response.mode},
            },
        )
        return state
    return (node_id, _exec)


def _research_agent(state: WorkflowState, db: Database) -> WorkflowState:
    findings = web_search_stub(state.user_input)
    state.notes.extend(findings)
    bullets = "\n".join(f"- {finding}" for finding in findings)
    response = generate_text(
        node="research_agent",
        task="research_gathering",
        prompt=(
            "You are a research agent. Given a user query and search results below, "
            "produce structured notes covering key facts, trends, and risks.\n\n"
            f"User query: {state.user_input}\n\nSearch results:\n{bullets}"
        ),
        db=db,
        run_id=state.run_id,
    )
    state.output = response.text
    db.add_message(
        workflow_id=state.workflow_id,
        run_id=state.run_id,
        channel="agent",
        from_agent_id="research_agent",
        to_agent_id="summarizer_agent",
        content=state.output,
        metadata={"node": "research_agent", "llm": {"provider": response.provider, "model": response.model, "mode": response.mode}},
    )
    return state


def _summarizer_agent(state: WorkflowState, db: Database) -> WorkflowState:
    bullets = "\n".join(f"- {note}" for note in state.notes)
    response = generate_text(
        node="summarizer_agent",
        task="research_summary",
        prompt=(
            "You are a concise research summarizer. Write a useful answer from these notes.\n\n"
            f"User request: {state.user_input}\n\nNotes:\n{bullets}"
        ),
        db=db,
        run_id=state.run_id,
    )
    state.output = response.text
    db.add_message(
        workflow_id=state.workflow_id,
        run_id=state.run_id,
        channel="agent",
        from_agent_id="summarizer_agent",
        content=state.output,
        metadata={
            "node": "summarizer_agent",
            "direction": "outbound",
            "llm": {
                "provider": response.provider,
                "model": response.model,
                "mode": response.mode,
            },
        },
    )
    return state


def _query_detector_agent(state: WorkflowState, db: Database) -> WorkflowState:
    llm_result = generate_json(
        node="query_detector_agent",
        task="classify_stock_query",
        prompt=(
            "Classify whether this Telegram message is asking for stock market data. "
            "Return only JSON with keys is_stock_query and reason.\n\n"
            f"Message: {state.user_input}"
        ),
        fallback_data={"is_stock_query": False, "reason": "json parse error"},
        db=db,
        run_id=state.run_id,
    )
    detected = bool(llm_result.get("is_stock_query"))
    state.metadata["is_stock_query"] = detected
    content = "Stock query detected." if detected else "This does not look like a stock query."
    db.add_message(
        workflow_id=state.workflow_id,
        run_id=state.run_id,
        channel="agent",
        from_agent_id="query_detector_agent",
        to_agent_id="ticker_resolver_agent",
        content=content,
        metadata={
            "is_stock_query": detected,
            "reason": llm_result.get("reason"),
            "llm": llm_result.get("_llm"),
        },
    )
    if not detected:
        state.output = "I can help with stock quotes. Try asking about a company like Apple, Tesla, or NVIDIA."
    return state


def _ticker_resolver_agent(state: WorkflowState, db: Database) -> WorkflowState:
    if state.output:
        return state
    if not state.metadata.get("is_stock_query"):
        return state
    target = state.metadata.get("company_or_ticker") or state.user_input
    llm_result = generate_json(
        node="ticker_resolver_agent",
        task="resolve_ticker",
        prompt=(
            "Resolve this extracted company name or ticker to the exact Yahoo Finance stock symbol. "
            "Return only JSON with keys ticker, company_name, and confidence.\n\n"
            f"Extracted target: {target}\nOriginal message: {state.user_input}"
        ),
        fallback_data={"ticker": None, "company_name": target, "confidence": 0},
        db=db,
        run_id=state.run_id,
    )
    ticker = llm_result.get("ticker")
    ticker = str(ticker).upper() if ticker else None
    state.metadata["ticker"] = ticker
    db.add_message(
        workflow_id=state.workflow_id,
        run_id=state.run_id,
        channel="agent",
        from_agent_id="ticker_resolver_agent",
        to_agent_id="market_data_agent",
        content=f"Resolved ticker: {ticker or 'unknown'}",
        metadata={
            "ticker": ticker,
            "company_name": llm_result.get("company_name"),
            "confidence": llm_result.get("confidence"),
            "llm": llm_result.get("_llm"),
        },
    )
    if ticker is None:
        state.output = "I could not identify the exact stock ticker. Try including the company name or ticker."
    return state


def _company_extractor_agent(state: WorkflowState, db: Database) -> WorkflowState:
    if not state.metadata.get("is_stock_query"):
        return state
    llm_result = generate_json(
        node="company_extractor_agent",
        task="extract_company_or_ticker",
        prompt=(
            "Extract the company name or ticker symbol the user is asking about. "
            "Return only JSON with keys company_or_ticker and confidence. "
            "If no company or ticker is present, company_or_ticker should be null.\n\n"
            f"Message: {state.user_input}"
        ),
        fallback_data={"company_or_ticker": None, "confidence": 0},
        db=db,
        run_id=state.run_id,
    )
    target = llm_result.get("company_or_ticker")
    state.metadata["company_or_ticker"] = target
    db.add_message(
        workflow_id=state.workflow_id,
        run_id=state.run_id,
        channel="agent",
        from_agent_id="company_extractor_agent",
        to_agent_id="ticker_resolver_agent",
        content=f"Extracted company or ticker: {target or 'unknown'}",
        metadata={
            "company_or_ticker": target,
            "confidence": llm_result.get("confidence"),
            "llm": llm_result.get("_llm"),
        },
    )
    if target is None:
        state.output = "I could not find a company name or ticker in that message."
    return state


def _market_data_agent(state: WorkflowState, db: Database) -> WorkflowState:
    ticker = state.metadata.get("ticker")
    if not ticker:
        return state
    quote = get_stock_quote(ticker)
    state.metadata["quote"] = quote.__dict__
    db.add_message(
        workflow_id=state.workflow_id,
        run_id=state.run_id,
        channel="agent",
        from_agent_id="market_data_agent",
        to_agent_id="response_formatter_agent",
        content=f"Fetched market data for {quote.symbol}.",
        metadata={"quote": quote.__dict__},
    )
    return state


def _response_formatter_agent(state: WorkflowState, db: Database) -> WorkflowState:
    if state.output:
        return state
    quote_data = state.metadata.get("quote")
    if not quote_data:
        state.output = "I could not fetch stock data for that request."
    else:
        response = generate_text(
            node="response_formatter_agent",
            task="format_stock_reply",
            prompt=(
                "Format this stock quote as a clean Telegram reply. Keep it short, clear, "
                "and include this exact disclaimer meaning: market data only, not financial advice.\n\n"
                f"Quote data: {quote_data}"
            ),
            db=db,
            run_id=state.run_id,
        )
        state.output = response.text
        state.metadata["formatter_llm"] = {
            "provider": response.provider,
            "model": response.model,
            "mode": response.mode,
        }
    db.add_message(
        workflow_id=state.workflow_id,
        run_id=state.run_id,
        channel=state.source_channel,
        from_agent_id="response_formatter_agent",
        content=state.output,
        metadata={
            "direction": "outbound",
            "external_user_id": state.external_user_id,
            "llm": state.metadata.get("formatter_llm"),
        },
    )
    return state


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()) * 2)
