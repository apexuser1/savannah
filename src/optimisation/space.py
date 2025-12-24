"""Relaxation search space and action application."""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import copy

from src.what_if.scenario import apply_skill_edits
from src.optimisation.models import (
    RELAX_ALLOW_PARTIALS,
    RELAX_DEMOTE_MUST,
    RELAX_DISABLE_EDUCATION,
    RELAX_INCREASE_PARTIAL_WEIGHT,
    RELAX_LOWER_COVERAGE_MIN,
    RELAX_LOWER_MIN_YEARS,
    RELAX_LOWER_THRESHOLD,
    RELAX_REMOVE_MUST,
    RELAX_REMOVE_NICE,
    RELAX_WEIGHTS_OVERRIDE,
    OptimisationConfig,
    RelaxationChange
)


@dataclass
class RelaxationAction:
    kind: str
    detail: Dict[str, Any]
    cost: float
    priority: int


class RelaxationSpace:
    """Generates relaxation actions from the current scenario."""

    def __init__(self, job_data: Dict[str, Any], config: OptimisationConfig):
        self.job_data = job_data
        self.config = config

    def list_actions(
        self,
        scenario: Dict[str, Any],
        changes: List[RelaxationChange]
    ) -> List[RelaxationAction]:
        actions: List[RelaxationAction] = []
        allowed = set(self.config.constraints.allowed_relaxations)
        change_counts = _count_skill_changes(changes)

        if RELAX_REMOVE_NICE in allowed:
            actions.extend(self._remove_nice_actions(scenario, change_counts))
        if RELAX_DEMOTE_MUST in allowed:
            actions.extend(self._demote_must_actions(scenario, change_counts))
        if RELAX_REMOVE_MUST in allowed:
            actions.extend(self._remove_must_actions(scenario, change_counts))
        if RELAX_LOWER_MIN_YEARS in allowed:
            actions.extend(self._lower_min_years_actions(scenario))
        if RELAX_DISABLE_EDUCATION in allowed:
            action = self._disable_education_action(scenario)
            if action:
                actions.append(action)
        if RELAX_ALLOW_PARTIALS in allowed:
            action = self._allow_partials_action(scenario)
            if action:
                actions.append(action)
        if RELAX_INCREASE_PARTIAL_WEIGHT in allowed:
            action = self._increase_partial_weight_action(scenario)
            if action:
                actions.append(action)
        if RELAX_LOWER_COVERAGE_MIN in allowed:
            action = self._lower_coverage_min_action(scenario)
            if action:
                actions.append(action)
        if RELAX_LOWER_THRESHOLD in allowed:
            action = self._lower_threshold_action(scenario)
            if action:
                actions.append(action)
        if RELAX_WEIGHTS_OVERRIDE in allowed:
            actions.extend(self._weights_override_actions(scenario))

        actions.sort(key=lambda item: (item.priority, item.cost, item.kind))
        return actions

    def apply_action(
        self,
        scenario: Dict[str, Any],
        action: RelaxationAction
    ) -> Dict[str, Any]:
        updated = copy.deepcopy(scenario)

        if action.kind == RELAX_REMOVE_NICE:
            skill = action.detail["skill"]
            _add_unique(updated["scenario"]["skills_remove"]["nice_to_have"], skill)
            _remove_item(updated["scenario"]["skills_add"]["nice_to_have"], skill)
        elif action.kind == RELAX_REMOVE_MUST:
            skill = action.detail["skill"]
            _add_unique(updated["scenario"]["skills_remove"]["must_have"], skill)
            _add_unique(updated["scenario"]["skills_remove"]["nice_to_have"], skill)
            _remove_item(updated["scenario"]["skills_add"]["must_have"], skill)
            _remove_item(updated["scenario"]["skills_add"]["nice_to_have"], skill)
        elif action.kind == RELAX_DEMOTE_MUST:
            skill = action.detail["skill"]
            _add_unique(updated["scenario"]["skills_remove"]["must_have"], skill)
            _add_unique(updated["scenario"]["skills_add"]["nice_to_have"], skill)
        elif action.kind == RELAX_LOWER_MIN_YEARS:
            updated["scenario"]["min_years_override"] = int(action.detail["to"])
        elif action.kind == RELAX_DISABLE_EDUCATION:
            updated["scenario"]["education_required_override"] = False
        elif action.kind == RELAX_ALLOW_PARTIALS:
            updated["evaluation"]["match_mode"] = "partial_ok"
        elif action.kind == RELAX_INCREASE_PARTIAL_WEIGHT:
            updated["evaluation"]["partial_match_weight"] = float(action.detail["to"])
        elif action.kind == RELAX_LOWER_COVERAGE_MIN:
            updated["evaluation"]["must_have_coverage_min"] = float(action.detail["to"])
        elif action.kind == RELAX_LOWER_THRESHOLD:
            updated["optimization"]["overall_score_threshold"] = float(action.detail["to"])
        elif action.kind == RELAX_WEIGHTS_OVERRIDE:
            updated["evaluation"]["weights_override"] = action.detail["weights"]

        _canonicalize_skill_lists(updated)
        return updated

    def _remove_nice_actions(
        self,
        scenario: Dict[str, Any],
        change_counts: Dict[str, int]
    ) -> List[RelaxationAction]:
        if self._max_skill_changes_reached(change_counts):
            return []
        effective = apply_skill_edits(self.job_data, scenario)
        actions = []
        for skill in effective["nice_to_have"]:
            actions.append(
                RelaxationAction(
                    kind=RELAX_REMOVE_NICE,
                    detail={"skill": skill},
                    cost=self._cost(RELAX_REMOVE_NICE),
                    priority=1
                )
            )
        return actions

    def _remove_must_actions(
        self,
        scenario: Dict[str, Any],
        change_counts: Dict[str, int]
    ) -> List[RelaxationAction]:
        if self._max_skill_changes_reached(change_counts):
            return []
        effective = apply_skill_edits(self.job_data, scenario)
        actions = []
        for skill in effective["must_have"]:
            actions.append(
                RelaxationAction(
                    kind=RELAX_REMOVE_MUST,
                    detail={"skill": skill},
                    cost=self._cost(RELAX_REMOVE_MUST),
                    priority=3
                )
            )
        return actions

    def _demote_must_actions(
        self,
        scenario: Dict[str, Any],
        change_counts: Dict[str, int]
    ) -> List[RelaxationAction]:
        if self._max_skill_changes_reached(change_counts):
            return []
        effective = apply_skill_edits(self.job_data, scenario)
        actions = []
        for skill in effective["must_have"]:
            actions.append(
                RelaxationAction(
                    kind=RELAX_DEMOTE_MUST,
                    detail={"skill": skill},
                    cost=self._cost(RELAX_DEMOTE_MUST),
                    priority=2
                )
            )
        return actions

    def _lower_min_years_actions(self, scenario: Dict[str, Any]) -> List[RelaxationAction]:
        constraint = self.config.constraints.min_years_override
        if constraint.step is None:
            return []
        current = scenario["scenario"]["min_years_override"]
        if current is None:
            requirements = self.job_data.get("requirements", {}) if isinstance(self.job_data, dict) else {}
            current = requirements.get("minimum_years_experience") or 0
        min_value = constraint.min_value if constraint.min_value is not None else 0
        next_value = current - constraint.step
        if next_value < min_value:
            return []
        return [
            RelaxationAction(
                kind=RELAX_LOWER_MIN_YEARS,
                detail={"from": current, "to": int(next_value)},
                cost=self._cost(RELAX_LOWER_MIN_YEARS),
                priority=4
            )
        ]

    def _disable_education_action(self, scenario: Dict[str, Any]) -> Optional[RelaxationAction]:
        override = scenario["scenario"].get("education_required_override")
        if override is False:
            return None
        requirements = self.job_data.get("requirements", {}) if isinstance(self.job_data, dict) else {}
        required_education = requirements.get("required_education") or {}
        if override is None and not required_education.get("required"):
            return None
        return RelaxationAction(
            kind=RELAX_DISABLE_EDUCATION,
            detail={},
            cost=self._cost(RELAX_DISABLE_EDUCATION),
            priority=4
        )

    def _allow_partials_action(self, scenario: Dict[str, Any]) -> Optional[RelaxationAction]:
        if scenario["evaluation"]["match_mode"] == "partial_ok":
            return None
        return RelaxationAction(
            kind=RELAX_ALLOW_PARTIALS,
            detail={},
            cost=self._cost(RELAX_ALLOW_PARTIALS),
            priority=4
        )

    def _increase_partial_weight_action(
        self,
        scenario: Dict[str, Any]
    ) -> Optional[RelaxationAction]:
        if scenario["evaluation"]["match_mode"] != "partial_ok":
            return None
        constraint = self.config.constraints.partial_match_weight
        if constraint.step is None or constraint.max_value is None:
            return None
        current = scenario["evaluation"]["partial_match_weight"] or 0.0
        next_value = min(current + constraint.step, constraint.max_value)
        if next_value <= current:
            return None
        return RelaxationAction(
            kind=RELAX_INCREASE_PARTIAL_WEIGHT,
            detail={"from": current, "to": next_value},
            cost=self._cost(RELAX_INCREASE_PARTIAL_WEIGHT),
            priority=4
        )

    def _lower_coverage_min_action(
        self,
        scenario: Dict[str, Any]
    ) -> Optional[RelaxationAction]:
        constraint = self.config.constraints.must_have_coverage_min
        if constraint.step is None:
            return None
        current = scenario["evaluation"]["must_have_coverage_min"] or 0.0
        min_value = constraint.min_value if constraint.min_value is not None else 0.0
        next_value = current - constraint.step
        if next_value < min_value:
            return None
        return RelaxationAction(
            kind=RELAX_LOWER_COVERAGE_MIN,
            detail={"from": current, "to": next_value},
            cost=self._cost(RELAX_LOWER_COVERAGE_MIN),
            priority=4
        )

    def _lower_threshold_action(
        self,
        scenario: Dict[str, Any]
    ) -> Optional[RelaxationAction]:
        constraint = self.config.constraints.overall_score_threshold
        if constraint.step is None:
            return None
        current = scenario["optimization"]["overall_score_threshold"] or 0.0
        min_value = constraint.min_value if constraint.min_value is not None else 0.0
        next_value = current - constraint.step
        if next_value < min_value:
            return None
        return RelaxationAction(
            kind=RELAX_LOWER_THRESHOLD,
            detail={"from": current, "to": next_value},
            cost=self._cost(RELAX_LOWER_THRESHOLD),
            priority=4
        )

    def _weights_override_actions(
        self,
        scenario: Dict[str, Any]
    ) -> List[RelaxationAction]:
        options = self.config.constraints.weights_override_options or []
        current = scenario["evaluation"].get("weights_override")
        actions = []
        for option in options:
            if option == current:
                continue
            actions.append(
                RelaxationAction(
                    kind=RELAX_WEIGHTS_OVERRIDE,
                    detail={"weights": option},
                    cost=self._cost(RELAX_WEIGHTS_OVERRIDE),
                    priority=5
                )
            )
        return actions

    def _max_skill_changes_reached(self, change_counts: Dict[str, int]) -> bool:
        max_skill = self.config.constraints.max_skill_changes
        if max_skill is None:
            return False
        return change_counts.get("skills", 0) >= max_skill

    def _cost(self, kind: str) -> float:
        return float(self.config.costs.get(kind, 1.0))


def _count_skill_changes(changes: List[RelaxationChange]) -> Dict[str, int]:
    count = 0
    for change in changes:
        if change.kind in (RELAX_REMOVE_NICE, RELAX_REMOVE_MUST, RELAX_DEMOTE_MUST):
            count += 1
    return {"skills": count}


def _add_unique(items: List[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _remove_item(items: List[str], value: str) -> None:
    if value in items:
        items.remove(value)


def _canonicalize_skill_lists(scenario: Dict[str, Any]) -> None:
    list_paths = (
        ("scenario", "skills_add", "must_have"),
        ("scenario", "skills_add", "nice_to_have"),
        ("scenario", "skills_remove", "must_have"),
        ("scenario", "skills_remove", "nice_to_have")
    )
    for path in list_paths:
        list_ref = _get_list_ref(scenario, path)
        updated = sorted(set(list_ref))
        list_ref.clear()
        list_ref.extend(updated)


def _get_list_ref(root: Dict[str, Any], path: tuple) -> List[str]:
    current: Any = root
    for key in path:
        current = current[key]
    if not isinstance(current, list):
        return []
    return current
