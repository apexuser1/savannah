"""Deterministic what-if evaluation rules."""
from typing import Any, Dict, List, Tuple

from src.what_if.scenario import ScenarioValidationError, apply_skill_edits


DEFAULT_WEIGHTS = {
    "must_have": 45.0,
    "nice_to_have": 20.0,
    "experience": 20.0,
    "education": 15.0
}


def evaluate_applications(
    applications: List[Any],
    job_data: Dict[str, Any],
    scenario: Dict[str, Any],
    include_details: bool = False,
    include_summary_table: bool = False
) -> Dict[str, Any]:
    """Evaluate a scenario across a list of applications."""
    warnings: List[str] = []
    results: List[Dict[str, Any]] = []
    scores: List[float] = []
    summary_table: List[Dict[str, Any]] = []

    effective_requirements = apply_skill_edits(job_data, scenario)

    for application in applications:
        candidate = getattr(application, "candidate", None)
        candidate_id = getattr(candidate, "id", None)
        candidate_name = getattr(candidate, "name", None)
        resume_data = getattr(candidate, "resume_data", {}) if candidate else {}
        match_data = getattr(application, "match_data", None)
        if not match_data:
            raise ScenarioValidationError(
                [f"Application {application.id} is missing match_data."]
            )

        candidate_result, warnings = evaluate_candidate(
            candidate_id,
            candidate_name,
            resume_data,
            match_data,
            job_data,
            scenario,
            effective_requirements,
            warnings,
            include_details
        )
        results.append(candidate_result)
        scores.append(candidate_result["overall_score"])

        if include_summary_table:
            original_score = _coalesce_score(getattr(application, "overall_score", None))
            job = getattr(application, "job", None)
            created_at = getattr(application, "created_at", None)
            summary_table.append(
                {
                    "id": getattr(application, "id", None),
                    "candidate": candidate_name or "",
                    "job_title": getattr(job, "title", "") if job else "",
                    "company": getattr(job, "company", "") if job else "",
                    "recommendation": (match_data or {}).get("recommendation", "N/A"),
                    "created": (
                        created_at.strftime("%Y-%m-%d %H:%M")
                        if created_at is not None
                        else ""
                    ),
                    "original_score": original_score,
                    "scenario_score": candidate_result["overall_score"]
                }
            )

    passed = [r for r in results if r["passed"]]
    failed = [r for r in results if not r["passed"]]

    summary = {
        "applications_total": len(results),
        "applications_passed": len(passed),
        "applications_failed": len(failed),
        "average_score": round(sum(scores) / len(scores), 1) if scores else 0.0,
        "min_score": min(scores) if scores else 0.0,
        "max_score": max(scores) if scores else 0.0
    }

    payload = {
        "summary": summary,
        "warnings": warnings
    }
    if include_details:
        payload["candidates"] = results
    if include_summary_table:
        summary_table.sort(
            key=lambda row: _coalesce_score(row.get("original_score")),
            reverse=True
        )
        payload["summary_table"] = summary_table
    return payload


def evaluate_candidate(
    candidate_id: Any,
    candidate_name: Any,
    resume_data: Dict[str, Any],
    match_data: Dict[str, Any],
    job_data: Dict[str, Any],
    scenario: Dict[str, Any],
    effective_requirements: Dict[str, List[str]],
    warnings: List[str],
    include_details: bool
) -> Tuple[Dict[str, Any], List[str]]:
    """Score a single candidate against the scenario."""
    evaluation = scenario["evaluation"]
    optimization = scenario["optimization"]

    match_mode = evaluation["match_mode"]
    partial_weight = evaluation["partial_match_weight"]

    must_bucket = _score_requirement_bucket(
        effective_requirements["must_have"],
        match_data.get("must_have_skills"),
        match_mode,
        partial_weight,
        "must_have_skills",
        warnings
    )
    nice_bucket = _score_requirement_bucket(
        effective_requirements["nice_to_have"],
        match_data.get("nice_to_have_skills"),
        match_mode,
        partial_weight,
        "nice_to_have_skills",
        warnings
    )

    gate_pass = _must_have_gate_pass(
        must_bucket,
        match_mode,
        evaluation["must_have_gate_mode"],
        evaluation["must_have_coverage_min"]
    )

    experience_score, candidate_years, required_years = _score_experience(
        match_data,
        job_data,
        scenario
    )

    education_score, education_detail = _score_education(
        resume_data,
        job_data,
        scenario
    )

    overall_score = _score_overall(
        must_bucket["score"],
        nice_bucket["score"],
        experience_score,
        education_score,
        evaluation
    )

    threshold = optimization["overall_score_threshold"]
    passed = gate_pass and overall_score >= threshold

    candidate_result = {
        "candidate_id": candidate_id,
        "candidate_name": candidate_name,
        "overall_score": overall_score,
        "passed": passed,
        "threshold": threshold,
        "must_have_gate_pass": gate_pass,
        "must_have_score": must_bucket["score"],
        "nice_to_have_score": nice_bucket["score"],
        "experience_score": experience_score,
        "education_score": education_score
    }

    if include_details:
        candidate_result.update(
            {
                "must_have": must_bucket,
                "nice_to_have": nice_bucket,
                "experience": {
                    "candidate_years": candidate_years,
                    "required_years": required_years
                },
                "education": education_detail
            }
        )

    return candidate_result, warnings


