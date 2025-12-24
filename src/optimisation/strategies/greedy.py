"""Greedy optimisation strategy."""
from dataclasses import dataclass
from typing import List

from src.optimisation.models import RelaxationChange, OptimisationResult
from src.optimisation.strategies.base import SearchContext


@dataclass
class _Plan:
    scenario: dict
    changes: List[RelaxationChange]
    cost: float


class GreedyStrategy:
    def __init__(self, options: dict):
        self.options = options or {}

    def run(self, context: SearchContext) -> List[OptimisationResult]:
        evaluator = context.evaluator
        space = context.space
        config = context.config
        target = context.target_count

        plan = _Plan(
            scenario=context.baseline_scenario,
            changes=[],
            cost=0.0
        )
        results: List[OptimisationResult] = [
            evaluator.make_result(plan.scenario, plan.changes, plan.cost)
        ]

        max_changes = config.constraints.max_total_changes
        for _ in range(max_changes):
            actions = space.list_actions(plan.scenario, plan.changes)
            if not actions:
                break

            candidates = []
            for action in actions:
                new_scenario = space.apply_action(plan.scenario, action)
                new_changes = plan.changes + [
                    RelaxationChange(
                        kind=action.kind,
                        detail=action.detail,
                        cost=action.cost
                    )
                ]
                new_cost = plan.cost + action.cost
                result = evaluator.make_result(new_scenario, new_changes, new_cost)
                candidates.append((result, new_scenario, new_changes, new_cost))

            candidates.sort(key=lambda item: context.ranker(item[0], target))
            best_result, best_scenario, best_changes, best_cost = candidates[0]

            plan = _Plan(best_scenario, best_changes, best_cost)
            results.append(best_result)

            if best_result.candidate_count >= target:
                break

        return results
