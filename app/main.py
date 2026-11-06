from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from agent.decision import DecisionRecord
from agent.llm import create_llm_client
from agent.reply import ReplyEngine
from app.db import DEFAULT_DB_PATH
from app.transcripts import append_turn, get_transcript, render_transcript_html


app = FastAPI(title="ChitChatCho Mock Support Agent")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str


class ReplyTurnRequest(BaseModel):
    customer_message: str = Field(min_length=1, max_length=4000)
    decision: DecisionRecord
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    history: list[dict[str, str]] = Field(default_factory=list)
    identity_verified: bool = False


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    reply = create_llm_client().complete(request.message)
    return ChatResponse(reply=reply)


@app.post("/conversations/{conversation_id}/turns")
def create_reply_turn(conversation_id: str, request: ReplyTurnRequest) -> dict[str, Any]:
    reply = ReplyEngine().reply(
        request.customer_message,
        request.decision,
        tool_results=request.tool_results,
        history=request.history,
        identity_verified=request.identity_verified,
    )
    turn = append_turn(
        conversation_id,
        request.customer_message,
        request.decision,
        reply,
        db_path=DEFAULT_DB_PATH,
    )
    return {
        "conversation_id": conversation_id,
        "turn_number": turn["turn_number"],
        "decision": turn["decision"],
        "reply": reply,
    }


@app.get("/conversations/{conversation_id}/transcript", response_class=HTMLResponse)
def transcript_viewer(conversation_id: str) -> HTMLResponse:
    turns = get_transcript(conversation_id, db_path=DEFAULT_DB_PATH)
    return HTMLResponse(render_transcript_html(conversation_id, turns))