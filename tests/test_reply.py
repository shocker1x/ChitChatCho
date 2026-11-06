import pytest
from fastapi.testclient import TestClient

from agent.decision import DecisionRecord, Emotion, Move
from agent.reply import ReplyEngine
from app.main import app
from app.transcripts import append_turn, get_transcript, render_transcript_html


def make_decision(move=Move.ANSWER, emotion=Emotion.CALM):
    return DecisionRecord(
        intent="Understand a rug order",
        known=["The customer gave a verified order number"],
        missing=[],
        move=move,
        confidence="high",
        stakes="low",
        policy_refs=["shipment_date_honesty"],
        tool_plan=[],
        emotion=emotion,
        reason="The shipment record provides the latest status.",
    )


class FakeClient:
    def __init__(self, response="Your order is in transit."):
        self.response = response
        self.prompt = ""

    def complete(self, prompt):
        self.prompt = prompt
        return self.response


def test_reply_prompt_uses_decision_move_emotion_and_tool_results():
    client = FakeClient("I know the delay is frustrating. The latest scan is at the mock hub.")
    engine = ReplyEngine(client)
    decision = make_decision(Move.ACT, Emotion.FRUSTRATED)

    reply = engine.reply(
        "This is late and frustrating.",
        decision,
        tool_results=[{"ok": True, "shipment": {"status": "delayed"}}],
        identity_verified=True,
    )

    assert reply == client.response
    assert "Report only what the supplied tool results confirm" in client.prompt
    assert "Name the specific frustration or impact" in client.prompt
    assert "shipment_date_honesty" in client.prompt
    assert '"identity_verified": true' in client.prompt


def test_reply_prompt_requires_one_clarification_or_explicit_confirmation():
    client = FakeClient("What are the room's dimensions?")
    engine = ReplyEngine(client)
    clarify = make_decision(Move.CLARIFY)
    confirm = make_decision(Move.CONFIRM)

    engine.reply("What size should I buy?", clarify)
    clarify_prompt = client.prompt
    engine.reply("Cancel my order", confirm)

    assert "Ask exactly one focused question" in clarify_prompt
    assert "ask for a clear yes or no" in client.prompt


def test_reply_prompt_reports_tool_failure_without_claiming_success():
    client = FakeClient("This should not be used.")
    reply = ReplyEngine(client).reply(
        "Where is my rug?",
        make_decision(Move.ACT).model_copy(
            update={"tool_plan": [{"tool": "track_shipment", "inputs": {"order_id": "MOCK-ORDER-009"}}]}
        ),
        tool_results=[{"ok": False, "error": "synthetic backend outage"}],
    )

    assert reply == "I couldn't complete that check just now. I can retry it or ask a teammate to review it."
    assert client.prompt == ""


def test_act_without_tool_results_does_not_claim_completion():
    decision = make_decision(Move.ACT).model_copy(
        update={"tool_plan": [{"tool": "track_shipment", "inputs": {"order_id": "MOCK-ORDER-009"}}]}
    )
    client = FakeClient("This should not be used.")

    reply = ReplyEngine(client).reply("Where is my rug?", decision)

    assert "haven't completed" in reply
    assert client.prompt == ""


def test_empty_provider_reply_is_rejected():
    with pytest.raises(ValueError, match="empty response"):
        ReplyEngine(FakeClient("  ")).reply("Hello", make_decision())


def test_transcript_storage_orders_turns_and_renders_decision_beside_reply(tmp_path):
    db_path = tmp_path / "transcript.sqlite3"
    first = append_turn("mock-chat", "Where is my order?", make_decision(), "It is in transit.", db_path)
    second = append_turn("mock-chat", "When will it arrive?", make_decision(), "The estimate is Nov 10.", db_path)
    turns = get_transcript("mock-chat", db_path)
    html = render_transcript_html("mock-chat", turns)

    assert first["turn_number"] == 1
    assert second["turn_number"] == 2
    assert len(turns) == 2
    assert turns[0]["decision"]["move"] == "answer"
    assert "Decision record" in html
    assert "It is in transit." in html
    assert html.index("Turn 1") < html.index("Turn 2")


def test_transcript_viewer_escapes_customer_content():
    html = render_transcript_html(
        "safe-id",
        [{
            "turn_number": 1,
            "customer_message": "<script>alert(1)</script>",
            "decision": make_decision().model_dump(mode="json"),
            "reply": "<img src=x onerror=alert(1)>",
        }],
    )

    assert "&lt;script&gt;" in html
    assert "&lt;img" in html
    assert "<script>alert(1)</script>" not in html


def test_ten_manual_chat_samples_are_documented():
    from pathlib import Path

    manual_chats = Path(__file__).resolve().parents[1] / "docs" / "manual_chats.md"
    headings = [line for line in manual_chats.read_text(encoding="utf-8").splitlines() if line.startswith("## ")]

    assert len(headings) == 10


def test_reply_turn_api_persists_and_viewer_reads_transcript(monkeypatch, tmp_path):
    class StubReplyEngine:
        def reply(self, customer_message, decision, **kwargs):
            assert customer_message == "Can I return this rug?"
            assert decision.move == Move.ANSWER
            return "The standard return window is 30 days after delivery."

    monkeypatch.setattr("app.main.ReplyEngine", StubReplyEngine)
    monkeypatch.setattr("app.main.DEFAULT_DB_PATH", tmp_path / "api-transcript.sqlite3")
    client = TestClient(app)
    response = client.post(
        "/conversations/demo-chat/turns",
        json={
            "customer_message": "Can I return this rug?",
            "decision": make_decision().model_dump(mode="json"),
        },
    )
    viewer = client.get("/conversations/demo-chat/transcript")

    assert response.status_code == 200
    assert response.json()["turn_number"] == 1
    assert response.json()["reply"].startswith("The standard return window")
    assert viewer.status_code == 200
    assert "Decision record" in viewer.text
    assert "The standard return window is 30 days" in viewer.text
