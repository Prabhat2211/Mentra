from __future__ import annotations

import json
from pathlib import Path

from app.db import Database
from app.utils.encryption import decrypt_value, encrypt_value


def test_encryption_roundtrip(tmp_path):
    """Test that encryption and decryption work correctly."""
    original = "test-api-key-12345"
    encrypted = encrypt_value(original)
    decrypted = decrypt_value(encrypted)
    assert decrypted == original
    assert encrypted != original.encode()


def test_encryption_empty_value(tmp_path):
    """Test encryption handles empty values."""
    assert encrypt_value("") == b""
    assert decrypt_value(b"") == ""


def test_create_agent_with_llm_config(tmp_path):
    """Test that agents can be created with per-agent LLM config and personality."""
    db = Database(tmp_path / "test.db")
    db.init()

    from app.utils.encryption import encrypt_value

    encrypted_key = encrypt_value("gemini-api-key-123")

    agent_id = db.create_agent(
        name="Test Agent",
        role="Test Role",
        system_prompt="You are a test agent.",
        model="gpt-4o-mini",
        tools=["web_search_stub"],
        channel="ui",
        memory_enabled=False,
        guardrails="Be safe.",
        personality="polite",
        llm_provider="gemini",
        llm_api_key_encrypted=encrypted_key,
        llm_model="gemini-2.5-flash-lite",
    )

    agents = db.list_agents()
    assert len(agents) == 1
    agent = agents[0]
    assert agent["name"] == "Test Agent"
    assert agent["llm_provider"] == "gemini"
    assert agent["llm_model"] == "gemini-2.5-flash-lite"
    assert agent["personality"] == "polite"


def test_create_custom_workflow(tmp_path):
    """Test that custom workflows can be created with nodes and edges."""
    db = Database(tmp_path / "test.db")
    db.init()

    workflow_id = db.create_workflow(
        name="Custom Workflow",
        description="A custom drag-and-drop workflow",
        template_key="custom",
        config={"test": True},
        is_custom=True,
        nodes=[
            {"agent_id": "agent-1", "position": {"x": 100, "y": 100}},
            {"agent_id": "agent-2", "position": {"x": 300, "y": 100}},
        ],
        edges=[
            {"source": "agent-1", "target": "agent-2"},
        ],
    )

    workflow = db.get_workflow(workflow_id)
    assert workflow["name"] == "Custom Workflow"
    assert workflow["is_custom"] == 1
    nodes = json.loads(workflow["nodes_json"] or "[]")
    edges = json.loads(workflow["edges_json"] or "[]")
    assert len(nodes) == 2
    assert len(edges) == 1
