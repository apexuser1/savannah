import pytest

from src.optimisation.factory import StrategyFactory
from src.optimisation.models import StrategySpec, OptimisationValidationError, load_optimisation_config


def test_factory_creates_strategy():
    payload = {
        "target": {"candidate_count": 1},
        "strategy": {"name": "beam"}
    }
    config = load_optimisation_config(payload)
    strategy = StrategyFactory.create(config.strategy)
    assert strategy.__class__.__name__ == "BeamStrategy"


def test_factory_rejects_unknown_strategy():
    with pytest.raises(OptimisationValidationError):
        StrategyFactory.create(StrategySpec(name="unknown"))
