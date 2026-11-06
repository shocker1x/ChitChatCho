import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from agent.llm import AnthropicCompletionClient, GeminiCompletionClient, create_llm_client
from app.db import initialize_database
from app.main import app


def test_database_initialization_seeds_synthetic_records(tmp_path):
    database = tmp_path / "test.sqlite3"

    initialize_database(database)
    initialize_database(database)

    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 15
        assert connection.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 30
        assert connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 40
        assert connection.execute("SELECT COUNT(*) FROM shipments").fetchone()[0] == 32
        assert connection.execute("SELECT COUNT(*) FROM conversations").fetchone()[0] == 0


def test_database_seed_contains_only_reserved_mock_identity():
    from app.db import SEED_PATH

    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    assert len(seed["customers"]) == 15
    assert len(seed["products"]) == 30
    assert sum(seed["order_status_counts"].values()) == 40
    assert ".invalid" in seed["customers"][0]["email"]
    assert seed["data_notice"].startswith("All records")


def test_gemini_client_uses_configured_model_and_returns_text(monkeypatch):
    class FakeResponse:
        text = "Hello from a test."

    class FakeModels:
        def generate_content(self, **kwargs):
            assert kwargs["model"] == "gemini-test-model"
            assert kwargs["contents"] == "Say hello"
            return FakeResponse()

    class FakeClient:
        def __init__(self, api_key):
            assert api_key == "test-key"
            self.models = FakeModels()

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("LLM_MODEL", "gemini-test-model")
    monkeypatch.setattr("agent.llm.genai.Client", FakeClient)

    client = create_llm_client()

    assert isinstance(client, GeminiCompletionClient)
    assert client.complete("Say hello") == "Hello from a test."


def test_model_client_requires_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setattr("agent.llm.load_dotenv", lambda **kwargs: None)

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        create_llm_client()


def test_model_client_loads_project_env_file(monkeypatch):
    loaded_paths = []

    def fake_load_dotenv(dotenv_path, override):
        loaded_paths.append(dotenv_path)
        assert override is False
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    class FakeClient:
        def __init__(self, api_key):
            assert api_key == "test-key"

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setattr("agent.llm.load_dotenv", fake_load_dotenv)
    monkeypatch.setattr("agent.llm.genai.Client", FakeClient)

    assert isinstance(create_llm_client(), GeminiCompletionClient)
    assert loaded_paths == [__import__("pathlib").Path(__file__).resolve().parents[1] / ".env"]


def test_anthropic_remains_selectable(monkeypatch):
    class FakeAnthropic:
        def __init__(self, api_key):
            assert api_key == "test-key"

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setattr("agent.llm.Anthropic", FakeAnthropic)

    assert isinstance(create_llm_client(), AnthropicCompletionClient)


def test_chat_endpoint_returns_provider_reply(monkeypatch):
    class FakeClient:
        def complete(self, prompt):
            assert prompt == "Hello"
            return "Hello from the mock provider."

    monkeypatch.setattr("app.main.create_llm_client", lambda: FakeClient())
    response = TestClient(app).post("/chat", json={"message": "Hello"})

    assert response.status_code == 200
    assert response.json() == {"reply": "Hello from the mock provider."}