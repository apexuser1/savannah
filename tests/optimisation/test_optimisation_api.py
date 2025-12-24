import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("LLM_PROVIDER", "openai")

from fastapi.testclient import TestClient

from src.api import app as app_module


def test_api_optimisation_overrides(monkeypatch):
    client = TestClient(app_module.app)

    def override_db():
        yield object()

    app_module.app.dependency_overrides[app_module.get_db] = override_db

    captured = {}

    def fake_run_optimisation(*_args, **kwargs):
        captured["candidate_count_override"] = kwargs.get("candidate_count_override")
        captured["top_k_override"] = kwargs.get("top_k_override")
        return {"results": []}

    monkeypatch.setattr(app_module, "run_optimisation", fake_run_optimisation)

    response = client.post(
        "/api/optimisation",
        json={
            "job_id": 1,
            "optimisation": {"target": {"candidate_count": 1}, "strategy": {"name": "beam"}},
            "candidate_count": 10,
            "top_k": 3
        }
    )

    assert response.status_code == 200
    assert captured["candidate_count_override"] == 10
    assert captured["top_k_override"] == 3
