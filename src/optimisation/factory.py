"""Factory for optimisation strategies."""
from typing import Dict, Type

from src.optimisation.models import OptimisationValidationError, StrategySpec
from src.optimisation.strategies.beam import BeamStrategy
from src.optimisation.strategies.greedy import GreedyStrategy
from src.optimisation.strategies.monte_carlo import MonteCarloStrategy


class StrategyFactory:
    _registry: Dict[str, Type] = {
        "beam": BeamStrategy,
        "greedy": GreedyStrategy,
        "monte_carlo": MonteCarloStrategy
    }

    @classmethod
    def create(cls, spec: StrategySpec):
        name = spec.name.strip().lower()
        if name not in cls._registry:
            raise OptimisationValidationError([f"Unknown strategy: {name}."])
        strategy_class = cls._registry[name]
        return strategy_class(spec.options)
