from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from app.db import Database
from app.models import WorkflowRunResult
from app.runtime.llm import generate_json, generate_text
from app.runtime.tools import (
    extract_company_or_ticker,
    format_stock_quote,
    get_stock_quote,
    is_stock_query,
    resolve_ticker,
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
    template = get_template(workflow["template_key"])
    decode_workflow_config(workflow)
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

    try:
        database.add_log(run_id=run_id, event="workflow.started", payload={"template": template.key})
        final_state = _coerce_state(_run_with_langgraph_if_available(template.key, state, database))
        token_count = _estimate_tokens(user_input + " " + final_state.output)
        estimated_cost = token_count * 0.00000015
        database.complete_run(
            run_id=run_id,
            status="completed",
            output=final_state.output,
            token_count=token_count,
            estimated_cost=estimated_cost,
        )
        database.add_log(
            run_id=run_id,
            event="workflow.completed",
            payload={"token_count": token_count, "estimated_cost": estimated_cost},
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
        database.complete_run(
            run_id=run_id,
            status="failed",
            output=str(exc),
            token_count=0,
            estimated_cost=0,
        )
        database.add_log(run_id=run_id, event="workflow.failed", level="error", payload={"error": str(exc)})
        raise


def _run_with_langgraph_if_available(template_key: str, state: WorkflowState, db: Database) -> WorkflowState | dict[str, Any]:
    nodes = _nodes_for_template(template_key)
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
            db.add_log(run_id=state.run_id, event="node.started", payload={"node": node_name})
            current = node(current, db)
            db.add_log(run_id=state.run_id, event="node.completed", payload={"node": node_name})
        return current


def _coerce_state(state: WorkflowState | dict[str, Any]) -> WorkflowState:
    if isinstance(state, WorkflowState):
        return state
    return WorkflowState(**state)


def _nodes_for_template(template_key: str) -> list[tuple[str, Node]]:
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


def _research_agent(state: WorkflowState, db: Database) -> WorkflowState:
    findings = web_search_stub(state.user_input)
    state.notes.extend(findings)
    content = "\n".join(f"- {finding}" for finding in findings)
    db.add_message(
        workflow_id=state.workflow_id,
        run_id=state.run_id,
        channel="agent",
        from_agent_id="research_agent",
        to_agent_id="summarizer_agent",
        content=content,
        metadata={"node": "research_agent"},
    )
    return state


def _summarizer_agent(state: WorkflowState, db: Database) -> WorkflowState:
    bullets = "\n".join(f"- {note}" for note in state.notes)
    fallback = f"Research summary for: {state.user_input}\n\n{bullets}"
    response = generate_text(
        node="summarizer_agent",
        task="research_summary",
        prompt=(
            "You are a concise research summarizer. Write a useful answer from these notes.\n\n"
            f"User request: {state.user_input}\n\nNotes:\n{bullets}"
        ),
        fallback_text=fallback,
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
    fallback_detected = is_stock_query(state.user_input)
    llm_result = generate_json(
        node="query_detector_agent",
        task="classify_stock_query",
        prompt=(
            "Classify whether this Telegram message is asking for stock market data. "
            "Return only JSON with keys is_stock_query and reason.\n\n"
            f"Message: {state.user_input}"
        ),
        fallback_data={"is_stock_query": fallback_detected, "reason": "deterministic keyword classifier"},
        db=db,
        run_id=state.run_id,
    )
    detected = bool(llm_result.get("is_stock_query", fallback_detected))
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
    fallback_ticker = resolve_ticker(str(target))
    llm_result = generate_json(
        node="ticker_resolver_agent",
        task="resolve_ticker",
        prompt=(
            "Resolve this extracted company name or ticker to the exact Yahoo Finance stock symbol. "
            "Return only JSON with keys ticker, company_name, and confidence.\n\n"
            f"Extracted target: {target}\nOriginal message: {state.user_input}"
        ),
        fallback_data={
            "ticker": fallback_ticker,
            "company_name": target,
            "confidence": 0.5 if fallback_ticker else 0,
        },
        db=db,
        run_id=state.run_id,
    )
    ticker = llm_result.get("ticker") or fallback_ticker
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
    fallback_target = extract_company_or_ticker(state.user_input)
    llm_result = generate_json(
        node="company_extractor_agent",
        task="extract_company_or_ticker",
        prompt=(
            "Extract the company name or ticker symbol the user is asking about. "
            "Return only JSON with keys company_or_ticker and confidence. "
            "If no company or ticker is present, company_or_ticker should be null.\n\n"
            f"Message: {state.user_input}"
        ),
        fallback_data={
            "company_or_ticker": fallback_target,
            "confidence": 0.5 if fallback_target else 0,
        },
        db=db,
        run_id=state.run_id,
    )
    target = llm_result.get("company_or_ticker") or fallback_target
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
        from app.runtime.tools import StockQuote

        quote = StockQuote(**quote_data)
        fallback = format_stock_quote(quote)
        response = generate_text(
            node="response_formatter_agent",
            task="format_stock_reply",
            prompt=(
                "Format this stock quote as a clean Telegram reply. Keep it short, clear, "
                "and include this exact disclaimer meaning: market data only, not financial advice.\n\n"
                f"Quote data: {quote_data}"
            ),
            fallback_text=fallback,
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
