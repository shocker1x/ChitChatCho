from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_chat_page_serves_threaded_conversation_and_inspector():
    response = client.get("/ui/chat")
    assert response.status_code == 200
    text = response.text
    assert "Rugs support" in text
    assert "Send" in text
    assert "inspector" in text
    assert "Turn 1" in text


def test_results_page_serves_summary_and_woven_view():
    response = client.get("/ui/results")
    assert response.status_code == 200
    text = response.text
    assert "Scenario results" in text
    assert "Hard-rule violations" in text
    assert "Blind comparison" in text
