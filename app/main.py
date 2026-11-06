from fastapi import FastAPI
from pydantic import BaseModel, Field

from agent.llm import create_llm_client


app = FastAPI(title="ChitChatCho Mock Support Agent")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    reply = create_llm_client().complete(request.message)
    return ChatResponse(reply=reply)