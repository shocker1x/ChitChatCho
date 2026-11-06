"""Load and validate data-defined evaluation scenarios."""

import json
from pathlib import Path
from typing import Any


SCENARIOS_PATH = Path(__file__).with_name("scenarios.json")
EXPECTED_CATEGORY_COUNTS = {
    "order_status_and_late_delivery": 8,
    "damaged_or_wrong_item": 8,
    "returns_and_exchanges": 10,
    "product_advice": 6,
    "cancel_or_change_order": 6,
    "angry_or_distressed_customers": 6,
    "vague_or_incomplete_requests": 5,
    "changed_mind_or_contradiction": 3,
    "policy_pressure_and_privacy": 8,
}
ALLOWED_MOVES = {"answer", "clarify", "act", "confirm", "escalate", "decline"}


def load_scenarios(path: str | Path = SCENARIOS_PATH) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    expanded: list[dict[str, Any]] = []
    categories_seen: dict[str, int] = {}

    for category in data["categories"]:
        category_name = category["name"]
        cases = category["cases"]
        categories_seen[category_name] = len(cases)
        for index, case in enumerate(cases, start=1):
            scenario = {
                "id": f"{category_name}-{index:02d}",
                "category": category_name,
                "starting_situation": category["starting_situation"],
                "persona": category["persona"],
                "hidden_facts": dict(category["hidden_facts"]),
                "customer_turns": [{"message": case["message"], "situation": case["situation"]}],
                "expected_moves": case.get("expected_moves", category["expected_moves"]),
                "forbidden_behaviours": list(category["forbidden_behaviours"]),
            }
            _validate_scenario(scenario)
            expanded.append(scenario)

    if categories_seen != EXPECTED_CATEGORY_COUNTS:
        raise ValueError(
            f"Scenario category counts differ from the plan: {categories_seen}"
        )
    return expanded


def _validate_scenario(scenario: dict[str, Any]) -> None:
    required_fields = {
        "id", "category", "starting_situation", "persona", "hidden_facts",
        "customer_turns", "expected_moves", "forbidden_behaviours",
    }
    missing = required_fields - scenario.keys()
    if missing:
        raise ValueError(f"Scenario {scenario.get('id')} is missing fields: {sorted(missing)}")
    if not scenario["customer_turns"]:
        raise ValueError(f"Scenario {scenario['id']} needs at least one customer turn")
    if any(move not in ALLOWED_MOVES for move in scenario["expected_moves"]):
        raise ValueError(f"Scenario {scenario['id']} has an unsupported expected move")
    if any(not turn.get("message") or not turn.get("situation") for turn in scenario["customer_turns"]):
        raise ValueError(f"Scenario {scenario['id']} has an incomplete customer turn")
