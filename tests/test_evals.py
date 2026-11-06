from collections import Counter

from evals.scenarios import EXPECTED_CATEGORY_COUNTS, load_scenarios


def test_scenario_library_expands_to_sixty_complete_cases():
    scenarios = load_scenarios()

    assert len(scenarios) == 60
    assert Counter(scenario["category"] for scenario in scenarios) == EXPECTED_CATEGORY_COUNTS
    assert all(scenario["hidden_facts"]["synthetic_only"] for scenario in scenarios)
    assert all(scenario["expected_moves"] for scenario in scenarios)
    assert all(scenario["forbidden_behaviours"] for scenario in scenarios)


def test_scenario_ids_are_unique_and_turns_have_situations():
    scenarios = load_scenarios()

    assert len({scenario["id"] for scenario in scenarios}) == 60
    assert all(
        turn["message"] and turn["situation"]
        for scenario in scenarios
        for turn in scenario["customer_turns"]
    )
