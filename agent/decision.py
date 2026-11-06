"""Structured decision step and deterministic policy gate."""

import json
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from agent.llm import CompletionClient, create_llm_client
from policies.lookup import get_policies_for
from tools.mock_tools import MOCK_REFUND_LIMIT


class Move(StrEnum):
    ANSWER = "answer"
    CLARIFY = "clarify"
    ACT = "act"
    CONFIRM = "confirm"
    ESCALATE = "escalate"
    DECLINE = "decline"


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Stakes(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Emotion(StrEnum):
    CALM = "calm"
    FRUSTRATED = "frustrated"
    ANXIOUS = "anxious"
    CONFUSED = "confused"
    ANGRY = "angry"


class ToolName(StrEnum):
    SEARCH_CATALOG = "search_catalog"
    LOOKUP_ORDER = "lookup_order"
    TRACK_SHIPMENT = "track_shipment"
    CHECK_RETURN_ELIGIBILITY = "check_return_eligibility"
    GET_CARE_GUIDE = "get_care_guide"
    ISSUE_REFUND = "issue_refund"
    ISSUE_STORE_CREDIT = "issue_store_credit"
    CANCEL_ORDER = "cancel_order"
    CREATE_RETURN_LABEL = "create_return_label"
    UPDATE_ADDRESS = "update_address"
    ESCALATE_TO_HUMAN = "escalate_to_human"


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: ToolName
    inputs: dict[str, Any] = Field(default_factory=dict)


class DecisionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: str
    known: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    move: Move
    confidence: Confidence
    stakes: Stakes
    policy_refs: list[str] = Field(default_factory=list)
    tool_plan: list[ToolCall] = Field(default_factory=list)
    emotion: Emotion = Emotion.CALM
    reason: str
    gate_override: str | None = None


RISKY_TOOLS = {
    "issue_refund",
    "issue_store_credit",
    "cancel_order",
    "create_return_label",
    "update_address",
}
IDENTITY_TOOLS = {
    "lookup_order",
    "track_shipment",
    "check_return_eligibility",
    *RISKY_TOOLS,
}


def apply_policy_gate(
    decision: DecisionRecord,
    *,
    explicit_confirmation: bool = False,
    identity_verified: bool = False,
    refund_amount: float | None = None,
    policy_forbidden: bool = False,
    authority_exceeded: bool = False,
) -> DecisionRecord:
    """Apply deterministic overrides after a model-proposed decision."""
    override: str | None = None
    explanation: str | None = None
    planned_amounts = [
        call.inputs.get("amount")
        for call in decision.tool_plan
        if call.tool in {"issue_refund", "issue_store_credit"}
    ]
    refund_amounts = [float(refund_amount)] if refund_amount is not None else []
    for amount in planned_amounts:
        try:
            refund_amounts.append(float(amount))
        except (TypeError, ValueError):
            continue

    if policy_forbidden:
        override = "policy_forbidden"
        explanation = "The requested outcome is forbidden by mock policy; offer the allowed alternative."
        move = Move.DECLINE
    elif authority_exceeded or any(amount > MOCK_REFUND_LIMIT for amount in refund_amounts):
        override = "outside_agent_authority"
        explanation = "The request exceeds the agent's mock authority and requires human review."
        move = Move.ESCALATE
    elif decision.stakes == Stakes.HIGH:
        override = "high_stakes_review"
        explanation = "This is a high-stakes request and must be reviewed by a human."
        move = Move.ESCALATE
    elif any(call.tool in IDENTITY_TOOLS for call in decision.tool_plan) and not identity_verified:
        override = "identity_verification_required"
        explanation = "Verify the order number with its email address or postcode before proceeding."
        move = Move.CLARIFY
    elif decision.missing and decision.move not in {Move.DECLINE, Move.ESCALATE}:
        override = "required_information_missing"
        explanation = "A required fact is missing; ask one focused question before proceeding."
        move = Move.CLARIFY
    elif decision.confidence == Confidence.LOW and decision.stakes == Stakes.LOW:
        override = "low_confidence_low_stakes"
        explanation = "Confidence is low for a low-stakes request; clarify rather than guess."
        move = Move.CLARIFY
    elif any(call.tool in RISKY_TOOLS for call in decision.tool_plan) and not explicit_confirmation:
        override = "explicit_confirmation_required"
        explanation = "Get the customer's explicit confirmation before this consequential action."
        move = Move.CONFIRM
    elif decision.move == Move.ACT and decision.stakes == Stakes.MEDIUM and not explicit_confirmation:
        override = "medium_stakes_confirmation_required"
        explanation = "Confirm the medium-stakes action before carrying it out."
        move = Move.CONFIRM
    else:
        move = decision.move

    if override is None:
        return decision
    return decision.model_copy(
        update={
            "move": move,
            "gate_override": override,
            "reason": f"{decision.reason.rstrip()} {explanation}",
        }
    )


class DecisionEngine:
    def __init__(self, client: CompletionClient | None = None) -> None:
        self.client = client or create_llm_client()

    def decide(
        self,
        message: str,
        situation: str,
        *,
        history: list[dict[str, str]] | None = None,
        known: list[str] | None = None,
        customer_profile: dict[str, Any] | None = None,
        explicit_confirmation: bool = False,
        identity_verified: bool = False,
        refund_amount: float | None = None,
        policy_forbidden: bool = False,
        authority_exceeded: bool = False,
    ) -> DecisionRecord:
        policies = get_policies_for(situation)
        prompt = self._build_prompt(
            message,
            history or [],
            known or [],
            customer_profile or {},
            policies,
        )
        decision = None
        validation_error: Exception | None = None
        for attempt in range(3):
            raw_decision = self.client.complete(prompt)
            try:
                decision = DecisionRecord.model_validate(_decision_payload(raw_decision))
                break
            except (json.JSONDecodeError, ValidationError, ValueError) as error:
                validation_error = error
                if attempt == 2:
                    raise ValueError(
                        f"Model failed to return a valid decision after three attempts: {error}"
                    ) from error
        if decision is None:
            raise ValueError(f"Model failed to return a valid decision: {validation_error}")
        if decision.gate_override is not None:
            raise ValueError("The model cannot set the deterministic gate override field.")

        available_policy_ids = {policy["id"] for policy in policies}
        unsupported_policy_ids = set(decision.policy_refs) - available_policy_ids
        if unsupported_policy_ids:
            raise ValueError(f"Model referenced policies not supplied for this situation: {sorted(unsupported_policy_ids)}")

        return apply_policy_gate(
            decision,
            explicit_confirmation=explicit_confirmation,
            identity_verified=identity_verified,
            refund_amount=refund_amount,
            policy_forbidden=policy_forbidden,
            authority_exceeded=authority_exceeded,
        )

    @staticmethod
    def _build_prompt(
        message: str,
        history: list[dict[str, str]],
        known: list[str],
        customer_profile: dict[str, Any],
        policies: list[dict[str, Any]],
    ) -> str:
        schema = {
            "intent": "one-line customer goal",
            "known": ["established facts"],
            "missing": ["required facts not yet known"],
            "move": [move.value for move in Move],
            "confidence": [level.value for level in Confidence],
            "stakes": [level.value for level in Stakes],
            "policy_refs": ["policy IDs from the supplied policy list only"],
            "tool_plan": [{"tool": "tool name", "inputs": {"argument": "value"}}],
            "emotion": [emotion.value for emotion in Emotion],
            "reason": "one or two concise sentences",
        }
        output_template = {
            "intent": "customer goal",
            "known": [],
            "missing": [],
            "move": "answer | clarify | act | confirm | escalate | decline",
            "confidence": "low | medium | high",
            "stakes": "low | medium | high",
            "policy_refs": [],
            "tool_plan": [],
            "emotion": "calm | frustrated | anxious | confused | angry",
            "reason": "one or two sentences",
        }
        context = {
            "customer_message": message,
            "conversation_history": history,
            "known_facts": known,
            "customer_profile_internal_only": customer_profile,
            "applicable_mock_policies": policies,
        }
        return (
            "You are the internal decision step for a fictional rug-store support agent. "
            "Choose exactly one move. Do not write a customer-facing reply or perform tools. "
            "Never invent facts. Use only supplied policy IDs. For missing information, list only "
            "what is needed next. Return exactly one JSON object with the fields in the template, "
            "with no extra context fields and no markdown.\n"
            f"Output template: {json.dumps(output_template, ensure_ascii=True)}\n"
            f"Allowed values: {json.dumps(schema, ensure_ascii=True)}\n"
            f"Context: {json.dumps(context, ensure_ascii=True)}"
        )


def _json_payload(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            stripped = "\n".join(lines[1:-1]).strip()
    return stripped


def _decision_payload(text: str) -> dict[str, Any]:
    payload = json.loads(_json_payload(text))
    if isinstance(payload, dict) and isinstance(payload.get("decision_record"), dict):
        payload = payload["decision_record"]
    if not isinstance(payload, dict):
        raise ValueError("The model decision must be a JSON object.")

    for echoed_field in {
        "customer_message",
        "conversation_history",
        "known_facts",
        "customer_profile_internal_only",
        "applicable_mock_policies",
    }:
        payload.pop(echoed_field, None)
    if "tool_plan" not in payload and isinstance(payload.get("tool"), list):
        payload["tool_plan"] = payload.pop("tool")
    elif payload.get("tool") == "":
        payload["tool_plan"] = []
        payload.pop("tool")
    return payload