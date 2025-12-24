import pytest

from src.what_if.evaluator import evaluate_applications
from src.what_if.scenario import DEFAULT_SCENARIO, ScenarioValidationError

from tests.conftest import deep_copy, make_job_data, make_match_data, make_application


def make_scenario():
    scenario = deep_copy(DEFAULT_SCENARIO)
    scenario["scenario"]["education_required_override"] = False
    scenario["evaluation"]["match_mode"] = "partial_ok"
    scenario["evaluation"]["must_have_gate_mode"] = "coverage_min"
    scenario["evaluation"]["must_have_coverage_min"] = 0.6
    scenario["optimization"]["overall_score_threshold"] = 50
    return scenario


def test_evaluator_partial_match_scores():
    job_data = make_job_data()
    match_data = make_match_data(
        must_full=["Skill A", "Skill B"],
        must_partial=["Skill C"],
        must_missing=["Skill D"],
        nice_full=[],
        nice_partial=[],
        nice_missing=["Skill E", "Skill F"]
    )
    application = make_application(1, "Alex", "DevOps", "CloudScale", match_data, 40.0)
    scenario = make_scenario()

    result = evaluate_applications(
        [application],
        job_data,
        scenario,
        include_details=True,
        include_summary_table=True
    )

    candidate = result["candidates"][0]
    assert candidate["must_have_score"] == 62
    assert candidate["must_have_gate_pass"] is True
    assert candidate["overall_score"] == 55.4


def test_evaluator_full_only_requires_full_partial_data():
    job_data = make_job_data()
    match_data = make_match_data(
        must_full=["Skill A"],
        must_partial=[],
        must_missing=["Skill B", "Skill C", "Skill D"],
        nice_full=[],
        nice_partial=[],
        nice_missing=["Skill E", "Skill F"]
    )
    match_data["must_have_skills"].pop("full_matches")
    match_data["must_have_skills"].pop("partial_matches")
    application = make_application(2, "Jamie", "DevOps", "CloudScale", match_data, 30.0)

    scenario = make_scenario()
    scenario["evaluation"]["match_mode"] = "full_only"

    with pytest.raises(ScenarioValidationError):
        evaluate_applications([application], job_data, scenario)


def test_summary_table_sorted_by_original_score():
    job_data = make_job_data()
    match_data = make_match_data(
        must_full=["Skill A", "Skill B"],
        must_partial=["Skill C"],
        must_missing=["Skill D"],
        nice_full=[],
        nice_partial=[],
        nice_missing=["Skill E", "Skill F"]
    )
    high_score_app = make_application(3, "Casey", "DevOps", "CloudScale", match_data, 90.0)
    low_score_app = make_application(4, "Robin", "DevOps", "CloudScale", match_data, 30.0)
    scenario = make_scenario()

    result = evaluate_applications(
        [low_score_app, high_score_app],
        job_data,
        scenario,
        include_summary_table=True
    )

    table = result["summary_table"]
    assert table[0]["original_score"] == 90.0
    assert table[1]["original_score"] == 30.0
