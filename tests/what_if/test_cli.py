from click.testing import CliRunner

from src.cli import commands


class DummySession:
    def close(self):
        pass


def test_cli_summary_output(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(commands, "init_database", lambda: None)
    monkeypatch.setattr(commands, "get_db_session", lambda: DummySession())

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

    monkeypatch.setattr(commands, "run_what_if", fake_run_what_if)

    result = runner.invoke(
        commands.cli,
        ["what-if", "scenario text", "1", "--summary"]
    )

    assert result.exit_code == 0
    assert "Original Score" in result.output
    assert "Scenario Score" in result.output


def test_cli_summary_disallows_explain(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(commands, "init_database", lambda: None)
    monkeypatch.setattr(commands, "get_db_session", lambda: DummySession())

    result = runner.invoke(
        commands.cli,
        ["what-if", "scenario text", "1", "--summary", "--explain"]
    )

    assert result.exit_code != 0
    assert "--summary cannot be used with --explain" in result.output
