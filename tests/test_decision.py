import json

import pytest
from pydantic import ValidationError

from agent.decision import (
    DecisionEngine,
    DecisionRecord,
    Move,
    ToolCall,
    apply_policy_gate,
)


DECISION_CASES = [
    {"name": "known product fact", "expected": "answer"},
    {"name": "material advice", "expected": "answer"},
    {"name": "care guidance", "expected": "answer"},
    {"name": "catalog search", "expected": "act", "tools": [{"tool": "search_catalog"}]},
    {"name": "care guide lookup", "expected": "act", "tools": [{"tool": "get_care_guide"}]},
    {"name": "verified order lookup", "expected": "act", "tools": [{"tool": "lookup_order"}], "gate": {"identity_verified": True}},
    {"name": "vague room request", "expected": "clarify", "missing": ["room dimensions"]},
    {"name": "missing order number", "expected": "clarify", "missing": ["order number"]},
    {"name": "low confidence and low stakes", "expected": "clarify", "confidence": "low"},
    {"name": "unverified order lookup", "expected": "clarify", "proposed": "act", "tools": [{"tool": "lookup_order"}]},
    {"name": "unverified shipment tracking", "expected": "clarify", "proposed": "act", "tools": [{"tool": "track_shipment"}]},
    {"name": "unverified return check", "expected": "clarify", "proposed": "act", "tools": [{"tool": "check_return_eligibility"}]},
    {"name": "unconfirmed cancellation", "expected": "confirm", "proposed": "act", "stakes": "medium", "tools": [{"tool": "cancel_order"}], "gate": {"identity_verified": True}},
    {"name": "unconfirmed refund", "expected": "confirm", "proposed": "act", "stakes": "medium", "tools": [{"tool": "issue_refund", "inputs": {"amount": 100}}], "gate": {"identity_verified": True}},
    {"name": "unconfirmed store credit", "expected": "confirm", "proposed": "act", "stakes": "medium", "tools": [{"tool": "issue_store_credit", "inputs": {"amount": 50}}], "gate": {"identity_verified": True}},
    {"name": "unconfirmed return label", "expected": "confirm", "proposed": "act", "stakes": "medium", "tools": [{"tool": "create_return_label"}], "gate": {"identity_verified": True}},
    {"name": "unconfirmed address update", "expected": "confirm", "proposed": "act", "stakes": "medium", "tools": [{"tool": "update_address"}], "gate": {"identity_verified": True}},
    {"name": "generic medium-stakes action", "expected": "confirm", "proposed": "act", "stakes": "medium"},
    {"name": "confirmed medium-stakes action", "expected": "act", "proposed": "act", "stakes": "medium", "gate": {"explicit_confirmation": True}},
    {"name": "confirmed refund at limit", "expected": "act", "proposed": "act", "stakes": "medium", "tools": [{"tool": "issue_refund", "inputs": {"amount": 150}}], "gate": {"identity_verified": True, "explicit_confirmation": True}},
    {"name": "refund above limit in tool plan", "expected": "escalate", "proposed": "act", "stakes": "medium", "tools": [{"tool": "issue_refund", "inputs": {"amount": 151}}], "gate": {"identity_verified": True}},
    {"name": "tool amount wins over lower caller amount", "expected": "escalate", "proposed": "act", "stakes": "medium", "tools": [{"tool": "issue_refund", "inputs": {"amount": 151}}], "gate": {"identity_verified": True, "refund_amount": 100}},
    {"name": "credit above limit in tool plan", "expected": "escalate", "proposed": "confirm", "stakes": "medium", "tools": [{"tool": "issue_store_credit", "inputs": {"amount": 200}}]},
    {"name": "caller refund amount above limit", "expected": "escalate", "gate": {"refund_amount": 151}},
    {"name": "authority exceeded", "expected": "escalate", "gate": {"authority_exceeded": True}},
    {"name": "high-stakes action", "expected": "escalate", "proposed": "act", "stakes": "high", "tools": [{"tool": "cancel_order"}], "gate": {"identity_verified": True}},
    {"name": "high stakes before action", "expected": "escalate", "proposed": "answer", "stakes": "high"},
    {"name": "custom item policy forbids return", "expected": "decline", "proposed": "answer", "gate": {"policy_forbidden": True}},
    {"name": "another customer's data forbidden", "expected": "decline", "proposed": "act", "gate": {"policy_forbidden": True}},
    {"name": "policy denial takes precedence", "expected": "decline", "proposed": "act", "stakes": "high", "gate": {"policy_forbidden": True, "authority_exceeded": True}},
    {"name": "model proposes escalation", "expected": "escalate", "proposed": "escalate"},
    {"name": "model proposes decline", "expected": "decline", "proposed": "decline"},
    {"name": "model proposes clarification", "expected": "clarify", "proposed": "clarify"},
    {"name": "model proposes confirmation", "expected": "confirm", "proposed": "confirm"},
]


def test_handwritten_decision_situations_map_to_expected_moves_without_model():
    assert len(DECISION_CASES) >= 25

    for case in DECISION_CASES:
        decision = DecisionRecord(
            intent=case["name"],
            known=[],
            missing=case.get("missing", []),
            move=case.get("proposed", case["expected"]),
            confidence=case.get("confidence", "high"),
            stakes=case.get("stakes", "low"),
            policy_refs=[],
            tool_plan=[ToolCall(**tool) for tool in case.get("tools", [])],
            emotion="calm",
            reason="The decision follows the stated facts.",
        )
        gated = apply_policy_gate(decision, **case.get("gate", {}))

        assert gated.move.value == case["expected"], case["name"]


