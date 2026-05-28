from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.config import settings
from app.db import Database
from app.runtime.graph import run_workflow
from app.runtime.llm import active_llm_status
from app.templates.registry import TEMPLATES, seed_default_workflows


st.set_page_config(page_title="Yuno Agent Orchestration", layout="wide")

db = Database(settings.database_path)
db.init()
seed_default_workflows(db)


def main() -> None:
    st.title("Yuno Agent Orchestration")
    page = st.sidebar.radio("Navigate", ["Dashboard", "Agents", "Workflows", "Messages", "Monitoring"])

    if page == "Dashboard":
        render_dashboard()
    elif page == "Agents":
        render_agents()
    elif page == "Workflows":
        render_workflows()
    elif page == "Messages":
        render_messages()
    else:
        render_monitoring()


def render_dashboard() -> None:
    agents = db.list_agents()
    workflows = db.list_workflows()
    runs = db.list_runs()
    logs = db.list_logs(limit=5)
    llm_status = active_llm_status()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Agents", len(agents))
    col2.metric("Workflows", len(workflows))
    col3.metric("Recent Runs", len(runs))
    col4.metric("LLM Mode", str(llm_status["mode"]))

    st.caption(
        f"Provider: {llm_status['provider']} | Model: {llm_status['model']} | "
        f"Configured: {llm_status['configured']}"
    )

    st.subheader("Recent Runs")
    st.dataframe([dict(row) for row in runs], width="stretch")

    st.subheader("Latest Logs")
    st.dataframe([dict(row) for row in logs], width="stretch")


def render_agents() -> None:
    st.subheader("Create Agent")
    with st.form("agent_form", clear_on_submit=True):
        name = st.text_input("Name", "Financial Assistant")
        role = st.text_input("Role", "Stock market assistant")
        system_prompt = st.text_area(
            "System Prompt",
            "Answer clearly, use tools when needed, and do not provide financial advice.",
        )
        model = st.text_input("Model", settings.openai_model)
        tools = st.multiselect(
            "Tools",
            ["web_search_stub", "save_note", "get_stock_quote"],
            default=["get_stock_quote"],
        )
        channel = st.selectbox("Channel", ["ui", "telegram", "agent"], index=1)
        memory_enabled = st.checkbox("Memory enabled")
        guardrails = st.text_area("Guardrails", "Keep responses brief and include disclaimers for market data.")
        submitted = st.form_submit_button("Create Agent")
        if submitted:
            db.create_agent(
                name=name,
                role=role,
                system_prompt=system_prompt,
                model=model,
                tools=tools,
                channel=channel,
                memory_enabled=memory_enabled,
                guardrails=guardrails,
            )
            st.success("Agent created.")

    st.subheader("Agents")
    st.dataframe([_agent_row(row) for row in db.list_agents()], width="stretch")


def render_workflows() -> None:
    st.subheader("Workflow Templates")
    for template in TEMPLATES.values():
        with st.expander(template.name, expanded=template.key == "financial_assistant"):
            st.write(template.description)
            st.code(" -> ".join(template.nodes))
            st.caption(f"Sample: {template.sample_input}")

    st.subheader("Run Workflow")
    workflows = db.list_workflows()
    workflow_names = {f"{row['name']} ({row['template_key']})": row["id"] for row in workflows}
    selected = st.selectbox("Workflow", list(workflow_names.keys()))
    default_input = _sample_for_workflow(workflows, workflow_names[selected])
    user_input = st.text_area("Input", default_input)
    source_channel = st.selectbox("Source channel", ["ui", "telegram"], index=0)
    if st.button("Run Workflow"):
        result = run_workflow(
            workflow_id=workflow_names[selected],
            user_input=user_input,
            source_channel=source_channel,
            db=db,
        )
        st.success("Workflow completed.")
        st.text_area("Output", result.output, height=220)
        st.caption(f"Run: {result.run_id} | Tokens: {result.token_count} | Cost: ${result.estimated_cost:.6f}")


def render_messages() -> None:
    st.subheader("Messages")
    rows = [dict(row) for row in db.list_messages()]
    for row in rows:
        row["metadata_json"] = _pretty_json(row["metadata_json"])
    st.dataframe(rows, width="stretch")


def render_monitoring() -> None:
    st.subheader("Logs")
    rows = [dict(row) for row in db.list_logs()]
    for row in rows:
        row["payload_json"] = _pretty_json(row["payload_json"])
    st.dataframe(rows, width="stretch")


def _agent_row(row) -> dict[str, object]:
    data = dict(row)
    data["tools_json"] = _pretty_json(data["tools_json"])
    data["memory_enabled"] = bool(data["memory_enabled"])
    return data


def _pretty_json(value: str) -> str:
    try:
        return json.dumps(json.loads(value or "{}"), indent=2)
    except json.JSONDecodeError:
        return value


def _sample_for_workflow(workflows, workflow_id: str) -> str:
    template_key = next(row["template_key"] for row in workflows if row["id"] == workflow_id)
    return TEMPLATES[template_key].sample_input


if __name__ == "__main__":
    main()
