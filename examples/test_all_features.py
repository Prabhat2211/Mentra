"""
Example: Test all features of the platform.

Run:   python examples/test_all_features.py

Prerequisites:
  - Valid GROQ_API_KEY in .env (or another LLM provider)
  - No agents/workflows in DB (optional, script cleans up after itself)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import Database
from app.runtime.graph import run_workflow
from app.templates.registry import seed_default_workflows


def print_header(text: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}")


def print_result(ok: bool, detail: str = "") -> None:
    mark = "✅" if ok else "❌"
    print(f"  {mark} {detail}" if detail else f"  {mark}")


# ──────────────────────────────────────────────
#  1. Create agents with different personalities
# ──────────────────────────────────────────────
print_header("1. Creating Agents with Different Personalities")

db = Database()
db.init()

research_agent_id = db.create_agent(
    name="Research Analyst",
    role="Deep research specialist",
    system_prompt=(
        "You are a research analyst. Given a topic, produce structured findings "
        "covering key facts, trends, expert opinions, and risks."
    ),
    model="gpt-oss-120B",
    tools=["web_search_stub", "save_note"],
    channel="ui",
    memory_enabled=True,
    guardrails="Do not fabricate data. If uncertain, say so.",
    personality="professional",
)
print_result(True, f"Research Analyst created: {research_agent_id[:8]}...")

summarizer_id = db.create_agent(
    name="Friendly Summarizer",
    role="Condenses research into a digestible answer",
    system_prompt="You take research notes and write a clear, friendly summary for a general audience.",
    model="gpt-oss-120B",
    tools=["save_note"],
    channel="ui",
    memory_enabled=False,
    guardrails="Keep it under 200 words.",
    personality="friendly",
)
print_result(True, f"Friendly Summarizer created: {summarizer_id[:8]}...")

ticker_agent_id = db.create_agent(
    name="Ticker Finder",
    role="Extracts stock tickers from questions",
    system_prompt="From the user's question, identify the company name and respond with ONLY the ticker symbol (e.g., AAPL, TSLA).",
    model="gpt-oss-120B",
    tools=[],
    channel="telegram",
    memory_enabled=False,
    guardrails="",
    personality="formal",
)
print_result(True, f"Ticker Finder created: {ticker_agent_id[:8]}...")

market_agent_id = db.create_agent(
    name="Market Data Provider",
    role="Fetches and formats stock data",
    system_prompt="You have live stock data. Present it clearly: name, ticker, price, change, market cap. End with: market data only, not financial advice.",
    model="gpt-oss-120B",
    tools=["get_stock_quote"],
    channel="telegram",
    memory_enabled=False,
    guardrails="Always include the disclaimer.",
    personality="polite",
)
print_result(True, f"Market Data Provider created: {market_agent_id[:8]}...")


# ──────────────────────────────────────────────
#  2. Create a template workflow with agent assignments
# ──────────────────────────────────────────────
print_header("2. Creating Template Workflow with Agent Assignments")

seed_default_workflows(db)
research_wf = None
for wf in db.list_workflows():
    if wf["template_key"] == "research_summary":
        research_wf = wf
        break

if research_wf:
    config = json.loads(research_wf["config_json"] or "{}")
    config["agent_assignments"] = {
        "research_agent": research_agent_id,
        "summarizer_agent": summarizer_id,
    }
    db.update_workflow(
        workflow_id=research_wf["id"],
        name=research_wf["name"],
        description=research_wf["description"],
        config=config,
    )
    print_result(True, f"Research Summary workflow assigned agents: {research_wf['id'][:8]}...")
else:
    print_result(False, "No research_summary workflow found to assign agents to")


# ──────────────────────────────────────────────
#  3. Create a custom drag-and-drop workflow
# ──────────────────────────────────────────────
print_header("3. Creating Custom Drag-and-Drop Workflow")

custom_wf_id = db.create_workflow(
    name="Stock Price Lookup",
    description="Custom two-step stock price workflow via the drag-and-drop builder",
    template_key="custom",
    is_custom=True,
    nodes=[
        {"id": "step-1", "agent_id": ticker_agent_id, "label": "Ticker Finder", "position": {"x": 100, "y": 100}},
        {"id": "step-2", "agent_id": market_agent_id, "label": "Market Data Provider", "position": {"x": 400, "y": 100}},
    ],
    edges=[
        {"source": "step-1", "target": "step-2"},
    ],
)
print_result(True, f"Custom Stock Price workflow: {custom_wf_id[:8]}...")


# ──────────────────────────────────────────────
#  4. Run the template research workflow
# ──────────────────────────────────────────────
print_header("4. Running Research Summary Workflow")

if research_wf:
    try:
        result = run_workflow(
            workflow_id=research_wf["id"],
            user_input="What are the benefits and risks of using AI in healthcare?",
            source_channel="ui",
            db=db,
        )
        print_result(result.status == "completed", f"Status: {result.status}")
        print(f"  Output preview: {result.output[:200]}...")
        print(f"  Tokens: {result.token_count}  Cost: ${result.estimated_cost:.6f}")
    except Exception as e:
        print_result(False, str(e)[:100])
else:
    print_result(False, "Cannot run — no research workflow")


# ──────────────────────────────────────────────
#  5. Run the custom stock workflow
# ──────────────────────────────────────────────
print_header("5. Running Custom Stock Price Workflow")

try:
    result = run_workflow(
        workflow_id=custom_wf_id,
        user_input="What is NVIDIA's stock price?",
        source_channel="telegram",
        db=db,
    )
    print_result(result.status == "completed", f"Status: {result.status}")
    print(f"  Output preview: {result.output[:300]}...")
    print(f"  Tokens: {result.token_count}  Cost: ${result.estimated_cost:.6f}")
except Exception as e:
    print_result(False, str(e)[:100])


# ──────────────────────────────────────────────
#  6. Verify logs, messages, and metrics
# ──────────────────────────────────────────────
print_header("6. Checking Logs, Messages, and Metrics")

runs = db.list_runs(limit=5)
logs = db.list_logs(limit=10)
messages = db.list_messages(limit=10)
metrics_agent_messages = sum(1 for m in messages if m.get("from_agent_id"))

print(f"  Runs recorded:      {len(runs)}")
print(f"  Log entries:        {len(logs)}")
print(f"  Messages:           {len(messages)}")
print(f"  Agent-to-agent msgs:{metrics_agent_messages}")

completed = sum(1 for r in runs if r["status"] == "completed")
rate = (completed / len(runs) * 100) if runs else 0
print(f"  Completion rate:    {rate:.0f}% ({completed}/{len(runs)})")

print(f"\n  Sample log events:")
for log in logs[:5]:
    print(f"    [{log['level']}] {log['event']}")

print(f"\n  Sample messages:")
for msg in messages[:5]:
    print(f"    [{msg['channel']}] {msg.get('from_agent_id', '')[:8] or 'user'} → {msg.get('to_agent_id', '')[:8] or 'user'}: {msg['content'][:60]}...")


# ──────────────────────────────────────────────
#  7. Check schedule creation
# ──────────────────────────────────────────────
print_header("7. Creating a Schedule")

schedule_id = db.create_schedule(
    workflow_id=custom_wf_id,
    name="Daily Stock Check",
    interval_minutes=1440,  # Every day
    input_text="What is Apple's stock price?",
)
print_result(True, f"Schedule created: {schedule_id[:8]}... (Every day)")

schedules = db.list_schedules()
print(f"  Total schedules: {len(schedules)}")


# ──────────────────────────────────────────────
#  Summary
# ──────────────────────────────────────────────
print_header("Summary")
print(f"  Agents created:     4")
print(f"  Workflows created:  2 (1 template + 1 custom)")
print(f"  Schedule created:   1")
print(f"  Runs executed:      {len(runs)}")
print(f"  Logs generated:     {len(logs)}")
print(f"\n  Next: Check the Dashboard at http://localhost:5173/ for live metrics")
