"""Run scripted evaluation scenarios through the decision, tools, and reply steps."""

import argparse
import gc
import json
import re
import sqlite3
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from agent.decision import DecisionEngine, Move
from agent.llm import CompletionClient
from agent.memory import MemoryStore
from agent.reply import ReplyEngine
from evals.hard_rules import RISKY_TOOLS, check_hard_rules
from evals.judge import RUBRIC_IDS, RubricJudge
from evals.scenarios import load_scenarios
from policies.lookup import get_policies_for
from tools import MockTools


RESULTS_DIR = Path(__file__).with_name("results")
POLICY_NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")


class EvaluationRunner:
    def __init__(
        self,
        decision_client_factory: Callable[[], CompletionClient] | None = None,
        reply_client_factory: Callable[[], CompletionClient] | None = None,
        judge: RubricJudge | None = None,
    ) -> None:
        self.decision_client_factory = decision_client_factory
        self.reply_client_factory = reply_client_factory
        self.judge = judge

    def run_scenario(self, scenario: dict[str, Any], *, use_judge: bool = True) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="chitchatcho-eval-") as temporary_dir:
            database_path = Path(temporary_dir) / "scenario.sqlite3"
            tools = MockTools(database_path)
            memory = MemoryStore(database_path)
            decision_engine = DecisionEngine(
                self.decision_client_factory() if self.decision_client_factory else None
            )
            reply_engine = ReplyEngine(
                self.reply_client_factory() if self.reply_client_factory else None
            )
            identity = scenario["hidden_facts"].get("verified_identity", {})
            order_id = identity.get("order_id")
            email = identity.get("email")
            postcode = identity.get("postcode")
            context = memory.load_context(
                scenario["id"], order_id=order_id, email=email, postcode=postcode
            )
            history: list[dict[str, str]] = []
            known = list(scenario["hidden_facts"].get("known_facts", []))
            turns: list[dict[str, Any]] = []
            expected_passes = []

            for index, customer_turn in enumerate(scenario["customer_turns"]):
                explicit_confirmation = bool(customer_turn.get("explicit_confirmation", False))
                decision = decision_engine.decide(
                    customer_turn["message"],
                    customer_turn["situation"],
                    history=history,
                    known=known,
                    customer_profile=context["customer_profile"],
                    explicit_confirmation=explicit_confirmation,
                    identity_verified=context["identity_verified"],
                    policy_forbidden=bool(customer_turn.get("policy_forbidden", False)),
                    authority_exceeded=bool(customer_turn.get("authority_exceeded", False)),
                )
                tool_calls = self._run_tools(
                    tools,
                    decision,
                    scenario["id"],
                    index,
                    identity,
                    explicit_confirmation,
                )
                tool_results = [call["result"] for call in tool_calls]
                reply = reply_engine.reply(
                    customer_turn["message"],
                    decision,
                    tool_results=tool_results,
                    history=history,
                    identity_verified=context["identity_verified"],
                )
                turn_record = {
                    "customer_message": customer_turn["message"],
                    "decision": decision.model_dump(mode="json"),
                    "reply": reply,
                    "tool_calls": tool_calls,
                    "identity_verified": context["identity_verified"],
                    "allowed_dates": [
                        *scenario["hidden_facts"].get("allowed_dates", []),
                        *_dates_from_results(tool_results),
                    ],
                    "allowed_policy_numbers": _policy_numbers(decision.policy_refs, customer_turn["situation"]),
                }
                turns.append(turn_record)
                expected_moves = scenario["expected_moves"]
                expected = expected_moves[min(index, len(expected_moves) - 1)]
                expected_passes.append(decision.move.value == expected)
                history.extend([
                    {"role": "user", "content": customer_turn["message"]},
                    {"role": "assistant", "content": reply},
                ])
                known = list(dict.fromkeys([*known, *decision.known]))
                memory.record_turn(scenario["id"], customer_turn["message"], decision, reply)

            run_record = {
                "scenario_id": scenario["id"],
                "category": scenario["category"],
                "starting_situation": scenario["starting_situation"],
                "persona": scenario["persona"],
                "hidden_facts": scenario["hidden_facts"],
                "expected_moves": scenario["expected_moves"],
                "forbidden_behaviours": scenario["forbidden_behaviours"],
                "turns": turns,
                "expected_move_pass": all(expected_passes),
                "hard_violations": [],
                "rubric": None,
            }
            run_record["protected_markers"], run_record["other_customer_markers"] = (
                self._customer_markers(database_path, identity)
            )
            run_record["hard_violations"] = check_hard_rules(run_record)
            if use_judge:
                judge = self.judge if self.judge is not None else RubricJudge()
                run_record["rubric"] = judge.score(run_record).model_dump(mode="json")
            tools = None
            memory = None
            decision_engine = None
            reply_engine = None
            gc.collect()
            return run_record

    def run_all(
        self,
        scenarios: list[dict[str, Any]] | None = None,
        *,
        use_judge: bool = True,
    ) -> list[dict[str, Any]]:
        return [
            self.run_scenario(scenario, use_judge=use_judge)
            for scenario in (scenarios if scenarios is not None else load_scenarios())
        ]

    @staticmethod
    def _run_tools(
        tools: MockTools,
        decision: Any,
        scenario_id: str,
        turn_index: int,
        identity: dict[str, Any],
        explicit_confirmation: bool,
    ) -> list[dict[str, Any]]:
        calls = []
        permitted_move = decision.move == Move.ACT
        for tool_call in decision.tool_plan:
            tool_name = tool_call.tool.value
            if tool_name == "escalate_to_human":
                permitted = decision.move == Move.ESCALATE
            else:
                permitted = permitted_move
            if not permitted:
                continue
            inputs = dict(tool_call.inputs)
            if tool_name in {
                "lookup_order", "track_shipment", "check_return_eligibility",
                *RISKY_TOOLS,
            }:
                if identity.get("email"):
                    inputs["email"] = identity["email"]
                if identity.get("postcode"):
                    inputs["postcode"] = identity["postcode"]
            if tool_name in RISKY_TOOLS:
                inputs["confirmed"] = explicit_confirmation
                inputs["idempotency_key"] = f"eval:{scenario_id}:{turn_index}:{tool_name}"
            result = getattr(tools, tool_name)(**inputs)
            calls.append({
                "tool": tool_name,
                "inputs": inputs,
                "result": result,
                "explicit_confirmation": explicit_confirmation,
                "action_key": f"{tool_name}:{inputs.get('order_id', '')}",
            })
        return calls

    @staticmethod
    def _customer_markers(
        database_path: Path,
        identity: dict[str, Any],
    ) -> tuple[list[str], list[str]]:
        with sqlite3.connect(database_path) as connection:
            customers = connection.execute(
                "SELECT customer_id, name, email FROM customers"
            ).fetchall()
            orders = connection.execute(
                "SELECT order_id, customer_id FROM orders"
            ).fetchall()
        current_customer_id = None
        if identity.get("order_id") and (identity.get("email") or identity.get("postcode")):
            with sqlite3.connect(database_path) as connection:
                row = connection.execute(
                    """SELECT c.customer_id FROM orders o JOIN customers c ON c.customer_id=o.customer_id
                       WHERE o.order_id=? AND ((? IS NOT NULL AND lower(c.email)=lower(?))
                       OR (? IS NOT NULL AND upper(c.postcode)=upper(?)))""",
                    (identity.get("order_id"), identity.get("email"), identity.get("email"),
                     identity.get("postcode"), identity.get("postcode")),
                ).fetchone()
            current_customer_id = row[0] if row else None
        protected = [value for row in customers for value in (row[1], row[2])]
        other = [
            value
            for row in customers
            if row[0] != current_customer_id
            for value in (row[1], row[2])
        ]
        other.extend(row[0] for row in orders if row[1] != current_customer_id)
        return protected, other


