"""Model-based judge for the eight-item behavior rubric."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agent.llm import CompletionClient, create_llm_client


RUBRIC_PATH = Path(__file__).with_name("rubric.json")
RUBRIC = json.loads(RUBRIC_PATH.read_text(encoding="utf-8"))
RUBRIC_IDS = tuple(item["id"] for item in RUBRIC["items"])


class RubricResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scores: dict[str, int]
    evidence: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_scores(self):
        if set(self.scores) != set(RUBRIC_IDS):
            raise ValueError("Judge must provide exactly one score for every rubric item.")
        if any(isinstance(score, bool) or not 1 <= score <= 5 for score in self.scores.values()):
            raise ValueError("Every rubric score must be an integer from 1 to 5.")
        if any(not isinstance(score, int) for score in self.scores.values()):
            raise ValueError("Every rubric score must be an integer from 1 to 5.")
        return self


class RubricJudge:
    def __init__(self, client: CompletionClient | None = None) -> None:
        self.client = client if client is not None else create_llm_client()

    def score(self, transcript: dict[str, Any]) -> RubricResult:
        prompt = (
            "You are a careful evaluator of a synthetic rug-store support-agent transcript. "
            "Score each rubric criterion from 1 to 5 using the full transcript. Use only evidence "
            "in the transcript. Do not reward politeness when the move or facts are wrong. Return "
            "JSON only with keys scores (all rubric IDs, integer values 1-5) and evidence (brief "
            "notes for scores below 4). Do not infer missing facts.\n"
            f"Rubric: {json.dumps(RUBRIC, ensure_ascii=True)}\n"
            f"Transcript: {json.dumps(transcript, ensure_ascii=True)}"
        )
        raw = self.client.complete(prompt).strip()
        if raw.startswith("```"):
            lines = raw.splitlines()
            if len(lines) >= 3 and lines[-1].strip() == "```":
                raw = "\n".join(lines[1:-1]).strip()
        result = RubricResult.model_validate_json(raw)
        return result
