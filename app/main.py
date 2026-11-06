from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from agent.decision import DecisionRecord
from agent.llm import create_llm_client
from agent.reply import ReplyEngine
from app.db import DEFAULT_DB_PATH
from agent.memory import MemoryStore
from app.transcripts import get_transcript, render_transcript_html


app = FastAPI(title="ChitChatCho Mock Support Agent")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str


class ReplyTurnRequest(BaseModel):
    customer_message: str = Field(min_length=1, max_length=4000)
    decision: DecisionRecord
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    order_id: str | None = None
    email: str | None = None
    postcode: str | None = None


class CompleteConversationRequest(BaseModel):
    summary: str = Field(min_length=1, max_length=2000)
    order_id: str
    email: str | None = None
    postcode: str | None = None
    preferences: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    reply = create_llm_client().complete(request.message)
    return ChatResponse(reply=reply)


@app.post("/conversations/{conversation_id}/turns")
def create_reply_turn(conversation_id: str, request: ReplyTurnRequest) -> dict[str, Any]:
    memory = MemoryStore(DEFAULT_DB_PATH)
    context = memory.load_context(
        conversation_id,
        order_id=request.order_id,
        email=request.email,
        postcode=request.postcode,
    )
    reply = ReplyEngine().reply(
        request.customer_message,
        request.decision,
        tool_results=request.tool_results,
        history=context["history"],
        identity_verified=context["identity_verified"],
    )
    turn = memory.record_turn(
        conversation_id,
        request.customer_message,
        request.decision,
        reply,
    )
    return {
        "conversation_id": conversation_id,
        "turn_number": turn["turn_number"],
        "decision": turn["decision"],
        "reply": reply,
        "known_facts": memory.load_context(conversation_id)["known_facts"],
    }


@app.get("/conversations/{conversation_id}/memory")
def load_conversation_memory(
    conversation_id: str,
    order_id: str | None = None,
    email: str | None = None,
    postcode: str | None = None,
) -> dict[str, Any]:
    return MemoryStore(DEFAULT_DB_PATH).load_context(
        conversation_id,
        order_id=order_id,
        email=email,
        postcode=postcode,
    )


@app.post("/conversations/{conversation_id}/complete")
def complete_conversation(
    conversation_id: str,
    request: CompleteConversationRequest,
) -> dict[str, Any]:
    try:
        return MemoryStore(DEFAULT_DB_PATH).complete_conversation(
            conversation_id,
            request.summary,
            order_id=request.order_id,
            email=request.email,
            postcode=request.postcode,
            preferences=request.preferences,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail="Identity verification failed.") from error


@app.get("/conversations/{conversation_id}/transcript", response_class=HTMLResponse)
def transcript_viewer(conversation_id: str) -> HTMLResponse:
    turns = get_transcript(conversation_id, db_path=DEFAULT_DB_PATH)
    return HTMLResponse(render_transcript_html(conversation_id, turns))