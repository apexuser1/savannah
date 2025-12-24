"""Models and validation for optimisation payloads."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


RELAX_REMOVE_NICE = "remove_nice_to_have"
RELAX_REMOVE_MUST = "remove_must_have"
RELAX_DEMOTE_MUST = "demote_must_to_nice"
RELAX_LOWER_MIN_YEARS = "lower_min_years"
RELAX_DISABLE_EDUCATION = "disable_education"
RELAX_ALLOW_PARTIALS = "allow_partials"
RELAX_INCREASE_PARTIAL_WEIGHT = "increase_partial_weight"
RELAX_LOWER_COVERAGE_MIN = "lower_coverage_min"
RELAX_LOWER_THRESHOLD = "lower_threshold"
RELAX_WEIGHTS_OVERRIDE = "weights_override"

RELAXATION_TYPES = [
    RELAX_REMOVE_NICE,
    RELAX_REMOVE_MUST,
    RELAX_DEMOTE_MUST,
    RELAX_LOWER_MIN_YEARS,
    RELAX_DISABLE_EDUCATION,
    RELAX_ALLOW_PARTIALS,
    RELAX_INCREASE_PARTIAL_WEIGHT,
    RELAX_LOWER_COVERAGE_MIN,
    RELAX_LOWER_THRESHOLD,
    RELAX_WEIGHTS_OVERRIDE
]

DEFAULT_COSTS = {
    RELAX_REMOVE_NICE: 1.0,
    RELAX_DEMOTE_MUST: 2.0,
    RELAX_REMOVE_MUST: 3.0,
    RELAX_LOWER_MIN_YEARS: 1.0,
    RELAX_DISABLE_EDUCATION: 2.0,
    RELAX_ALLOW_PARTIALS: 1.0,
    RELAX_INCREASE_PARTIAL_WEIGHT: 1.0,
    RELAX_LOWER_COVERAGE_MIN: 1.0,
    RELAX_LOWER_THRESHOLD: 1.0,
    RELAX_WEIGHTS_OVERRIDE: 2.0
}


class OptimisationValidationError(ValueError):
    """Raised when optimisation config is invalid."""

    def __init__(self, errors: List[str]):
        super().__init__("Optimisation validation failed.")
        self.errors = errors


@dataclass
class RangeConstraint:
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None


@dataclass
class OptimisationConstraints:
    max_total_changes: int = 3
    max_skill_changes: Optional[int] = None
    allowed_relaxations: List[str] = field(default_factory=list)
    min_years_override: RangeConstraint = field(
        default_factory=lambda: RangeConstraint(min_value=0, step=1)
    )
    overall_score_threshold: RangeConstraint = field(
        default_factory=lambda: RangeConstraint(min_value=0, step=5)
    )
    partial_match_weight: RangeConstraint = field(
        default_factory=lambda: RangeConstraint(max_value=1.0, step=0.1)
    )
    must_have_coverage_min: RangeConstraint = field(
        default_factory=lambda: RangeConstraint(min_value=0.0, step=0.1)
    )
    weights_override_options: Optional[List[Dict[str, float]]] = None


@dataclass
class OptimisationTarget:
    candidate_count: Optional[int]
    mode: str = "at_least"


@dataclass
class StrategySpec:
    name: str
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimisationConfig:
    target: OptimisationTarget
    strategy: StrategySpec
    constraints: OptimisationConstraints
    costs: Dict[str, float]
    top_k: int = 5


@dataclass
class RelaxationChange:
    kind: str
    detail: Dict[str, Any]
    cost: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.kind,
            "detail": self.detail,
            "cost": self.cost
        }


@dataclass
class OptimisationResult:
    scenario: Dict[str, Any]
    changes: List[RelaxationChange]
    cost: float
    summary: Dict[str, Any]
    candidate_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_count": self.candidate_count,
            "cost": self.cost,
            "changes": [change.to_dict() for change in self.changes],
            "normalized_scenario": self.scenario,
            "summary": self.summary
        }


def load_optimisation_config(payload: Dict[str, Any]) -> OptimisationConfig:
    errors: List[str] = []
    if not isinstance(payload, dict):
        raise OptimisationValidationError(["Optimisation payload must be an object."])

    target_raw = payload.get("target") or {}
    candidate_count = target_raw.get("candidate_count")
    if candidate_count is not None:
        if isinstance(candidate_count, bool) or not isinstance(candidate_count, int):
            errors.append("target.candidate_count must be an integer.")
        elif candidate_count <= 0:
            errors.append("target.candidate_count must be positive.")

    mode = target_raw.get("mode", "at_least")
    if not isinstance(mode, str):
        errors.append("target.mode must be a string.")
        mode = "at_least"
    mode = mode.strip().lower()
    if mode not in ("at_least",):
        errors.append("target.mode must be at_least.")

    strategy_raw = payload.get("strategy")
    if not isinstance(strategy_raw, dict):
        errors.append("strategy must be an object.")
        strategy_raw = {}
    strategy_name = strategy_raw.get("name")
    if not isinstance(strategy_name, str) or not strategy_name.strip():
        errors.append("strategy.name is required.")
        strategy_name = ""
    strategy_options = strategy_raw.get("options", {})
    if strategy_options is None:
        strategy_options = {}
    if not isinstance(strategy_options, dict):
        errors.append("strategy.options must be an object.")
        strategy_options = {}

    constraints = _parse_constraints(payload.get("constraints"), errors)
    costs = _parse_costs(payload.get("costs"), errors)

    top_k = payload.get("top_k", 5)
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        errors.append("top_k must be an integer.")
        top_k = 5
    if isinstance(top_k, int) and top_k <= 0:
        errors.append("top_k must be positive.")
        top_k = 5

    if errors:
        raise OptimisationValidationError(errors)

    return OptimisationConfig(
        target=OptimisationTarget(candidate_count=candidate_count, mode=mode),
        strategy=StrategySpec(name=strategy_name.strip().lower(), options=strategy_options),
        constraints=constraints,
        costs=costs,
        top_k=top_k
    )


def _parse_constraints(
    raw: Any,
    errors: List[str]
) -> OptimisationConstraints:
    constraints = OptimisationConstraints()
    if raw is None:
        constraints.allowed_relaxations = list(RELAXATION_TYPES)
        return constraints
    if not isinstance(raw, dict):
        errors.append("constraints must be an object.")
        constraints.allowed_relaxations = list(RELAXATION_TYPES)
        return constraints

    max_total = raw.get("max_total_changes", constraints.max_total_changes)
    if isinstance(max_total, bool) or not isinstance(max_total, int):
        errors.append("constraints.max_total_changes must be an integer.")
    elif max_total <= 0:
        errors.append("constraints.max_total_changes must be positive.")
    else:
        constraints.max_total_changes = max_total

    max_skill = raw.get("max_skill_changes", None)
    if max_skill is not None:
        if isinstance(max_skill, bool) or not isinstance(max_skill, int):
            errors.append("constraints.max_skill_changes must be an integer.")
        elif max_skill <= 0:
            errors.append("constraints.max_skill_changes must be positive.")
        else:
            constraints.max_skill_changes = max_skill

    allowed = raw.get("allowed_relaxations", None)
    if allowed is None:
        constraints.allowed_relaxations = list(RELAXATION_TYPES)
    elif not isinstance(allowed, list):
        errors.append("constraints.allowed_relaxations must be a list.")
        constraints.allowed_relaxations = list(RELAXATION_TYPES)
    else:
        cleaned = []
        for item in allowed:
            if not isinstance(item, str):
                errors.append("constraints.allowed_relaxations items must be strings.")
                continue
            key = item.strip().lower()
            if key not in RELAXATION_TYPES:
                errors.append(f"Unknown relaxation: {item}.")
                continue
            if key not in cleaned:
                cleaned.append(key)
        constraints.allowed_relaxations = cleaned or list(RELAXATION_TYPES)

    constraints.min_years_override = _parse_range(
        raw.get("min_years_override"),
        "constraints.min_years_override",
        errors,
        default=constraints.min_years_override
    )
    constraints.overall_score_threshold = _parse_range(
        raw.get("overall_score_threshold"),
        "constraints.overall_score_threshold",
        errors,
        default=constraints.overall_score_threshold
    )
    constraints.partial_match_weight = _parse_range(
        raw.get("partial_match_weight"),
        "constraints.partial_match_weight",
        errors,
        default=constraints.partial_match_weight
    )
    constraints.must_have_coverage_min = _parse_range(
        raw.get("must_have_coverage_min"),
        "constraints.must_have_coverage_min",
        errors,
        default=constraints.must_have_coverage_min
    )

    weights_options = raw.get("weights_override_options")
    if weights_options is not None:
        if not isinstance(weights_options, list):
            errors.append("constraints.weights_override_options must be a list.")
        else:
            parsed = []
            for option in weights_options:
                if not isinstance(option, dict):
                    errors.append("constraints.weights_override_options items must be objects.")
                    continue
                parsed.append(option)
            if parsed:
                constraints.weights_override_options = parsed

    return constraints


def _parse_range(
    raw: Any,
    label: str,
    errors: List[str],
    default: RangeConstraint
) -> RangeConstraint:
    if raw is None:
        return default
    if not isinstance(raw, dict):
        errors.append(f"{label} must be an object.")
        return default

    min_value = raw.get("min", default.min_value)
    max_value = raw.get("max", default.max_value)
    step = raw.get("step", default.step)

    if min_value is not None and (isinstance(min_value, bool) or not isinstance(min_value, (int, float))):
        errors.append(f"{label}.min must be a number.")
        min_value = default.min_value
    if max_value is not None and (isinstance(max_value, bool) or not isinstance(max_value, (int, float))):
        errors.append(f"{label}.max must be a number.")
        max_value = default.max_value
    if step is not None and (isinstance(step, bool) or not isinstance(step, (int, float))):
        errors.append(f"{label}.step must be a number.")
        step = default.step

    return RangeConstraint(
        min_value=None if min_value is None else float(min_value),
        max_value=None if max_value is None else float(max_value),
        step=None if step is None else float(step)
    )


def _parse_costs(raw: Any, errors: List[str]) -> Dict[str, float]:
    costs = dict(DEFAULT_COSTS)
    if raw is None:
        return costs
    if not isinstance(raw, dict):
        errors.append("costs must be an object.")
        return costs
    for key, value in raw.items():
        if key not in RELAXATION_TYPES:
            errors.append(f"Unknown cost key: {key}.")
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append(f"costs.{key} must be a number.")
            continue
        costs[key] = float(value)
    return costs
