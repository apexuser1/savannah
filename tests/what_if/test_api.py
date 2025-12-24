import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("LLM_PROVIDER", "openai")

from fastapi.testclient import TestClient

from src.api import app as app_module


def test_api_summary_disallows_include_details(monkeypatch):
    client = TestClient(app_module.app)

    def override_db():
        yield object()

    app_module.app.dependency_overrides[app_module.get_db] = override_db

    response = client.post(
        "/api/what-if",
        json={
            "job_id": 1,
            "scenario_text": "test scenario",
            "summary": True,
            "include_details": True
        }
    )

    assert response.status_code == 400
    assert "summary cannot be used" in response.json()["detail"]


def test_api_summary_returns_table(monkeypatch):
    client = TestClient(app_module.app)

    def override_db():
        yield object()

    app_module.app.dependency_overrides[app_module.get_db] = override_db

    def fake_run_what_if(*_args, **_kwargs):
        return {
            "summary_table": [
                {
                    "id": 1,
                    "candidate": "Alex",
                    "job_title": "DevOps",
                    "company": "CloudScale",
                    "recommendation": "Consider",
                    "created": "2024-01-01 12:00",
                    "original_score": 40.0,
                    "scenario_score": 55.4
                }
            ]
        }

    monkeypatch.setattr(app_module, "run_what_if", fake_run_what_if)

    response = client.post(
        "/api/what-if",
        json={
            "job_id": 1,
            "scenario_text": "test scenario",
            "summary": True
        }
    )

    assert response.status_code == 200
    payload = response.json()
    assert "summary_table" in payload
    assert payload["summary_table"][0]["original_score"] == 40.0
