import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from agent.decision import DecisionRecord, Move
from agent.memory import MemoryStore
from app.main import app


def make_decision(known):
    return DecisionRecord(
        intent="Customer asks about an order",
        known=known,
        missing=[],
        move=Move.ANSWER,
        confidence="high",
        stakes="low",
        policy_refs=["order_status"],
        tool_plan=[],
        emotion="calm",
        reason="Facts are available in the synthetic conversation.",
    )


def test_conversation_memory_keeps_history_and_accumulates_known_facts(tmp_path):
    store = MemoryStore(tmp_path / "memory.sqlite3")
    store.record_turn(
        "chat-a", "My rug arrived yesterday.", make_decision(["Delivery was yesterday"]),
        "I can help with that.", known_facts=["Customer prefers email updates"],
    )
    store.record_turn(
        "chat-a", "It is unused and still boxed.", make_decision(["Item is unused"]),
        "Thanks, that helps.", known_facts=["delivery was yesterday"],
    )

    context = store.load_context("chat-a")

    assert context["history"] == [
        {"role": "user", "content": "My rug arrived yesterday."},
        {"role": "assistant", "content": "I can help with that."},
        {"role": "user", "content": "It is unused and still boxed."},
        {"role": "assistant", "content": "Thanks, that helps."},
    ]
    assert context["known_facts"] == [
        "Delivery was yesterday",
        "Customer prefers email updates",
        "Item is unused",
    ]
    assert context["identity_verified"] is False
    assert context["customer_profile"] is None


def test_unverified_or_wrong_identity_never_receives_profile(tmp_path):
    store = MemoryStore(tmp_path / "memory.sqlite3")
    store.complete_conversation(
        "chat-owner",
        "Customer asked about a damaged delivery.",
        order_id="MOCK-ORDER-033",
        email="riley@example.invalid",
        preferences={"preferred_material": "wool"},
    )

    without_identity = store.load_context("new-chat")
    wrong_email = store.load_context(
        "new-chat", order_id="MOCK-ORDER-033", email="casey@example.invalid"
    )
    wrong_order_owner = store.load_context(
        "new-chat", order_id="MOCK-ORDER-033", email="jordan@example.invalid"
    )

    for context in (without_identity, wrong_email, wrong_order_owner):
        assert context["identity_verified"] is False
        assert context["customer_profile"] is None


def test_verified_returning_customer_loads_profile_summary_orders_issues_and_preferences(tmp_path):
    store = MemoryStore(tmp_path / "memory.sqlite3")
    store.complete_conversation(
        "chat-first",
        "Customer reported order MOCK-ORDER-033 arrived damaged; photo was received.",
        order_id="MOCK-ORDER-033",
        postcode="MOCK 1003",
        preferences={"preferred_material": "wool", "room": "living room"},
    )

    returning = store.load_context(
        "chat-next", order_id="MOCK-ORDER-033", email="riley@example.invalid"
    )
    profile = returning["customer_profile"]

    assert returning["identity_verified"] is True
    assert profile["name"] == "Riley Demo"
    assert profile["last_conversation_summary"].startswith("Customer reported")
    assert profile["preferences"] == {"preferred_material": "wool", "room": "living room"}
    assert any(order["order_id"] == "MOCK-ORDER-033" for order in profile["past_orders"])
    assert any(issue["order_id"] == "MOCK-ORDER-033" for issue in profile["past_issues"])
    assert "Customer preference: preferred_material=wool" in returning["known_facts"]
    assert any(fact.startswith("Previous conversation summary:") for fact in returning["known_facts"])


def test_completed_conversation_cannot_be_rebound_to_another_customer(tmp_path):
    store = MemoryStore(tmp_path / "memory.sqlite3")
    store.complete_conversation(
        "chat-owner", "Owner summary", order_id="MOCK-ORDER-001", email="jordan@example.invalid"
    )

    context = store.load_context(
        "chat-owner", order_id="MOCK-ORDER-002", email="casey@example.invalid"
    )
    with pytest.raises(PermissionError, match="different verified customer"):
        store.complete_conversation(
            "chat-owner", "Attempted replacement", order_id="MOCK-ORDER-002",
            email="casey@example.invalid",
        )

    assert context["identity_verified"] is False
    assert context["customer_profile"] is None


def test_completion_requires_order_number_and_matching_email_or_postcode(tmp_path):
    store = MemoryStore(tmp_path / "memory.sqlite3")

    with pytest.raises(PermissionError, match="Identity verification failed"):
        store.complete_conversation(
            "chat-a", "Summary", order_id="MOCK-ORDER-001", email="other@example.invalid"
        )
    with pytest.raises(PermissionError, match="Identity verification failed"):
        store.complete_conversation("chat-a", "Summary", order_id="", postcode="MOCK 1001")


def test_memory_api_gates_profile_and_completion(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DEFAULT_DB_PATH", tmp_path / "api-memory.sqlite3")
    client = TestClient(app)

    private_context = client.get("/conversations/api-chat/memory").json()
    assert private_context["identity_verified"] is False
    assert private_context["customer_profile"] is None

    unauthorized = client.post(
        "/conversations/api-chat/complete",
        json={"summary": "Private summary", "order_id": "MOCK-ORDER-001", "email": "wrong@example.invalid"},
    )
    assert unauthorized.status_code == 403

    completed = client.post(
        "/conversations/api-chat/complete",
        json={
            "summary": "Verified synthetic customer asked about wool care.",
            "order_id": "MOCK-ORDER-001",
            "postcode": "MOCK 1001",
            "preferences": {"preferred_material": "wool"},
        },
    )
    assert completed.status_code == 200

    verified_context = client.get(
        "/conversations/api-chat/memory",
        params={"order_id": "MOCK-ORDER-001", "postcode": "MOCK 1001"},
    ).json()
    assert verified_context["customer_profile"]["name"] == "Jordan Sample"
    assert verified_context["customer_profile"]["preferences"]["preferred_material"] == "wool"


def test_known_facts_are_stored_as_structured_json(tmp_path):
    store = MemoryStore(tmp_path / "facts.sqlite3")
    store.record_turn("facts-chat", "I'm looking for wool.", make_decision(["Interested in wool"]), "I can help.")

    with sqlite3.connect(tmp_path / "facts.sqlite3") as connection:
        stored = connection.execute(
            "SELECT known_facts_json FROM conversations WHERE conversation_id='facts-chat'"
        ).fetchone()[0]

    assert json.loads(stored) == ["Interested in wool"]
