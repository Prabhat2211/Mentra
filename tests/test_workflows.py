from __future__ import annotations

from app.db import Database
from app.runtime.graph import run_workflow
from app.runtime.tools import StockQuote
from app.templates.registry import seed_default_workflows


def build_db(tmp_path):
    db = Database(tmp_path / "test.db")
    db.init()
    seed_default_workflows(db)
    return db


def workflow_id_for(db: Database, template_key: str) -> str:
    for workflow in db.list_workflows():
        if workflow["template_key"] == template_key:
            return workflow["id"]
    raise AssertionError(f"Missing workflow: {template_key}")


def test_research_summary_persists_run_messages_and_logs(tmp_path):
    db = build_db(tmp_path)
    workflow_id = workflow_id_for(db, "research_summary")

    result = run_workflow(
        workflow_id=workflow_id,
        user_input="Summarize AI agents for customer support.",
        db=db,
    )

    assert result.status == "completed"
    assert "Research summary" in result.output
    assert len(db.list_messages()) >= 2
    logs = db.list_logs()
    assert any(row["event"] == "workflow.completed" for row in logs)
    assert any(row["event"] == "llm.call.completed" for row in logs)


def test_financial_assistant_formats_stock_reply_with_mocked_quote(tmp_path, monkeypatch):
    db = build_db(tmp_path)
    workflow_id = workflow_id_for(db, "financial_assistant")

    def fake_quote(query: str) -> StockQuote:
        assert query == "AAPL"
        return StockQuote(
            symbol="AAPL",
            name="Apple Inc.",
            price=189.98,
            currency="USD",
            change_percent=1.24,
            market_cap=2_910_000_000_000,
            volume=48_200_000,
            day_low=187.40,
            day_high=190.21,
            fifty_two_week_low=150.00,
            fifty_two_week_high=205.00,
        )

    monkeypatch.setattr("app.runtime.graph.get_stock_quote", fake_quote)

    result = run_workflow(
        workflow_id=workflow_id,
        user_input="What is Apple's stock price?",
        source_channel="telegram",
        external_user_id="123",
        db=db,
    )

    assert result.status == "completed"
    assert "Apple Inc. (AAPL)" in result.output
    assert "This is market data only" in result.output
    messages = db.list_messages()
    assert any(row["channel"] == "telegram" for row in messages)
    assert any(row["event"] == "llm.call.completed" for row in db.list_logs())


def test_financial_assistant_resolves_asml_in_fallback_mode(tmp_path, monkeypatch):
    db = build_db(tmp_path)
    workflow_id = workflow_id_for(db, "financial_assistant")

    def fake_quote(query: str) -> StockQuote:
        assert query == "ASML"
        return StockQuote(
            symbol="ASML",
            name="ASML Holding N.V.",
            price=721.50,
            currency="USD",
            change_percent=-0.42,
            market_cap=285_000_000_000,
            volume=1_200_000,
            day_low=718.00,
            day_high=730.00,
            fifty_two_week_low=580.00,
            fifty_two_week_high=1_110.00,
        )

    monkeypatch.setattr("app.runtime.graph.get_stock_quote", fake_quote)

    result = run_workflow(
        workflow_id=workflow_id,
        user_input="What is asml stock price?",
        source_channel="telegram",
        db=db,
    )

    assert result.status == "completed"
    assert "ASML Holding N.V. (ASML)" in result.output
    messages = db.list_messages()
    assert any(row["from_agent_id"] == "company_extractor_agent" for row in messages)
    assert any(row["from_agent_id"] == "ticker_resolver_agent" for row in messages)
