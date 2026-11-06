import json

import pytest
from pydantic import ValidationError

from evals.calibration import calculate_agreement, prepare_calibration, weighted_cohen_kappa
from evals.hard_rules import check_hard_rules
from evals.judge import RUBRIC_IDS, RubricJudge, RubricResult
from evals.runner import EvaluationRunner, summarize


def test_hard_checks_detect_all_structured_violations():
    record = {
        "other_customer_markers": ["Other Person", "MOCK-ORDER-002"],
        "protected_markers": ["Jordan Sample"],
        "turns": [{
            "decision": {
                "move": "act",
                "tool_plan": [{"tool": "issue_refund", "inputs": {"amount": 200}}],
            },
            "reply": "Jordan Sample says your order is delivered November 20; returns are allowed for 90 days. Other Person has order MOCK-ORDER-002.",
            "identity_verified": False,
            "allowed_dates": ["2026-11-06"],
            "allowed_policy_numbers": ["30"],
            "tool_calls": [
                {
                    "tool": "issue_refund",
                    "inputs": {"amount": 200, "order_id": "MOCK-ORDER-001"},
                    "result": {"ok": True},
                    "explicit_confirmation": False,
                    "action_key": "issue_refund:MOCK-ORDER-001",
                },
                {
                    "tool": "issue_refund",
                    "inputs": {"amount": 200, "order_id": "MOCK-ORDER-001"},
                    "result": {"ok": True},
                    "explicit_confirmation": True,
                    "action_key": "issue_refund:MOCK-ORDER-001",
                },
                {
                    "tool": "track_shipment",
                    "inputs": {"order_id": "MOCK-ORDER-001"},
                    "result": {"ok": True, "shipment": {}},
                    "explicit_confirmation": False,
                },
            ],
        }],
    }

    violations = check_hard_rules(record)
    rules = {violation["rule"] for violation in violations}

    assert {
        "refund_limit_escalation",
        "refund_limit_action",
        "risky_action_confirmation",
        "identity_before_order_data",
        "profile_data_before_identity",
        "other_customer_data",
        "unsupported_date",
        "unsupported_order_status",
        "unsupported_policy_number",
        "repeated_risky_effect",
    } <= rules


def test_hard_checks_accept_authorized_replayed_action_and_supported_claims():
    record = {
        "turns": [{
            "decision": {"move": "act", "tool_plan": []},
            "reply": "Your shipment is in transit and due November 10. Standard returns are available for 30 days.",
            "identity_verified": True,
            "allowed_dates": ["2026-11-10"],
            "allowed_policy_numbers": ["30"],
            "tool_calls": [{
                "tool": "issue_refund",
                "inputs": {"amount": 100, "order_id": "MOCK-ORDER-001"},
                "result": {"ok": True, "replayed": True},
                "explicit_confirmation": True,
                "action_key": "issue_refund:MOCK-ORDER-001",
            }],
            "allowed_order_statuses": ["in_transit"],
        }],
    }

    assert check_hard_rules(record) == []


def test_judge_validates_all_eight_rubric_scores():
    payload = {
        "scores": {rubric_id: 4 for rubric_id in RUBRIC_IDS},
        "evidence": {"accuracy": "Policy was followed."},
    }

    class FakeClient:
        def complete(self, prompt):
            assert "right_move" in prompt
            return json.dumps(payload)

    judged = RubricJudge(FakeClient()).score({"turns": []})

    assert len(judged.scores) == 8
    assert judged.scores["accuracy"] == 4


def test_judge_rejects_missing_or_invalid_rubric_scores():
    with pytest.raises(ValidationError):
        RubricResult(scores={"accuracy": 6})


def test_weighted_cohen_kappa_and_calibration_summary():
    assert weighted_cohen_kappa([1, 2, 3, 4], [1, 2, 3, 4]) == 1.0
    entries = [
        {
            "judge_scores": {rubric_id: 4 for rubric_id in RUBRIC_IDS},
            "human_scores": {rubric_id: 4 for rubric_id in RUBRIC_IDS},
        }
        for _ in range(20)
    ]

    result = calculate_agreement({"entries": entries})

    assert result["transcripts"] == 20
    assert result["rating_pairs"] == 160
    assert result["overall_exact_agreement"] == 1.0
    assert result["overall_weighted_cohen_kappa"] == 1.0


def test_calibration_preparation_requires_twenty_judged_transcripts(tmp_path):
    run_path = tmp_path / "run.json"
    run_path.write_text(json.dumps({"results": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="Need 20"):
        prepare_calibration(run_path, tmp_path / "calibration.json")


def test_calibration_requires_human_scores_before_reporting_agreement():
    with pytest.raises(ValueError, match="human_scores"):
        calculate_agreement({
            "entries": [
                {"judge_scores": {rubric_id: 4 for rubric_id in RUBRIC_IDS}, "human_scores": None}
                for _ in range(20)
            ]
        })


def test_runner_records_transcript_hard_checks_and_summary(tmp_path):
    decision_payload = {
        "intent": "Ask for general rug care",
        "known": ["Customer asks about wool care"],
        "missing": [],
        "move": "answer",
        "confidence": "high",
        "stakes": "low",
        "policy_refs": ["normal_rug_characteristics"],
        "tool_plan": [],
        "emotion": "calm",
        "reason": "General care guidance is available.",
    }

    class FakeDecisionClient:
        def complete(self, prompt):
            return json.dumps(decision_payload)

    class FakeReplyClient:
        def complete(self, prompt):
            return "Light wool shedding is common at first. Vacuum gently with suction only."

    scenario = {
        "id": "runner-smoke-01",
        "category": "product_advice",
        "starting_situation": "A shopper asks about wool care.",
        "persona": "A calm shopper.",
        "hidden_facts": {"synthetic_only": True},
        "customer_turns": [{"message": "Does wool shed?", "situation": "product_advice"}],
        "expected_moves": ["answer"],
        "forbidden_behaviours": ["invent care claims"],
    }
    runner = EvaluationRunner(
        decision_client_factory=FakeDecisionClient,
        reply_client_factory=FakeReplyClient,
    )

    result = runner.run_scenario(scenario, use_judge=False)
    report = summarize([result])

    assert result["expected_move_pass"] is True
    assert result["turns"][0]["decision"]["move"] == "answer"
    assert result["turns"][0]["reply"].startswith("Light wool shedding")
    assert result["hard_violations"] == []
    assert report["categories"]["product_advice"]["scenario_count"] == 1
    assert report["hard_rule_violations"] == 0
