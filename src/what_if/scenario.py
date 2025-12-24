"""Scenario parsing, normalization, and shock reporting for what-if analysis."""
import json
from typing import Any, Dict, List, Tuple

from src.config import Config
from src.matching.matcher import LLMClient


SCENARIO_PARSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "scenario": {
            "type": "object",
            "properties": {
                "min_years_override": {"type": ["number", "null"]},
                "education_required_override": {"type": ["boolean", "null"]},
                "skills_add": {
                    "type": "object",
                    "properties": {
                        "must_have": {"type": "array", "items": {"type": "string"}},
                        "nice_to_have": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["must_have", "nice_to_have"]
                },
                "skills_remove": {
                    "type": "object",
                    "properties": {
                        "must_have": {"type": "array", "items": {"type": "string"}},
                        "nice_to_have": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["must_have", "nice_to_have"]
                }
            },
            "required": [
                "min_years_override",
                "education_required_override",
                "skills_add",
                "skills_remove"
            ]
        },
        "evaluation": {
            "type": "object",
            "properties": {
                "match_mode": {"type": "string", "enum": ["full_only", "partial_ok"]},
                "partial_match_weight": {"type": ["number", "null"]},
                "must_have_gate_mode": {"type": "string", "enum": ["all", "coverage_min"]},
                "must_have_coverage_min": {"type": ["number", "null"]},
                "include_nice_to_have": {"type": ["boolean", "null"]},
                "weights_override": {
                    "type": ["object", "null"],
                    "properties": {
                        "must_have": {"type": "number"},
                        "nice_to_have": {"type": "number"},
                        "experience": {"type": "number"},
                        "education": {"type": "number"}
                    },
                    "required": ["must_have", "nice_to_have", "experience", "education"]
                }
            },
            "required": [
                "match_mode",
                "partial_match_weight",
                "must_have_gate_mode",
                "must_have_coverage_min",
                "include_nice_to_have",
                "weights_override"
            ]
        },
        "optimization": {
            "type": "object",
            "properties": {
                "objective": {
                    "type": "string",
                    "enum": ["maximize_candidate_count"]
                },
                "overall_score_threshold": {"type": ["number", "null"]}
            },
            "required": ["objective", "overall_score_threshold"]
        }
    },
    "required": ["scenario", "evaluation", "optimization"]
}


DEFAULT_SCENARIO = {
    "scenario": {
        "min_years_override": None,
        "education_required_override": None,
        "skills_add": {"must_have": [], "nice_to_have": []},
        "skills_remove": {"must_have": [], "nice_to_have": []}
    },
    "evaluation": {
        "match_mode": "partial_ok",
        "partial_match_weight": 0.5,
        "must_have_gate_mode": "coverage_min",
        "must_have_coverage_min": 1.0,
        "include_nice_to_have": True,
        "weights_override": None
    },
    "optimization": {
        "objective": "maximize_candidate_count",
        "overall_score_threshold": 50
    }
}


class ScenarioValidationError(ValueError):
    """Raised when a scenario is invalid."""

    def __init__(self, errors: List[str]):
        super().__init__("Scenario validation failed.")
        self.errors = errors