def _dates_from_results(value: Any) -> list[str]:
    dates = []
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(child, str) and ("date" in key.lower() or "delivery" in key.lower()):
                dates.append(child[:10])
            else:
                dates.extend(_dates_from_results(child))
    elif isinstance(value, list):
        for child in value:
            dates.extend(_dates_from_results(child))
    return dates


def _policy_numbers(policy_refs: list[str], situation: str) -> list[str]:
    rules = {rule["id"]: rule["rule"] for rule in get_policies_for(situation)}
    return [
        number
        for policy_id in policy_refs
        for number in POLICY_NUMBER_PATTERN.findall(rules.get(policy_id, ""))
    ]


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    categories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        categories[result["category"]].append(result)
    report: dict[str, Any] = {"scenarios": len(results), "categories": {}}
    for category, cases in sorted(categories.items()):
        rubric_scores = [
            result["rubric"]["scores"]
            for result in cases
            if result.get("rubric")
        ]
        averages = {
            rubric_id: round(
                sum(scores[rubric_id] for scores in rubric_scores) / len(rubric_scores), 2
            )
            for rubric_id in RUBRIC_IDS
        } if rubric_scores else {}
        report["categories"][category] = {
            "scenario_count": len(cases),
            "pass_rate": round(
                sum(
                    bool(case["expected_move_pass"]) and not case["hard_violations"]
                    for case in cases
                ) / len(cases),
                3,
            ),
            "expected_move_pass_rate": round(
                sum(bool(case["expected_move_pass"]) for case in cases) / len(cases), 3
            ),
            "hard_rule_violations": sum(len(case["hard_violations"]) for case in cases),
            "rubric_averages": averages,
        }
    report["hard_rule_violations"] = sum(
        len(result["hard_violations"]) for result in results
    )
    report["pass_rate"] = round(
        sum(bool(result["expected_move_pass"]) and not result["hard_violations"] for result in results)
        / len(results),
        3,
    ) if results else 0.0
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the scripted rug-support evaluation scenarios.")
    parser.add_argument("--limit", type=int, help="Run only the first N scenarios (for smoke testing).")
    parser.add_argument("--no-judge", action="store_true", help="Skip the model-based rubric judge.")
    parser.add_argument("--output", type=Path, default=RESULTS_DIR / "latest.json")
    args = parser.parse_args(argv)
    scenarios = load_scenarios()
    if args.limit is not None:
        scenarios = scenarios[:max(0, args.limit)]
    try:
        results = EvaluationRunner().run_all(scenarios, use_judge=not args.no_judge)
    except Exception as error:
        print(f"Evaluation stopped: {error}", file=sys.stderr)
        return 2

    report = summarize(results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"summary": report, "results": results}, indent=2), encoding="utf-8")
    print(f"Scenarios: {report['scenarios']}")
    for category, details in report["categories"].items():
        print(
            f"{category}: pass={details['pass_rate']:.1%} "
            f"(expected move={details['expected_move_pass_rate']:.1%}); "
            f"hard-rule violations={details['hard_rule_violations']}"
        )
        if details["rubric_averages"]:
            print("  rubric averages: " + ", ".join(
                f"{criterion}={score:.2f}"
                for criterion, score in details["rubric_averages"].items()
            ))
    print(f"Hard-rule violations total: {report['hard_rule_violations']}")
    print(f"Overall pass rate: {report['pass_rate']:.1%}")
    print(f"Transcript report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
