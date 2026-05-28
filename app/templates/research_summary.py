from __future__ import annotations

from app.templates.types import WorkflowTemplate


RESEARCH_SUMMARY_TEMPLATE = WorkflowTemplate(
    key="research_summary",
    name="Research Summary",
    description="Two-agent workflow that gathers structured notes and turns them into a concise answer.",
    nodes=["research_agent", "summarizer_agent"],
    edges=[("human", "research_agent"), ("research_agent", "summarizer_agent"), ("summarizer_agent", "human")],
    sample_input="Summarize the main benefits and risks of using AI agents in customer support.",
    default_config={
        "roles": {
            "research_agent": "Collect key facts and produce structured notes.",
            "summarizer_agent": "Write a concise final answer from the notes.",
        },
        "tools": ["web_search_stub", "save_note"],
    },
)

