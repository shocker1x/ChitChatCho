from fastapi.testclient import TestClient

from app.main import app
from tools.mock_tools import MockTools as RealMockTools


client = TestClient(app)


def test_chat_page_serves_empty_customer_chat_without_internal_trace():
    response = client.get("/ui/chat")
    assert response.status_code == 200
    text = response.text
    assert "Rugs support" in text
    assert "linear-gradient" not in text
    assert "Send" in text
    assert 'id="theme-toggle"' in text
    assert "Switch to dark mode" in text
    assert "chitchatcho-theme" in text
    assert text.index('class="workspace"') < text.index('id="theme-toggle"')
    assert "position: fixed" in text
    assert 'aria-label="Send message"' in text
    assert "event.shiftKey" in text
    assert "overscroll-behavior: contain" in text
    assert 'role="scrollbar"' in text
    assert 'id="conversation-scrollbar-thumb"' in text
    assert "scrollbar-width: none" in text
    assert ".thread::-webkit-scrollbar-button" not in text
    assert ".empty-state[hidden]" in text
    assert "conversation.scrollTo" in text
    assert "scrollIntoView" not in text
    assert "How can I help?" in text
    assert "Decision trace" not in text
    assert "inspector" not in text
    assert "Where is my order?" not in text


def test_order_lookup_requires_identity_verification():
    response = client.post("/chat", json={"message": "Where is my order?"})

    assert response.status_code == 200
    assert "order number" in response.json()["reply"].lower()


def test_verified_order_lookup_returns_seeded_shipment(monkeypatch, tmp_path):
    database_path = tmp_path / "chat.sqlite3"
    monkeypatch.setattr(
        "app.main.MockTools",
        lambda _database_path: RealMockTools(database_path),
    )

    response = client.post(
        "/chat",
        json={
            "message": "My email is alex@example.invalid",
            "history": [
                {"role": "user", "content": "Where is my order?"},
                {"role": "assistant", "content": "What is the order number?"},
                {"role": "user", "content": "9"},
                {"role": "assistant", "content": "Please provide the email address or postcode used at checkout."},
            ],
        },
    )

    assert response.status_code == 200
    reply = response.json()["reply"]
    assert "MOCK-ORDER-009" in reply
    assert "shipped" in reply
    assert "MOCKTRACK00000009" in reply


def test_unknown_bare_order_number_is_reported_as_not_found(monkeypatch, tmp_path):
    database_path = tmp_path / "chat.sqlite3"
    monkeypatch.setattr(
        "app.main.MockTools",
        lambda _database_path: RealMockTools(database_path),
    )

    response = client.post(
        "/chat",
        json={
            "message": "402",
            "history": [
                {"role": "user", "content": "I want to know my order status."},
                {"role": "assistant", "content": "What is the order number?"},
            ],
        },
    )

    assert response.status_code == 200
    reply = response.json()["reply"].lower()
    assert "mock-order-402" in reply
    assert "can't find" in reply
    assert "records" in reply
    assert "what is the order number" not in reply


def test_new_question_exits_order_verification_prompt(monkeypatch):
    class FakeClient:
        def complete(self, prompt):
            assert "How do I clean a wool rug?" in prompt
            return "Vacuum gently with suction only."

    monkeypatch.setattr("app.main.create_llm_client", FakeClient)
    histories = [
        [
            {"role": "user", "content": "I want to know my order status."},
            {"role": "assistant", "content": "What is the order number?"},
        ],
        [
            {"role": "user", "content": "Where is my order?"},
            {"role": "assistant", "content": "What is the order number?"},
            {"role": "user", "content": "9"},
            {"role": "assistant", "content": "Please provide the email address or postcode used at checkout."},
        ],
    ]

    for history in histories:
        response = client.post(
            "/chat",
            json={"message": "How do I clean a wool rug?", "history": history},
        )
        assert response.status_code == 200
        assert response.json()["reply"] == "Vacuum gently with suction only."


def test_order_lookup_rejects_mismatched_identity(monkeypatch, tmp_path):
    database_path = tmp_path / "chat.sqlite3"
    monkeypatch.setattr(
        "app.main.MockTools",
        lambda _database_path: RealMockTools(database_path),
    )

    response = client.post(
        "/chat",
        json={
            "message": "Where is MOCK-ORDER-009? My email is wrong@example.invalid",
        },
    )

    assert response.status_code == 200
    assert "couldn't verify" in response.json()["reply"].lower()
    assert "shipped" not in response.json()["reply"].lower()


def test_general_question_uses_llm(monkeypatch):
    class FakeClient:
        def complete(self, prompt):
            assert "How should I care for a wool rug?" in prompt
            return "Vacuum gently with suction only."

    monkeypatch.setattr("app.main.create_llm_client", FakeClient)

    response = client.post("/chat", json={"message": "How should I care for a wool rug?"})

    assert response.status_code == 200
    assert response.json()["reply"] == "Vacuum gently with suction only."


def test_results_page_serves_summary_and_woven_view():
    response = client.get("/ui/results")
    assert response.status_code == 200
    text = response.text
    assert "Scenario results" in text
    assert "Hard-rule violations" in text
    assert "Blind comparison" in text
