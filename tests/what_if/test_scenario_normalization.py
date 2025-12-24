import pytest

from src.what_if.scenario import normalize_scenario, ScenarioValidationError

from tests.conftest import make_job_data


def base_raw_scenario():
    return {
        "scenario": {
            "min_years_override": 3,
            "education_required_override": None,
            "skills_add": {"must_have": [], "nice_to_have": []},
            "skills_remove": {"must_have": [], "nice_to_have": []}
        },
        "evaluation": {
            "match_mode": "partial",
            "partial_match_weight": 0.5,
            "must_have_gate_mode": "coverage_min",
            "must_have_coverage_min": 0.7,
            "include_nice_to_have": True,
            "weights_override": None
        },
        "optimization": {
            "objective": "maximize_candidate_count",
            "overall_score_threshold": 50
        }
    }


def test_normalize_scenario_maps_match_mode():
    job_data = make_job_data()
    raw = base_raw_scenario()
    normalized, warnings = normalize_scenario(raw, job_data)
    assert normalized["evaluation"]["match_mode"] == "partial_ok"
    assert warnings == []


def test_normalize_scenario_warns_on_gate_mode_override():
    job_data = make_job_data()
    raw = base_raw_scenario()
    raw["evaluation"]["must_have_gate_mode"] = "all"
    raw["evaluation"]["must_have_coverage_min"] = 0.5
    normalized, warnings = normalize_scenario(raw, job_data)
    assert normalized["evaluation"]["must_have_gate_mode"] == "all"
    assert any("coverage_min is ignored" in warning for warning in warnings)


def test_normalize_scenario_rejects_unknown_skills():
    job_data = make_job_data()
    raw = base_raw_scenario()
    raw["scenario"]["skills_add"]["must_have"] = ["Unknown Skill"]
    with pytest.raises(ScenarioValidationError) as exc:
        normalize_scenario(raw, job_data)
    assert any("unknown skill" in error.lower() for error in exc.value.errors)


def test_normalize_scenario_skill_move_warning():
    job_data = make_job_data()
    raw = base_raw_scenario()
    raw["scenario"]["skills_add"]["must_have"] = ["skill e"]
    normalized, warnings = normalize_scenario(raw, job_data)
    assert normalized["scenario"]["skills_add"]["must_have"] == ["Skill E"]
    assert any("moved from nice_to_have to must_have" in warning for warning in warnings)


def test_normalize_scenario_rejects_invalid_weights():
    job_data = make_job_data()
    raw = base_raw_scenario()
    raw["evaluation"]["weights_override"] = {
        "must_have": 40,
        "nice_to_have": 20,
        "experience": 20,
        "education": 10
    }
    with pytest.raises(ScenarioValidationError) as exc:
        normalize_scenario(raw, job_data)
    assert any("weights must sum to 100" in error for error in exc.value.errors)
