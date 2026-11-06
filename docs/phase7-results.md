# Phase 7 Evaluation Results

## Acceptance Rate

The evaluation report defines a scenario as passing when its expected move matches and it has no deterministic hard-rule violations. The completed 60-scenario runs measured:

| Run | Passing scenarios | Pass rate | Hard-rule violations |
| --- | ---: | ---: | ---: |
| Baseline (`evals/results/latest.json`) | 44 / 60 | 73.3% | 3 |
| Iteration 2 (`evals/results/phase7-iteration2.json`) | 54 / 60 | 90.0% | 1 |

That is an increase of 10 passing scenarios, or 16.7 percentage points. Iteration 2 cleared the 85% scenario target and every overall rubric-item average was at least 4.0. It did **not** yet satisfy the separate zero-hard-rule-violations target.

## Category Results

| Category | Baseline | Iteration 2 |
| --- | ---: | ---: |
| Angry or distressed customers | 66.7% | 83.3% |
| Cancel or change order | 100% | 83.3% |
| Changed mind or contradiction | 100% | 100% |
| Damaged or wrong item | 75% | 100% |
| Order status and late delivery | 87.5% | 100% |
| Policy pressure and privacy | 50% | 100% |
| Product advice | 33.3% | 50% |
| Returns and exchanges | 70% | 90% |
| Vague or incomplete requests | 100% | 100% |

## Rubric Averages

| Criterion | Baseline | Iteration 2 |
| --- | ---: | ---: |
| Right move | 4.67 | 4.83 |
| Emotion | 4.28 | 4.27 |
| Necessary questions | 4.85 | 4.77 |
| Accuracy | 4.78 | 4.92 |
| Clear next step | 4.83 | 4.83 |
| Natural language | 4.78 | 4.88 |
| Uncertainty | 4.97 | 4.98 |
| Recovery | 4.30 | 4.40 |

Rubric scores come from the model judge. The small emotion and question-efficiency changes are not improvements; emotion was effectively flat, while necessary-question score slipped slightly. Model judgment and response generation are stochastic, so small run-to-run changes should not be overinterpreted.

## What Changed

- Added explicit `policy_forbidden` scenario facts so the deterministic decision gate declines customer requests to disclose another customer's information or bypass final-sale, privacy, and delivery-promise rules. Policy-pressure/privacy pass rate rose from 50% to 100%.
- Added case-specific expected moves for clear answers, declines, escalations, and clarifications instead of applying one broad category default. Product advice rose from 33.3% to 50%; returns rose from 70% to 90%.
- Supplied known delivered status for damage-report scenarios and stopped treating an order number repeated from the customer's own message as disclosure of another customer's data. Damage handling rose from 75% to 100%, and the corresponding status/privacy checker false positives were removed.
- Added Gemini request pacing, checkpoint output, resume support, bounded retry for transient 503s, and normalization/retry for malformed decision JSON. These made the long evaluation reproducible under free-tier quotas and provider response variation; they do not themselves count as scenario-quality gains.

## Remaining Hard-Rule Item and Status

Iteration 2's one counted violation was `unsupported_policy_number` in `returns_and_exchanges-06`. The customer said “31 days,” and the reply accurately contrasted that fact with the mock 30-day return policy. The checker did not yet treat numbers stated by the customer as grounded context. The checker was updated to allow numbers from the customer message, and emotion guidance was strengthened to acknowledge the specific stated feeling or impact.

A third full evaluation was started to validate those changes, but the run was cancelled before it completed. Its `phase7-final.json` file is a partial one-scenario report and is not an acceptance result. Therefore the measured 90.0% is the latest **completed** run, while zero hard violations after the checker fix remains unverified. Phase 8 should wait for a completed rerun that confirms zero violations and at least an 85% pass rate.
