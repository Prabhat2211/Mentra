"""
Quick smoke test — run this to verify the platform works end-to-end.

Usage:  python examples/quick_test.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import Database
from app.runtime.graph import run_workflow
from app.templates.registry import seed_default_workflows

db = Database()
db.init()
seed_default_workflows(db)

# Create a simple agent
agent_id = db.create_agent(
    name="Test Assistant",
    role="General assistant",
    system_prompt="You are a helpful assistant. Answer concisely.",
    model="gpt-oss-120B",
    tools=[],
    channel="ui",
)
print(f"✅ Agent created: {agent_id[:8]}...")

# Assign agent to research template
for wf in db.list_workflows():
    if wf["template_key"] == "research_summary":
        import json
        config = json.loads(wf["config_json"] or "{}")
        config["agent_assignments"] = {"research_agent": agent_id, "summarizer_agent": agent_id}
        db.update_workflow(workflow_id=wf["id"], name=wf["name"], description=wf["description"], config=config)

        # Run
        result = run_workflow(
            workflow_id=wf["id"],
            user_input="What are the benefits of AI in education?",
            db=db,
        )
        print(f"✅ Run completed: status={result.status}")
        print(f"   Output: {result.output[:150]}...")
        print(f"   Tokens: {result.token_count}  Cost: ${result.estimated_cost:.6f}")
        break

# Check monitoring data
runs = db.list_runs()
logs = db.list_logs()
messages = db.list_messages()
print(f"📊 Runs: {len(runs)} | Logs: {len(logs)} | Messages: {len(messages)}")
print(f"\n✅ Platform is working!")