def test_decision_engine_builds_structured_prompt_and_applies_gate():
    payload = {
        "intent": "Return an unused rug",
        "known": ["The rug was delivered 10 days ago"],
        "missing": [],
        "move": "answer",
        "confidence": "high",
        "stakes": "low",
        "policy_refs": ["standard_returns"],
        "tool_plan": [],
        "emotion": "calm",
        "reason": "The stated return facts meet the mock window.",
    }

    class FakeClient:
        prompt = ""

        def complete(self, prompt):
            self.prompt = prompt
            return json.dumps(payload)

    client = FakeClient()
    engine = DecisionEngine(client)
    decision = engine.decide(
        "Can I return this rug?",
        "return_request",
        history=[{"role": "user", "content": "It arrived 10 days ago."}],
        known=["Delivered 10 days ago"],
        customer_profile={"preferred_material": "wool"},
    )

    assert decision.move == Move.ANSWER
    assert decision.policy_refs == ["standard_returns"]
    assert "applicable_mock_policies" in client.prompt
    assert "preferred_material" in client.prompt
    assert decision.gate_override is None


def test_decision_engine_escalates_refund_amount_from_model_tool_plan():
    payload = {
        "intent": "Refund above agent authority",
        "known": ["Identity verified"],
        "missing": [],
        "move": "confirm",
        "confidence": "high",
        "stakes": "medium",
        "policy_refs": ["refund_credit_authority"],
        "tool_plan": [{"tool": "issue_refund", "inputs": {"order_id": "MOCK-ORDER-001", "amount": 151}}],
        "emotion": "frustrated",
        "reason": "The customer requested a refund.",
    }

    class FakeClient:
        def complete(self, prompt):
            return json.dumps(payload)

    decision = DecisionEngine(FakeClient()).decide(
        "Please refund 151.", "refund_or_credit", identity_verified=True
    )

    assert decision.move == Move.ESCALATE
    assert decision.gate_override == "outside_agent_authority"


def test_decision_engine_rejects_policy_refs_not_provided_for_situation():
    payload = {
        "intent": "Ask for status",
        "known": [],
        "missing": [],
        "move": "answer",
        "confidence": "high",
        "stakes": "low",
        "policy_refs": ["custom_final_sale"],
        "tool_plan": [],
        "emotion": "calm",
        "reason": "Not relevant.",
    }

    class FakeClient:
        def complete(self, prompt):
            return json.dumps(payload)

    with pytest.raises(ValueError, match="policies not supplied"):
        DecisionEngine(FakeClient()).decide("Where is my order?", "order_status")


def test_decision_record_rejects_invalid_moves_and_extra_fields():
    with pytest.raises(ValidationError):
        DecisionRecord(
            intent="Test",
            move="ignore",
            confidence="high",
            stakes="low",
            reason="Invalid move.",
            unsupported="not allowed",
        )


def test_model_cannot_supply_internal_gate_metadata():
    payload = {
        "intent": "Try to bypass gate",
        "known": [],
        "missing": [],
        "move": "act",
        "confidence": "high",
        "stakes": "low",
        "policy_refs": [],
        "tool_plan": [],
        "emotion": "calm",
        "reason": "Test record.",
        "gate_override": "policy_checked",
    }

    class FakeClient:
        def complete(self, prompt):
            return json.dumps(payload)

    with pytest.raises(ValueError, match="model cannot set"):
        DecisionEngine(FakeClient()).decide("Hello", "product_advice")


def test_decision_parser_normalizes_known_provider_shape_quirks():
    payload = {
        "intent": "Check an order",
        "known": [],
        "missing": ["order number"],
        "move": "clarify",
        "confidence": "high",
        "stakes": "low",
        "policy_refs": ["identity_verification"],
        "tool": [],
        "emotion": "calm",
        "reason": "Order details require identity verification.",
        "customer_message": "Where is my order?",
        "conversation_history": [],
    }

    class FakeClient:
        def complete(self, prompt):
            return json.dumps(payload)

    decision = DecisionEngine(FakeClient()).decide("Where is my order?", "order_status")

    assert decision.move == Move.CLARIFY
    assert decision.tool_plan == []


def test_decision_parser_normalizes_empty_tool_alias():
    payload = {
        "intent": "Check damage report",
        "known": [],
        "missing": ["delivery date"],
        "move": "clarify",
        "confidence": "high",
        "stakes": "low",
        "policy_refs": ["damage_reporting"],
        "tool": "",
        "emotion": "calm",
        "reason": "The reporting time needs confirmation.",
    }

    class FakeClient:
        def complete(self, prompt):
            return json.dumps(payload)

    decision = DecisionEngine(FakeClient()).decide("The rug is damaged.", "damaged_or_wrong_item")

    assert decision.move == Move.CLARIFY
    assert decision.tool_plan == []


def test_decision_engine_retries_malformed_structured_response():
    valid_payload = {
        "intent": "Give wool care guidance",
        "known": [],
        "missing": [],
        "move": "answer",
        "confidence": "high",
        "stakes": "low",
        "policy_refs": ["normal_rug_characteristics"],
        "tool_plan": [],
        "emotion": "calm",
        "reason": "General care guidance is available.",
    }

    class FlakyClient:
        attempts = 0

        def complete(self, prompt):
            self.attempts += 1
            return "{malformed" if self.attempts == 1 else json.dumps(valid_payload)

    client = FlakyClient()
    decision = DecisionEngine(client).decide("Does wool shed?", "product_advice")

    assert decision.move == Move.ANSWER
    assert client.attempts == 2


def test_tool_plan_rejects_unimplemented_tools():
    with pytest.raises(ValidationError):
        ToolCall(tool="delete_customer", inputs={})
