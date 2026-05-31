from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.db import Database


@pytest.fixture
def test_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def client(test_db_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", test_db_path)

    # Re-import settings to pick up the new env var
    import app.config
    import importlib
    importlib.reload(app.config)

    db = Database(path=test_db_path)
    db.init()

    from app.templates.registry import seed_default_workflows
    seed_default_workflows(db)

    from backend.main import app
    return TestClient(app)


class TestHealthAndStatus:
    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "2.0.0"

    def test_llm_status(self, client):
        response = client.get("/api/llm-status")
        assert response.status_code == 200
        data = response.json()
        assert "provider" in data
        assert "model" in data
        assert "mode" in data
        assert "configured" in data


class TestAgentCRUD:
    def test_create_agent(self, client):
        response = client.post("/api/agents/", json={
            "name": "Test Agent",
            "role": "tester",
            "system_prompt": "You are a test agent.",
            "model": "test-model",
            "tools": ["web_search_stub"],
            "channel": "ui",
            "memory_enabled": True,
            "guardrails": "no-harm",
        })
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["message"] == "Agent created successfully"

    def test_create_agent_with_llm_config(self, client):
        response = client.post("/api/agents/", json={
            "name": "LLM Agent",
            "role": "tester",
            "system_prompt": "Test prompt",
            "model": "gemini-2.5-flash-lite",
            "tools": [],
            "channel": "ui",
            "memory_enabled": False,
            "guardrails": "",
            "llm_provider": "gemini",
            "llm_api_key": "test-key-123",
            "llm_model": "gemini-2.5-flash-lite",
            "mcp_tools": [{"name": "test_tool", "description": "A test MCP tool", "server_url": "http://localhost:9999"}],
        })
        assert response.status_code == 200
        assert "id" in response.json()

    def test_list_agents(self, client):
        client.post("/api/agents/", json={
            "name": "Agent A", "role": "tester", "system_prompt": "A", "model": "m", "tools": [], "channel": "ui",
        })
        client.post("/api/agents/", json={
            "name": "Agent B", "role": "tester", "system_prompt": "B", "model": "m", "tools": [], "channel": "ui",
        })
        response = client.get("/api/agents/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_get_agent(self, client):
        create_resp = client.post("/api/agents/", json={
            "name": "Get Me", "role": "tester", "system_prompt": "G", "model": "m", "tools": [], "channel": "ui",
        })
        agent_id = create_resp.json()["id"]

        response = client.get(f"/api/agents/{agent_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Get Me"

    def test_get_agent_not_found(self, client):
        response = client.get("/api/agents/nonexistent-id")
        assert response.status_code == 404

    def test_update_agent(self, client):
        create_resp = client.post("/api/agents/", json={
            "name": "Original", "role": "tester", "system_prompt": "O", "model": "m", "tools": [], "channel": "ui",
        })
        agent_id = create_resp.json()["id"]

        response = client.put(f"/api/agents/{agent_id}", json={
            "name": "Updated", "role": "updater", "system_prompt": "U", "model": "m2",
            "tools": ["get_stock_quote"], "channel": "telegram", "memory_enabled": True, "guardrails": "updated",
        })
        assert response.status_code == 200
        assert response.json()["message"] == "Agent updated successfully"

        get_resp = client.get(f"/api/agents/{agent_id}")
        assert get_resp.json()["name"] == "Updated"

    def test_update_agent_not_found(self, client):
        response = client.put("/api/agents/nonexistent", json={
            "name": "X", "role": "tester", "system_prompt": "X", "model": "m", "tools": [], "channel": "ui",
        })
        assert response.status_code == 404

    def test_delete_agent(self, client):
        create_resp = client.post("/api/agents/", json={
            "name": "Delete Me", "role": "tester", "system_prompt": "D", "model": "m", "tools": [], "channel": "ui",
        })
        agent_id = create_resp.json()["id"]

        response = client.delete(f"/api/agents/{agent_id}")
        assert response.status_code == 200
        assert response.json()["message"] == "Agent deleted successfully"

        get_resp = client.get(f"/api/agents/{agent_id}")
        assert get_resp.status_code == 404

    def test_delete_agent_not_found(self, client):
        response = client.delete("/api/agents/nonexistent")
        assert response.status_code == 404


class TestWorkflowEndpoints:
    def test_list_workflows(self, client):
        response = client.get("/api/workflows/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2  # Two template workflows seeded

    def test_get_workflow(self, client):
        workflows = client.get("/api/workflows/").json()
        workflow_id = workflows[0]["id"]

        response = client.get(f"/api/workflows/{workflow_id}")
        assert response.status_code == 200
        assert response.json()["id"] == workflow_id

    def test_get_workflow_not_found(self, client):
        response = client.get("/api/workflows/nonexistent")
        assert response.status_code == 404

    def test_create_custom_workflow(self, client):
        response = client.post("/api/workflows/", json={
            "name": "Custom WF",
            "description": "A custom drag-and-drop workflow",
            "template_key": "custom",
            "is_custom": True,
            "nodes": [{"id": "n1", "agent_id": "some-agent", "label": "Test"}],
            "edges": [],
        })
        assert response.status_code == 200
        assert "id" in response.json()

    def test_run_workflow(self, client):
        workflows = client.get("/api/workflows/").json()
        research_wf = next((w for w in workflows if w["template_key"] == "research_summary"), None)
        assert research_wf is not None

        response = client.post(f"/api/workflows/{research_wf['id']}/run", json={
            "user_input": "Summarize the benefits of testing.",
            "source_channel": "ui",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "run_id" in data
        assert "output" in data


class TestRunsMessagesLogs:
    def test_list_runs(self, client):
        response = client.get("/api/runs/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_runs_after_execution(self, client):
        workflows = client.get("/api/workflows/").json()
        research_wf = next((w for w in workflows if w["template_key"] == "research_summary"), None)

        client.post(f"/api/workflows/{research_wf['id']}/run", json={
            "user_input": "Test run message.",
            "source_channel": "ui",
        })

        response = client.get("/api/runs/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(r["status"] == "completed" for r in data)

    def test_list_messages(self, client):
        workflows = client.get("/api/workflows/").json()
        research_wf = next((w for w in workflows if w["template_key"] == "research_summary"), None)

        client.post(f"/api/workflows/{research_wf['id']}/run", json={
            "user_input": "Message test.",
            "source_channel": "ui",
        })

        response = client.get("/api/messages/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_list_logs(self, client):
        workflows = client.get("/api/workflows/").json()
        research_wf = next((w for w in workflows if w["template_key"] == "research_summary"), None)

        client.post(f"/api/workflows/{research_wf['id']}/run", json={
            "user_input": "Log test.",
            "source_channel": "ui",
        })

        response = client.get("/api/logs/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


class TestPersonality:
    def test_create_agent_with_personality(self, client):
        response = client.post("/api/agents/", json={
            "name": "Polite Agent",
            "role": "tester",
            "system_prompt": "Test",
            "model": "test-model",
            "tools": [],
            "channel": "ui",
            "personality": "polite",
        })
        assert response.status_code == 200
        agent_id = response.json()["id"]

        get_resp = client.get(f"/api/agents/{agent_id}")
        agent_data = get_resp.json()
        assert agent_data["personality"] == "polite"

    def test_personality_defaults_to_professional(self, client):
        response = client.post("/api/agents/", json={
            "name": "Default Agent",
            "role": "tester",
            "system_prompt": "Test",
            "model": "test-model",
            "tools": [],
            "channel": "ui",
        })
        assert response.status_code == 200
        agent_id = response.json()["id"]

        get_resp = client.get(f"/api/agents/{agent_id}")
        agent_data = get_resp.json()
        assert agent_data["personality"] == "professional"
