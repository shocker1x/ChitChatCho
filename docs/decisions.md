# Project Decisions

- Phase 0 uses Python's built-in `sqlite3` and a JSON seed file to keep setup inspectable and dependency-light. Seed records are explicitly synthetic and use the reserved `.invalid` email domain.
- Gemini is the initial provider for testing, using `GEMINI_API_KEY` and a configurable model (currently defaulting to `gemini-3.8-flash`, following the configured API's availability response). `CompletionClient` is the provider boundary; Anthropic remains available by setting `LLM_PROVIDER=anthropic` and supplying `ANTHROPIC_API_KEY`, for the planned switch after the final phase. No API key is stored in the repository.
- The initial database contains one customer, one product, and one order. Larger mock datasets and tool behavior belong to later phases.
- The API exposes only a health check and a minimal model-backed chat endpoint for the Phase 0 smoke check. No decision logic, policy data, authentication, or real integrations are included yet.