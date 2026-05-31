from __future__ import annotations

from app.runtime.tools import save_note, web_search_stub
from app.runtime.graph import _pick_tool_query, WorkflowState


def test_web_search_stub_returns_list():
    results = web_search_stub("test query")
    assert isinstance(results, list)
    assert len(results) >= 1
    assert any("test query" in r for r in results)


def test_save_note_returns_string():
    result = save_note("hello world")
    assert isinstance(result, str)
    assert "hello world" in result


def test_save_note_truncates_long_input():
    long = "x" * 200
    result = save_note(long)
    assert len(result) == 132  # "Saved note: " (12) + 120 chars


def test_pick_tool_query_uses_output_when_short_and_uppercase():
    state = WorkflowState(
        workflow_id="test", run_id="test", user_input="What is apple stock",
        source_channel="ui", output="AAPL",
    )
    assert _pick_tool_query(state) == "AAPL"


def test_pick_tool_query_falls_back_to_user_input():
    state = WorkflowState(
        workflow_id="test", run_id="test",
        user_input="What is Apple's stock price?",
        source_channel="ui", output="",
    )
    assert _pick_tool_query(state) == "What is Apple's stock price?"


def test_pick_tool_query_uses_user_input_when_output_is_long():
    state = WorkflowState(
        workflow_id="test", run_id="test",
        user_input="Apple stock",
        source_channel="ui",
        output="Apple Inc. is a technology company that makes iPhones and Macs.",
    )
    assert _pick_tool_query(state) == "Apple stock"
