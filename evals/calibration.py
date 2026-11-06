"""Prepare human ratings and calculate rubric-judge agreement."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from evals.judge import RUBRIC_IDS


REQUIRED_TRANSCRIPTS = 20


def prepare_calibration(run_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    run = json.loads(Path(run_path).read_text(encoding="utf-8"))
    scored_results = [
        result for result in run["results"]
        if result.get("rubric") and result.get("rubric", {}).get("scores")
    ]
    if len(scored_results) < REQUIRED_TRANSCRIPTS:
        raise ValueError(
            f"Need {REQUIRED_TRANSCRIPTS} judge-scored transcripts; found {len(scored_results)}."
        )
    entries = []
    for result in scored_results[:REQUIRED_TRANSCRIPTS]:
        entries.append({
            "scenario_id": result["scenario_id"],
            "transcript": result,
            "judge_scores": result["rubric"]["scores"],
            "human_scores": None,
        })
    calibration = {
        "instructions": "Enter one integer from 1 to 5 for every rubric ID in human_scores. Do not edit judge_scores.",
        "rubric_ids": list(RUBRIC_IDS),
        "entries": entries,
    }
    Path(output_path).write_text(json.dumps(calibration, indent=2), encoding="utf-8")
    return calibration


def calculate_agreement(calibration: dict[str, Any]) -> dict[str, Any]:
    entries = calibration.get("entries", [])
    if len(entries) < REQUIRED_TRANSCRIPTS:
        raise ValueError(f"Calibration needs {REQUIRED_TRANSCRIPTS} rated transcripts.")
    per_criterion: dict[str, dict[str, float]] = {}
    all_human: list[int] = []
    all_judge: list[int] = []

    for rubric_id in RUBRIC_IDS:
        human_scores = []
        judge_scores = []
        for entry in entries[:REQUIRED_TRANSCRIPTS]:
            human = entry.get("human_scores")
            judge = entry.get("judge_scores")
            if not isinstance(human, dict) or not isinstance(judge, dict):
                raise ValueError("Every calibration entry needs human_scores and judge_scores.")
            human_value = human.get(rubric_id)
            judge_value = judge.get(rubric_id)
            if not _valid_score(human_value) or not _valid_score(judge_value):
                raise ValueError(
                    f"Complete valid human and judge scores are required for {rubric_id} on all 20 transcripts."
                )
            human_scores.append(human_value)
            judge_scores.append(judge_value)
        exact = sum(left == right for left, right in zip(human_scores, judge_scores)) / REQUIRED_TRANSCRIPTS
        kappa = weighted_cohen_kappa(human_scores, judge_scores)
        per_criterion[rubric_id] = {
            "exact_agreement": round(exact, 4),
            "weighted_cohen_kappa": round(kappa, 4),
        }
        all_human.extend(human_scores)
        all_judge.extend(judge_scores)

    return {
        "transcripts": REQUIRED_TRANSCRIPTS,
        "rating_pairs": len(all_human),
        "overall_exact_agreement": round(
            sum(left == right for left, right in zip(all_human, all_judge)) / len(all_human), 4
        ),
        "overall_weighted_cohen_kappa": round(weighted_cohen_kappa(all_human, all_judge), 4),
        "per_criterion": per_criterion,
    }


def weighted_cohen_kappa(left: list[int], right: list[int]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("Rating lists must have equal, non-zero length.")
    categories = range(1, 6)
    observed = sum(abs(a - b) / 4 for a, b in zip(left, right)) / len(left)
    left_distribution = {score: left.count(score) / len(left) for score in categories}
    right_distribution = {score: right.count(score) / len(right) for score in categories}
    expected = sum(
        left_distribution[a] * right_distribution[b] * abs(a - b) / 4
        for a in categories
        for b in categories
    )
    if expected == 0:
        return 1.0 if observed == 0 else 0.0
    return 1.0 - observed / expected


def _valid_score(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 5


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare or calculate rubric-judge calibration.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", type=Path, help="Prepare a 20-transcript rating sheet from a judge-scored run.")
    group.add_argument("--score", type=Path, help="Calculate agreement from a completed human-rating sheet.")
    parser.add_argument("--output", type=Path, default=Path("evals/calibration.json"))
    parser.add_argument(
        "--result-output",
        type=Path,
        default=Path("evals/calibration_agreement.json"),
        help="Where to save agreement metrics after human ratings are complete.",
    )
    args = parser.parse_args(argv)

    try:
        if args.prepare:
            calibration = prepare_calibration(args.prepare, args.output)
            print(f"Prepared {len(calibration['entries'])} transcripts for human ratings: {args.output}")
            print("Agreement is pending until all human scores are entered.")
            return 0
        scores = calculate_agreement(json.loads(args.score.read_text(encoding="utf-8")))
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"Calibration pending or invalid: {error}", file=sys.stderr)
        return 2

    print(json.dumps(scores, indent=2))
    args.result_output.write_text(json.dumps(scores, indent=2), encoding="utf-8")
    print(f"Agreement results saved to {args.result_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
