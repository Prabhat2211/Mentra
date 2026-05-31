from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db import Database
from app.utils.encryption import decrypt_value, encrypt_value

router = APIRouter()


# Pydantic models
class AgentCreate(BaseModel):
    name: str
    role: str
    system_prompt: str
    model: str
    tools: list[str] | None = None
    channel: str = "ui"
    memory_enabled: bool = False
    guardrails: str = ""
    personality: str = "professional"
    llm_provider: str | None = None
    llm_api_key: str | None = None  # Will be encrypted before storage
    llm_model: str | None = None


class AgentResponse(BaseModel):
    id: str
    name: str
    role: str
    system_prompt: str
    model: str
    tools: list[str]
    channel: str
    memory_enabled: bool
    guardrails: str
    personality: str = "professional"
    llm_provider: str | None = None
    llm_model: str | None = None


def get_db() -> Database:
    db = Database()
    db.init()
    return db


@router.get("/")
async def list_agents(db: Database = Depends(get_db)):
    rows = db.list_agents()
    return [dict(row) for row in rows]


@router.post("/")
async def create_agent(agent: AgentCreate, db: Database = Depends(get_db)):
    # Encrypt API key if provided
    encrypted_key = None
    if agent.llm_api_key:
        encrypted_key = encrypt_value(agent.llm_api_key)

    agent_id = db.create_agent(
        name=agent.name,
        role=agent.role,
        system_prompt=agent.system_prompt,
        model=agent.model,
        tools=agent.tools,
        channel=agent.channel,
        memory_enabled=agent.memory_enabled,
        guardrails=agent.guardrails,
        personality=agent.personality,
        llm_provider=agent.llm_provider,
        llm_api_key_encrypted=encrypted_key,
        llm_model=agent.llm_model,
    )
    return {"id": agent_id, "message": "Agent created successfully"}


@router.get("/{agent_id}")
async def get_agent(agent_id: str, db: Database = Depends(get_db)):
    agents = db.list_agents()
    agent = next((dict(row) for row in agents if row["id"] == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.put("/{agent_id}")
async def update_agent(agent_id: str, agent: AgentCreate, db: Database = Depends(get_db)):
    encrypted_key = None
    if agent.llm_api_key:
        encrypted_key = encrypt_value(agent.llm_api_key)

    updated = db.update_agent(
        agent_id=agent_id,
        name=agent.name,
        role=agent.role,
        system_prompt=agent.system_prompt,
        model=agent.model,
        tools=agent.tools,
        channel=agent.channel,
        memory_enabled=agent.memory_enabled,
        guardrails=agent.guardrails,
        personality=agent.personality,
        llm_provider=agent.llm_provider,
        llm_api_key_encrypted=encrypted_key,
        llm_model=agent.llm_model,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"id": agent_id, "message": "Agent updated successfully"}


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str, db: Database = Depends(get_db)):
    deleted = db.delete_agent(agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": "Agent deleted successfully"}
