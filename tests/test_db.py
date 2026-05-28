from __future__ import annotations

from app.db import Database


def test_agent_creation_persists_expected_fields(tmp_path):
    db = Database(tmp_path / "test.db")
    db.init()

    agent_id = db.create_agent(
        name="Ticker Resolver",
        role="Resolve tickers",
        system_prompt="Find exact stock symbols.",
        model="gpt-4o-mini",
        tools=["get_stock_quote"],
        channel="telegram",
        memory_enabled=True,
        guardrails="Do not give financial advice.",
    )

    agents = db.list_agents()
    assert agents[0]["id"] == agent_id
    assert agents[0]["name"] == "Ticker Resolver"
    assert agents[0]["channel"] == "telegram"
    assert agents[0]["memory_enabled"] == 1

