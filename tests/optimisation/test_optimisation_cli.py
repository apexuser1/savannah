from click.testing import CliRunner

from src.cli import commands


class DummySession:
    def close(self):
        pass


def test_cli_outputs_table_before_candidates(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(commands, "init_database", lambda: None)
    monkeypatch.setattr(commands, "get_db_session", lambda: DummySession())

    def fake_run_optimisation(*_args, **_kwargs):
        return {
            "results": [
                {
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
                    ],
                    "candidates": [
                        {"candidate_name": "Alex", "overall_score": 55.4}
                    ]
                }
            ]
        }

    monkeypatch.setattr(commands, "run_optimisation", fake_run_optimisation)

    with runner.isolated_filesystem():
        with open("optimisation.json", "w", encoding="utf-8") as handle:
            handle.write("{}")

        result = runner.invoke(
            commands.cli,
            ["optimisation", "1", "--optimisation-file", "optimisation.json", "--detail"]
        )

    assert result.exit_code == 0
    table_index = result.output.find("Original Score")
    candidates_index = result.output.find("Candidates:")
    assert table_index != -1
    assert candidates_index != -1
    assert table_index < candidates_index
