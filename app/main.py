import re
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from agent.decision import DecisionRecord
from agent.llm import create_llm_client
from agent.reply import ReplyEngine
from app.db import DEFAULT_DB_PATH
from agent.memory import MemoryStore
from app.transcripts import get_transcript, render_transcript_html
from app.ui import chat_page, results_page, ui_index_page
from tools import MockTools


app = FastAPI(title="ChitChatCho Mock Support Agent")

ORDER_STATUS_PATTERN = re.compile(
    r"\b(where(?:'s| is)?\s+(?:my\s+)?(?:order|package|shipment)|"
    r"(?:order|shipment|package)\s+(?:status|tracking|update)|"
    r"track(?:ing)?\s+(?:my\s+)?(?:order|package|shipment)|"
    r"shipping\s+(?:status|update)|delivery\s+(?:status|update)|"
    r"when\s+(?:will|does)\s+(?:my\s+)?(?:order|package)\s+(?:arrive|deliver))\b",
    re.IGNORECASE,
)
ORDER_ID_PATTERN = re.compile(
    r"(?:\b(?:MOCK[-\s]?ORDER[-\s]?|ORDER(?:\s+(?:NUMBER|NO\.?))?\s*#?\s*(?:IS\s*)?)|#\s*)(\d+)\b",
    re.IGNORECASE,
)
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
MOCK_POSTCODE_PATTERN = re.compile(r"\bMOCK\s*[- ]?\s*(\d{4})\b", re.IGNORECASE)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=30)


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


@app.get("/ui", response_class=HTMLResponse)
def ui_index() -> HTMLResponse:
    return ui_index_page()


@app.get("/ui/chat", response_class=HTMLResponse)
def ui_chat() -> HTMLResponse:
    return chat_page()


@app.get("/ui/results", response_class=HTMLResponse)
def ui_results() -> HTMLResponse:
    return results_page()


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    last_assistant_message = next(
        (item.content.lower() for item in reversed(request.history) if item.role == "assistant"),
        "",
    )
    awaiting_order_number = "order number" in last_assistant_message
    awaiting_identity = "email" in last_assistant_message and "postcode" in last_assistant_message
    order_id, email, postcode = _extract_order_details(
        request.message,
        allow_bare_order_id=awaiting_order_number,
    )
    current_order_id = order_id
    if awaiting_identity:
        for item in reversed(request.history):
            if item.role != "user":
                continue
            history_order_id, history_email, history_postcode = _extract_order_details(
                item.content,
                allow_bare_order_id=True,
            )
            order_id = order_id or history_order_id
            email = email or history_email
            postcode = postcode or history_postcode

    is_order_number_answer = awaiting_order_number and order_id is not None
    is_identity_answer = awaiting_identity and order_id is not None and (email or postcode)
    if ORDER_STATUS_PATTERN.search(request.message) or current_order_id or is_order_number_answer or is_identity_answer:
        if not order_id:
            return ChatResponse(reply="What is the order number?")

        tools = MockTools(DEFAULT_DB_PATH)
        existence = tools.order_exists(order_id)
        if not existence.get("ok"):
            return ChatResponse(reply="I couldn't check that order number just now. Please try again.")
        if not existence.get("exists"):
            return ChatResponse(
                reply=f"I can't find order number {order_id} in our records. Please check it and send the number again."
            )

        if not email and not postcode:
            return ChatResponse(
                reply="For privacy, please provide the email address or postcode used at checkout."
            )

        lookup = tools.lookup_order(order_id, email=email, postcode=postcode)
        if not lookup.get("ok"):
            return ChatResponse(
                reply="I couldn't verify those details. Please check the order number and the email or postcode, then try again."
            )

        order = lookup["order"]
        status = str(order["status"]).replace("-", " ")
        reply = f"I found {order_id}. Its latest status is {status}."
        if order["status"] == "processing":
            reply += " It has not shipped yet, so tracking is not available."
        elif order["status"] in {"shipped", "delayed", "delivered", "damaged-reported"}:
            shipment_result = tools.track_shipment(order_id, email=email, postcode=postcode)
            shipment = shipment_result.get("shipment") if shipment_result.get("ok") else None
            if shipment:
                if shipment.get("tracking_number"):
                    reply += f" Tracking number: {shipment['tracking_number']}."
                if shipment.get("estimated_delivery"):
                    reply += f" Estimated delivery: {shipment['estimated_delivery']}."
                if shipment.get("last_event"):
                    reply += f" Latest update: {shipment['last_event']}."
        return ChatResponse(reply=reply)

    history = "\n".join(
        f"{'Customer' if item.role == 'user' else 'Assistant'}: {item.content}"
        for item in request.history
    )
    prompt = (
        "You are a helpful customer support assistant. Be clear and honest. "
        "Do not claim to have checked orders, accounts, or systems unless that information "
        "is included in the conversation.\n\n"
        f"{history + chr(10) if history else ''}"
        f"Customer: {request.message}\nAssistant:"
    )
    reply = create_llm_client().complete(prompt)
    return ChatResponse(reply=reply)


def _extract_order_details(
    text: str,
    *,
    allow_bare_order_id: bool = False,
) -> tuple[str | None, str | None, str | None]:
    order_matches = list(ORDER_ID_PATTERN.finditer(text))
    order_match = order_matches[-1] if order_matches else None
    email_matches = list(EMAIL_PATTERN.finditer(text))
    postcode_matches = list(MOCK_POSTCODE_PATTERN.finditer(text))
    email_match = email_matches[-1] if email_matches else None
    postcode_match = postcode_matches[-1] if postcode_matches else None
    if (
        not order_match
        and allow_bare_order_id
        and not email_match
        and not postcode_match
        and re.fullmatch(r"\s*#?\s*(\d{1,12})\s*[.!]?\s*", text)
    ):
        order_match = re.fullmatch(r"\s*#?\s*(\d{1,12})\s*[.!]?\s*", text)
    order_number = (
        order_match.group(1) if order_matches else order_match.group(0)
    ) if order_match else None
    order_id = f"MOCK-ORDER-{order_number.zfill(3)}" if order_number else None
    postcode = f"MOCK {postcode_match.group(1)}" if postcode_match else None
    email = email_match.group(0) if email_match else None
    return order_id, email, postcode


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