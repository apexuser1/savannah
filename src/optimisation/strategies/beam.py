"""Beam search optimisation strategy."""
from dataclasses import dataclass
from typing import List

from src.optimisation.models import RelaxationChange, OptimisationResult
from src.optimisation.strategies.base import SearchContext


@dataclass
class _BeamPlan:
    scenario: dict
    changes: List[RelaxationChange]
    cost: float
    result: OptimisationResult


class BeamStrategy:
    def __init__(self, options: dict):
        self.options = options or {}

    def run(self, context: SearchContext) -> List[OptimisationResult]:
        evaluator = context.evaluator
        space = context.space
        config = context.config
        target = context.target_count

        beam_width = int(self.options.get("beam_width", 5))
        if beam_width <= 0:
            beam_width = 5

        baseline_result = evaluator.make_result(
            context.baseline_scenario,
            [],
            0.0
        )
        all_results = [baseline_result]

        beam = [
            _BeamPlan(
                scenario=context.baseline_scenario,
                changes=[],
                cost=0.0,
                result=baseline_result
            )
        ]
        visited = {evaluator.key_for(context.baseline_scenario)}

        for _ in range(config.constraints.max_total_changes):
            candidates: List[_BeamPlan] = []
            for plan in beam:
                actions = space.list_actions(plan.scenario, plan.changes)
                for action in actions:
                    new_scenario = space.apply_action(plan.scenario, action)
                    key = evaluator.key_for(new_scenario)
                    if key in visited:
                        continue
                    visited.add(key)
                    new_changes = plan.changes + [
                        RelaxationChange(
                            kind=action.kind,
                            detail=action.detail,
                            cost=action.cost
                        )
                    ]
                    new_cost = plan.cost + action.cost
                    result = evaluator.make_result(new_scenario, new_changes, new_cost)
                    candidates.append(
                        _BeamPlan(
                            scenario=new_scenario,
                            changes=new_changes,
                            cost=new_cost,
                            result=result
                        )
                    )
                    all_results.append(result)

            if not candidates:
                break

            candidates.sort(key=lambda item: context.ranker(item.result, target))
            beam = candidates[:beam_width]

        return all_results