def parse_scenario_text(scenario_text: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a free-text scenario into structured directives using the LLM."""
    requirements = job_data.get("requirements", {}) if isinstance(job_data, dict) else {}
    must_have = requirements.get("must_have_skills") or []
    nice_to_have = requirements.get("nice_to_have_skills") or []

    prompt = f"""You are a strict scenario parser for a recruiter what-if tool.

Return ONLY valid JSON that matches the provided schema. Do not add extra keys.

Allowed directives:
- min_years_override: number or null
- education_required_override: boolean or null
- skills_add.must_have / skills_add.nice_to_have: list of skills from the allowed lists
- skills_remove.must_have / skills_remove.nice_to_have: list of skills from the allowed lists
- match_mode: "full_only" or "partial_ok"
- partial_match_weight: number or null
- must_have_gate_mode: "all" or "coverage_min"
- must_have_coverage_min: number or null
- include_nice_to_have: boolean or null
- weights_override: object with must_have, nice_to_have, experience, education (or null)
- objective: "maximize_candidate_count"
- overall_score_threshold: number or null

If a directive is not mentioned, set it to null (or empty lists for skills).
Use ONLY these skills when adding/removing:
must_have_skills: {json.dumps(must_have, indent=2)}
nice_to_have_skills: {json.dumps(nice_to_have, indent=2)}

Scenario text:
{scenario_text}
"""

    llm_client = LLMClient(model=Config.DEFAULT_MODEL)
    return llm_client.call_llm(
        prompt,
        temperature=0.0,
        max_tokens=1500,
        context="what-if scenario parsing",
        schema=SCENARIO_PARSE_SCHEMA,
        function_name="parse_what_if_scenario"
    )


def normalize_scenario(
    raw: Dict[str, Any],
    job_data: Dict[str, Any],
    strict: bool = True
) -> Tuple[Dict[str, Any], List[str]]:
    """Normalize and validate a scenario payload."""
    errors: List[str] = []
    warnings: List[str] = []
    normalized = json.loads(json.dumps(DEFAULT_SCENARIO))

    if not isinstance(raw, dict):
        raise ScenarioValidationError(["Scenario payload must be an object."])

    scenario_raw = _ensure_dict(raw.get("scenario"), "scenario", errors)
    evaluation_raw = _ensure_dict(raw.get("evaluation"), "evaluation", errors)
    optimization_raw = _ensure_dict(raw.get("optimization"), "optimization", errors)

    skill_catalog = _build_skill_catalog(job_data)

    normalized["scenario"]["min_years_override"] = _coerce_int(
        scenario_raw.get("min_years_override"),
        "min_years_override",
        errors,
        min_value=0,
        max_value=40
    )
    normalized["scenario"]["education_required_override"] = _coerce_bool(
        scenario_raw.get("education_required_override"),
        "education_required_override",
        errors
    )

    add_block = _normalize_skill_block(
        scenario_raw.get("skills_add"),
        "skills_add",
        skill_catalog,
        errors
    )
    remove_block = _normalize_skill_block(
        scenario_raw.get("skills_remove"),
        "skills_remove",
        skill_catalog,
        errors
    )
    normalized["scenario"]["skills_add"] = add_block
    normalized["scenario"]["skills_remove"] = remove_block

    match_mode = _coerce_enum(
        evaluation_raw.get("match_mode"),
        "match_mode",
        ["full_only", "partial_ok", "full", "partial"],
        errors
    )
    if match_mode in ("full", "partial"):
        match_mode = "full_only" if match_mode == "full" else "partial_ok"
    normalized["evaluation"]["match_mode"] = match_mode or normalized["evaluation"]["match_mode"]

    partial_weight = _coerce_float(
        evaluation_raw.get("partial_match_weight"),
        "partial_match_weight",
        errors,
        min_value=0.0,
        max_value=1.0
    )
    if partial_weight is not None:
        normalized["evaluation"]["partial_match_weight"] = partial_weight

    gate_mode = _coerce_enum(
        evaluation_raw.get("must_have_gate_mode"),
        "must_have_gate_mode",
        ["all", "coverage_min"],
        errors
    )
    if gate_mode:
        normalized["evaluation"]["must_have_gate_mode"] = gate_mode

    coverage_min = _coerce_float(
        evaluation_raw.get("must_have_coverage_min"),
        "must_have_coverage_min",
        errors,
        min_value=0.0,
        max_value=1.0
    )
    if coverage_min is not None:
        normalized["evaluation"]["must_have_coverage_min"] = coverage_min

    include_nice = _coerce_bool(
        evaluation_raw.get("include_nice_to_have"),
        "include_nice_to_have",
        errors
    )
    if include_nice is not None:
        normalized["evaluation"]["include_nice_to_have"] = include_nice

    weights_override = _normalize_weights(
        evaluation_raw.get("weights_override"),
        "weights_override",
        errors
    )
    if weights_override is not None:
        normalized["evaluation"]["weights_override"] = weights_override

    objective = _coerce_enum(
        optimization_raw.get("objective"),
        "objective",
        ["maximize_candidate_count"],
        errors
    )
    if objective:
        normalized["optimization"]["objective"] = objective

    threshold = _coerce_float(
        optimization_raw.get("overall_score_threshold"),
        "overall_score_threshold",
        errors,
        min_value=0.0,
        max_value=100.0
    )
    if threshold is not None:
        normalized["optimization"]["overall_score_threshold"] = threshold

    if normalized["evaluation"]["match_mode"] == "full_only" and partial_weight is not None:
        warnings.append(
            "partial_match_weight is ignored because match_mode is full_only."
        )

    if normalized["evaluation"]["must_have_gate_mode"] == "all" and coverage_min is not None:
        warnings.append(
            "must_have_coverage_min is ignored because must_have_gate_mode is all."
        )

    _warn_on_skill_moves(
        add_block,
        remove_block,
        job_data,
        warnings
    )

    if errors and strict:
        raise ScenarioValidationError(errors)

    return normalized, warnings


def build_shock_report(
    job_data: Dict[str, Any],
    scenario: Dict[str, Any]
) -> Dict[str, Any]:
    """Summarize how the scenario changes the base job requirements."""
    requirements = job_data.get("requirements", {}) if isinstance(job_data, dict) else {}
    base_must = requirements.get("must_have_skills") or []
    base_nice = requirements.get("nice_to_have_skills") or []
    base_min_years = requirements.get("minimum_years_experience") or 0
    base_education_required = False
    required_education = requirements.get("required_education")
    if isinstance(required_education, dict):
        base_education_required = bool(required_education.get("required"))

    effective = apply_skill_edits(job_data, scenario)
    effective_min_years = scenario["scenario"]["min_years_override"]
    if effective_min_years is None:
        effective_min_years = base_min_years

    education_override = scenario["scenario"]["education_required_override"]
    effective_education_required = (
        base_education_required if education_override is None else bool(education_override)
    )

    return {
        "min_years": {
            "from": base_min_years,
            "to": effective_min_years,
            "delta": effective_min_years - base_min_years
        },
        "education_required": {
            "from": base_education_required,
            "to": effective_education_required
        },
        "must_have_added": [s for s in effective["must_have"] if s not in base_must],
        "must_have_removed": [s for s in base_must if s not in effective["must_have"]],
        "nice_to_have_added": [s for s in effective["nice_to_have"] if s not in base_nice],
        "nice_to_have_removed": [s for s in base_nice if s not in effective["nice_to_have"]]
    }


def apply_skill_edits(
    job_data: Dict[str, Any],
    scenario: Dict[str, Any]
) -> Dict[str, List[str]]:
    """Apply add/remove edits to job requirements."""
    requirements = job_data.get("requirements", {}) if isinstance(job_data, dict) else {}
    base_must = list(requirements.get("must_have_skills") or [])
    base_nice = list(requirements.get("nice_to_have_skills") or [])

    add = scenario["scenario"]["skills_add"]
    remove = scenario["scenario"]["skills_remove"]

    remove_set = set(remove.get("must_have", [])) | set(remove.get("nice_to_have", []))
    must = [skill for skill in base_must if skill not in remove_set]
    nice = [skill for skill in base_nice if skill not in remove_set]

    for skill in add.get("must_have", []):
        if skill not in must:
            must.append(skill)
        if skill in nice:
            nice.remove(skill)

    for skill in add.get("nice_to_have", []):
        if skill not in nice and skill not in must:
            nice.append(skill)

    return {"must_have": must, "nice_to_have": nice}


def _ensure_dict(value: Any, label: str, errors: List[str]) -> Dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object.")
        return {}
    return value


def _coerce_int(
    value: Any,
    label: str,
    errors: List[str],
    min_value: int,
    max_value: int
) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        errors.append(f"{label} must be a number.")
        return None
    if isinstance(value, float):
        if value.is_integer():
            value = int(value)
        else:
            errors.append(f"{label} must be an integer.")
            return None
    if not isinstance(value, int):
        errors.append(f"{label} must be an integer.")
        return None
    if value < min_value or value > max_value:
        errors.append(f"{label} must be between {min_value} and {max_value}.")
        return None
    return value


def _coerce_float(
    value: Any,
    label: str,
    errors: List[str],
    min_value: float,
    max_value: float
) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        errors.append(f"{label} must be a number.")
        return None
    if not isinstance(value, (int, float)):
        errors.append(f"{label} must be a number.")
        return None
    value = float(value)
    if value < min_value or value > max_value:
        errors.append(f"{label} must be between {min_value} and {max_value}.")
        return None
    return value


def _coerce_bool(value: Any, label: str, errors: List[str]) -> Any:
    if value is None:
        return None
    if not isinstance(value, bool):
        errors.append(f"{label} must be a boolean.")
        return None
    return value


def _coerce_enum(
    value: Any,
    label: str,
    allowed: List[str],
    errors: List[str]
) -> Any:
    if value is None:
        return None
    if not isinstance(value, str):
        errors.append(f"{label} must be a string.")
        return None
    value_lower = value.strip().lower()
    if value_lower not in allowed:
        errors.append(f"{label} must be one of: {', '.join(allowed)}.")
        return None
    return value_lower


def _normalize_skill_block(
    value: Any,
    label: str,
    skill_catalog: Dict[str, str],
    errors: List[str]
) -> Dict[str, List[str]]:
    block = {"must_have": [], "nice_to_have": []}
    if value is None:
        return block
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object.")
        return block

    for key in ("must_have", "nice_to_have"):
        raw_list = value.get(key, [])
        if raw_list is None:
            raw_list = []
        if not isinstance(raw_list, list):
            errors.append(f"{label}.{key} must be a list.")
            continue
        for item in raw_list:
            if not isinstance(item, str):
                errors.append(f"{label}.{key} items must be strings.")
                continue
            canonical = _canonicalize_skill(item, skill_catalog)
            if canonical is None:
                errors.append(
                    f"{label}.{key} contains unknown skill: {item}."
                )
                continue
            if canonical not in block[key]:
                block[key].append(canonical)
    return block


def _normalize_weights(
    value: Any,
    label: str,
    errors: List[str]
) -> Any:
    if value is None:
        return None
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object or null.")
        return None

    weights = {}
    total = 0.0
    for key in ("must_have", "nice_to_have", "experience", "education"):
        if key not in value:
            errors.append(f"{label} must include {key}.")
            continue
        raw = value.get(key)
        if not isinstance(raw, (int, float)) or isinstance(raw, bool):
            errors.append(f"{label}.{key} must be a number.")
            continue
        weights[key] = float(raw)
        total += weights[key]

    if weights and abs(total - 100.0) > 0.01:
        errors.append(f"{label} weights must sum to 100.")
    return weights if weights else None


def _build_skill_catalog(job_data: Dict[str, Any]) -> Dict[str, str]:
    requirements = job_data.get("requirements", {}) if isinstance(job_data, dict) else {}
    catalog: Dict[str, str] = {}
    for skill in (requirements.get("must_have_skills") or []):
        key = _normalize_skill_key(skill)
        if key:
            catalog[key] = skill
    for skill in (requirements.get("nice_to_have_skills") or []):
        key = _normalize_skill_key(skill)
        if key:
            catalog[key] = skill
    return catalog


def _normalize_skill_key(skill: str) -> str:
    return " ".join(skill.strip().lower().split())


def _canonicalize_skill(skill: str, catalog: Dict[str, str]) -> Any:
    key = _normalize_skill_key(skill)
    return catalog.get(key)


def _warn_on_skill_moves(
    add_block: Dict[str, List[str]],
    remove_block: Dict[str, List[str]],
    job_data: Dict[str, Any],
    warnings: List[str]
) -> None:
    requirements = job_data.get("requirements", {}) if isinstance(job_data, dict) else {}
    base_must = set(requirements.get("must_have_skills") or [])
    base_nice = set(requirements.get("nice_to_have_skills") or [])

    for skill in add_block.get("must_have", []):
        if skill in base_nice and skill not in base_must:
            warnings.append(f"Skill moved from nice_to_have to must_have: {skill}")

    for skill in add_block.get("nice_to_have", []):
        if skill in base_must and skill not in base_nice:
            warnings.append(f"Skill moved from must_have to nice_to_have: {skill}")

    for skill in remove_block.get("must_have", []) + remove_block.get("nice_to_have", []):
        if skill in base_must or skill in base_nice:
            warnings.append(f"Skill removed from requirements: {skill}")

