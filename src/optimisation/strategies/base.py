"""Strategy base interface."""
from typing import Callable, List, Protocol

from src.optimisation.models import OptimisationConfig, OptimisationResult


class OptimisationStrategy(Protocol):
    def run(self, context: "SearchContext") -> List[OptimisationResult]:
        """Return candidate optimisation results."""
        raise NotImplementedError


class SearchContext:
    def __init__(
        self,
        space,
        evaluator,
        config: OptimisationConfig,
        target_count: int,
        ranker: Callable[[OptimisationResult, int], tuple],
        baseline_scenario: dict
    ):
        self.space = space
        self.evaluator = evaluator
        self.config = config
        self.target_count = target_count
        self.ranker = ranker
        self.baseline_scenario = baseline_scenario
