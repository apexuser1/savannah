"""Orchestration for scenario parsing and evaluation."""
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from src.database.models import Job, Application, Candidate
from src.what_if.evaluator import evaluate_applications
from src.what_if.scenario import (
    ScenarioValidationError,
    parse_scenario_text,
    normalize_scenario,
    build_shock_report
)


def run_what_if(
    db: Session,
    job_id: int,
    scenario_text: Optional[str] = None,
    scenario_payload: Optional[Dict[str, Any]] = None,
    overrides: Optional[Dict[str, Any]] = None,
    include_details: bool = False,
    include_summary: bool = False
) -> Dict[str, Any]:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise ScenarioValidationError([f"Job {job_id} not found."])

    if scenario_payload is None and not scenario_text:
        raise ScenarioValidationError(
            ["Provide scenario_text or scenario payload."]
        )

    if scenario_payload is None:
        raw_scenario = parse_scenario_text(scenario_text, job.job_data)
    else:
        raw_scenario = scenario_payload

    normalized, warnings = normalize_scenario(raw_scenario, job.job_data, strict=True)
    if overrides:
        normalized = _apply_overrides(normalized, overrides)

    shock_report = build_shock_report(job.job_data, normalized)

    applications = (
        db.query(Application)
        .join(Candidate)
        .filter(Application.job_id == job_id)
        .all()
    )

    evaluation = evaluate_applications(
        applications,
        job.job_data,
        normalized,
        include_details=include_details,
        include_summary_table=include_summary
    )

    all_warnings = warnings + evaluation.get("warnings", [])
    result = {
        "job_id": job_id,
        "normalized_scenario": normalized,
        "shock_report": shock_report,
        "warnings": all_warnings,
        "summary": evaluation.get("summary", {})
    }

    if include_details:
        result["candidates"] = evaluation.get("candidates", [])
    if include_summary:
        result["summary_table"] = evaluation.get("summary_table", [])

    return result


def _apply_overrides(
    scenario: Dict[str, Any],
    overrides: Dict[str, Any]
) -> Dict[str, Any]:
    errors = []
    evaluation = scenario["evaluation"]
    optimization = scenario["optimization"]

    match_mode = overrides.get("match_mode")
    if match_mode:
        match_mode = match_mode.strip().lower()
        if match_mode in ("full", "full_only"):
            evaluation["match_mode"] = "full_only"
        elif match_mode in ("partial", "partial_ok"):
            evaluation["match_mode"] = "partial_ok"
        else:
            errors.append("match_mode must be full or partial.")

    if "partial_match_weight" in overrides:
        weight = overrides.get("partial_match_weight")
        if weight is None:
            pass
        elif not isinstance(weight, (int, float)) or isinstance(weight, bool):
            errors.append("partial_match_weight must be a number.")
        elif weight < 0 or weight > 1:
            errors.append("partial_match_weight must be between 0 and 1.")
        else:
            evaluation["partial_match_weight"] = float(weight)

    if "overall_score_threshold" in overrides:
        threshold = overrides.get("overall_score_threshold")
        if threshold is None:
            pass
        elif not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
            errors.append("overall_score_threshold must be a number.")
        elif threshold < 0 or threshold > 100:
            errors.append("overall_score_threshold must be between 0 and 100.")
        else:
            optimization["overall_score_threshold"] = float(threshold)

    if errors:
        raise ScenarioValidationError(errors)

    return scenario