def _score_requirement_bucket(
    requirements: List[str],
    match_bucket: Dict[str, Any],
    match_mode: str,
    partial_weight: float,
    label: str,
    warnings: List[str]
) -> Dict[str, Any]:
    if not isinstance(match_bucket, dict):
        raise ScenarioValidationError([f"match_data.{label} is missing or invalid."])

    full_matches = match_bucket.get("full_matches")
    partial_matches = match_bucket.get("partial_matches")
    missing_skills = match_bucket.get("missing_skills")
    matched_skills = match_bucket.get("matched_skills")

    legacy_mode = False
    if full_matches is None or partial_matches is None:
        legacy_mode = True
        full_matches = matched_skills or []
        partial_matches = []
        missing_skills = missing_skills or []

    if match_mode == "full_only" and legacy_mode:
        raise ScenarioValidationError(
            [f"{label} lacks full/partial data; rerun matching for full_only mode."]
        )

    if legacy_mode:
        warnings.append(
            f"{label} uses legacy matched_skills only; partials cannot be separated."
        )

    full_set = set(full_matches or [])
    partial_set = set(partial_matches or [])
    missing_set = set(missing_skills or [])

    ordered_full: List[str] = []
    ordered_partial: List[str] = []
    ordered_missing: List[str] = []

    for requirement in requirements:
        if requirement in full_set:
            ordered_full.append(requirement)
        elif requirement in partial_set:
            ordered_partial.append(requirement)
        else:
            ordered_missing.append(requirement)

    total = len(requirements)
    if total == 0:
        score = 50
        coverage = 1.0
    else:
        if match_mode == "partial_ok":
            covered = len(ordered_full) + (len(ordered_partial) * partial_weight)
        else:
            covered = len(ordered_full)
        coverage = covered / total
        score = round(100 * coverage)

    return {
        "score": score,
        "coverage": round(coverage, 3),
        "total": total,
        "full_count": len(ordered_full),
        "partial_count": len(ordered_partial),
        "missing_count": len(ordered_missing),
        "full_matches": ordered_full,
        "partial_matches": ordered_partial,
        "missing_skills": ordered_missing,
        "legacy_mode": legacy_mode
    }


def _must_have_gate_pass(
    must_bucket: Dict[str, Any],
    match_mode: str,
    gate_mode: str,
    coverage_min: float
) -> bool:
    if must_bucket["total"] == 0:
        return True
    if gate_mode == "all":
        if match_mode == "full_only":
            return must_bucket["full_count"] == must_bucket["total"]
        return must_bucket["missing_count"] == 0
    return must_bucket["coverage"] >= coverage_min


def _score_experience(
    match_data: Dict[str, Any],
    job_data: Dict[str, Any],
    scenario: Dict[str, Any]
) -> Tuple[float, float, float]:
    required_years = scenario["scenario"]["min_years_override"]
    if required_years is None:
        requirements = job_data.get("requirements", {}) if isinstance(job_data, dict) else {}
        required_years = requirements.get("minimum_years_experience") or 0

    experience = match_data.get("minimum_years_experience", {})
    candidate_years = experience.get("candidate_years") or 0

    if required_years == 0:
        return 50.0, candidate_years, required_years

    score = min(100.0, round(100.0 * float(candidate_years) / float(required_years)))
    return score, candidate_years, required_years


