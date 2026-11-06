# ChitChatCho

A phased portfolio project for a text-first rug-store support agent. All customer, product, order, shipment, and policy data is synthetic.

## Setup

Requires Python 3.11 or newer. From PowerShell in the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Put `GEMINI_API_KEY=your-key` in the ignored project-root `.env` file or set it in your process environment before making an initial live model call. The app loads `.env` automatically, while process environment values take precedence. Keep the key out of source control:

```powershell
$env:GEMINI_API_KEY = "your-key"
```

Run the deterministic tests and initialize the local SQLite database:

```powershell
python -m pytest
python -m app.seed_db
```

Make a live model smoke call using the configured provider and model:

```powershell
python -m app.model_smoke
```

The minimal FastAPI chat endpoint can also be started with `python -m uvicorn app.main:app --reload`; it exposes `GET /health` and `POST /chat` with a JSON body such as `{"message":"Hello"}`. `LLM_PROVIDER` defaults to `gemini` and `LLM_MODEL` to `gemini-3.8-flash`. Anthropic remains available for the planned later switch by setting `LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY`, and a Claude model in `LLM_MODEL`.

## Mock Backend

`python -m app.seed_db` initializes the local SQLite database with 15 synthetic customers, 30 catalog products, 40 orders across processing, shipped, delivered, delayed, and damaged-reported states, and mock shipment data. All seed identities use reserved `.invalid` emails.

The tools are available directly from Python:

```python
from tools import MockTools

tools = MockTools()
tools.search_catalog(category="runner", material="wool")
tools.lookup_order("MOCK-ORDER-001", postcode="MOCK 1001")
```

Order lookup, tracking, return checks, and order mutations require an order number plus matching email or postcode. Risky mutations also require `confirmed=True` and a stable `idempotency_key`. Every call and result is recorded in SQLite; no real store, payment, or shipping service is contacted.

## Decision Layer

`DecisionEngine.decide(message, situation, ...)` asks the configured model for a structured decision record and validates its move, confidence, stakes, emotion, policy references, and tool plan. A deterministic gate then enforces the policy/authority limits, identity requirements, missing facts, stakes, and confirmation requirements. The gate scenario table runs locally without a model call.

`POST /conversations/{conversation_id}/turns` accepts a customer message, its validated decision record, and any tool results, then writes a customer-facing reply and stores the turn. `GET /conversations/{conversation_id}/transcript` shows each customer message and reply beside its decision record. Prior turns are not automatically loaded into future prompts yet; conversation memory is reserved for Phase 5. The original `POST /chat` route remains a provider smoke endpoint.

See [docs/manual_chats.md](docs/manual_chats.md) for ten manually drafted sample conversations and [docs/decisions.md](docs/decisions.md) for the design choices.