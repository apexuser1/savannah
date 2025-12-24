"""Monte Carlo optimisation strategy."""
import random
from dataclasses import dataclass
from typing import List

from src.optimisation.models import RelaxationChange, OptimisationResult
from src.optimisation.strategies.base import SearchContext


@dataclass
class _RunPlan:
    scenario: dict
    changes: List[RelaxationChange]
    cost: float


class MonteCarloStrategy:
    def __init__(self, options: dict):
        self.options = options or {}

    def run(self, context: SearchContext) -> List[OptimisationResult]:
        evaluator = context.evaluator
        space = context.space
        config = context.config

        max_runs = int(self.options.get("max_runs", 200))
        if max_runs <= 0:
            max_runs = 200
        seed = self.options.get("seed")
        rng = random.Random(seed)

        results: List[OptimisationResult] = []
        baseline_result = evaluator.make_result(
            context.baseline_scenario,
            [],
            0.0
        )
        results.append(baseline_result)

        visited = {evaluator.key_for(context.baseline_scenario)}

        for _ in range(max_runs):
            plan = _RunPlan(
                scenario=context.baseline_scenario,
                changes=[],
                cost=0.0
            )
            steps = rng.randint(1, config.constraints.max_total_changes)

            for _ in range(steps):
                actions = space.list_actions(plan.scenario, plan.changes)
                if not actions:
                    break
                action = _weighted_pick(actions, rng)
                plan = _RunPlan(
                    scenario=space.apply_action(plan.scenario, action),
                    changes=plan.changes
                    + [RelaxationChange(kind=action.kind, detail=action.detail, cost=action.cost)],
                    cost=plan.cost + action.cost
                )

            key = evaluator.key_for(plan.scenario)
            if key in visited:
                continue
            visited.add(key)

            result = evaluator.make_result(plan.scenario, plan.changes, plan.cost)
            results.append(result)

        return results


def _weighted_pick(actions, rng: random.Random):
    weights = []
    for action in actions:
        weight = 1.0 / (1.0 + float(action.priority))
        weights.append(weight)
    return rng.choices(actions, weights=weights, k=1)[0]