def _score_education(
    resume_data: Dict[str, Any],
    job_data: Dict[str, Any],
    scenario: Dict[str, Any]
) -> Tuple[float, Dict[str, Any]]:
    requirements = job_data.get("requirements", {}) if isinstance(job_data, dict) else {}
    required_education = requirements.get("required_education") or {}
    override = scenario["scenario"]["education_required_override"]

    if override is False:
        return 50.0, {"reason": "Education requirement disabled."}

    required_flag = bool(required_education.get("required"))
    if override is None and not required_flag:
        return 50.0, {"reason": "No education requirement in base job."}

    required_level = required_education.get("level")
    required_field = required_education.get("field")

    candidate_level_rank, candidate_summary, candidate_area = _extract_candidate_education(
        resume_data
    )
    required_rank = _rank_degree(required_level)

    if required_rank == 0:
        return 50.0, {"reason": "Education level is unclear.", "required": required_level}

    if candidate_level_rank == 0:
        return 0.0, {"reason": "No education found.", "required": required_level}

    field_match = _field_matches(candidate_area, required_field)

    if candidate_level_rank >= required_rank and field_match:
        return 100.0, {
            "reason": "Meets education requirement.",
            "candidate": candidate_summary,
            "required": required_level
        }

    if candidate_level_rank < required_rank:
        return 0.0, {
            "reason": "Education level below requirement.",
            "candidate": candidate_summary,
            "required": required_level
        }

    return 50.0, {
        "reason": "Education field match is unclear.",
        "candidate": candidate_summary,
        "required": required_level
    }


def _score_overall(
    must_score: float,
    nice_score: float,
    experience_score: float,
    education_score: float,
    evaluation: Dict[str, Any]
) -> float:
    weights = _normalize_weights(evaluation, include_nice=evaluation["include_nice_to_have"])
    weighted = (
        must_score * weights["must_have"]
        + nice_score * weights["nice_to_have"]
        + experience_score * weights["experience"]
        + education_score * weights["education"]
    )
    return round(weighted / 100.0, 1)


def _normalize_weights(evaluation: Dict[str, Any], include_nice: bool) -> Dict[str, float]:
    weights = dict(DEFAULT_WEIGHTS)
    override = evaluation.get("weights_override")
    if override:
        weights.update(override)

    if include_nice:
        return weights

    total = weights["must_have"] + weights["experience"] + weights["education"]
    if total == 0:
        return {
            "must_have": 0.0,
            "nice_to_have": 0.0,
            "experience": 0.0,
            "education": 0.0
        }

    return {
        "must_have": weights["must_have"] / total * 100.0,
        "nice_to_have": 0.0,
        "experience": weights["experience"] / total * 100.0,
        "education": weights["education"] / total * 100.0
    }


def _coalesce_score(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return 0.0


def _extract_candidate_education(
    resume_data: Dict[str, Any]
) -> Tuple[int, str, str]:
    education_entries = resume_data.get("education") or []
    best_rank = 0
    best_summary = ""
    best_area = ""

    for entry in education_entries:
        study_type = entry.get("studyType") or ""
        area = entry.get("area") or ""
        rank = _rank_degree(study_type)
        if rank > best_rank:
            best_rank = rank
            best_summary = f"{study_type} in {area}".strip()
            best_area = area

    return best_rank, best_summary, best_area


def _rank_degree(level: Any) -> int:
    if not isinstance(level, str):
        return 0
    text = level.lower()
    if "phd" in text or "doctor" in text:
        return 5
    if "master" in text or "msc" in text or "mba" in text:
        return 4
    if "bachelor" in text or "bsc" in text or "ba" in text or "bs" in text:
        return 3
    if "associate" in text:
        return 2
    if "high school" in text or "secondary" in text:
        return 1
    return 0


def _field_matches(candidate_area: str, required_field: Any) -> bool:
    if not required_field or not isinstance(required_field, str):
        return True
    if "related" in required_field.lower():
        return bool(candidate_area)
    if not candidate_area:
        return False
    candidate_text = candidate_area.lower()
    required_text = required_field.lower()
    tokens = [token.strip() for token in required_text.replace("/", ",").split(",")]
    return any(token and token in candidate_text for token in tokens)
