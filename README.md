# ChitChatCho

A phased portfolio project for a text-first rug-store support agent. All customer, product, order, and policy data is synthetic. This repository currently contains Phase 0 setup only.

## Phase 0 Setup

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

Make one live Claude smoke call:

```powershell
python -m app.model_smoke
```

The minimal FastAPI chat endpoint can also be started with `python -m uvicorn app.main:app --reload`; it exposes `GET /health` and `POST /chat` with a JSON body such as `{"message":"Hello"}`. `LLM_PROVIDER` defaults to `gemini` and `LLM_MODEL` to `gemini-3.8-flash`. Anthropic remains available for the planned later switch by setting `LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY`, and a Claude model in `LLM_MODEL`.

See [docs/decisions.md](docs/decisions.md) for Phase 0 setup choices.