"""Deterministic lookup of mock policy rules by explicit situation key."""

import json
from pathlib import Path
from typing import Any


POLICY_DATA_PATH = Path(__file__).with_name("rules.json")


def get_policies_for(situation: str) -> list[dict[str, Any]]:
    """Return the mock policy rules mapped to a known situation key."""
    policy_data = json.loads(POLICY_DATA_PATH.read_text(encoding="utf-8"))
    situation_key = situation.strip().lower()
    situations = policy_data["situations"]
    if situation_key not in situations:
        known_situations = ", ".join(sorted(situations))
        raise ValueError(f"Unknown situation '{situation}'; expected one of: {known_situations}")

    rules_by_id = {rule["id"]: rule for rule in policy_data["rules"]}
    policy_ids = situations[situation_key]
    missing_ids = [policy_id for policy_id in policy_ids if policy_id not in rules_by_id]
    if missing_ids:
        raise ValueError(f"Situation '{situation_key}' references unknown policies: {missing_ids}")

    return [dict(rules_by_id[policy_id]) for policy_id in policy_ids]