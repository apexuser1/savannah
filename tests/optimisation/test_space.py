from src.optimisation.space import RelaxationSpace
from src.optimisation.models import (
    RELAX_DEMOTE_MUST,
    RELAX_REMOVE_MUST,
    RELAX_REMOVE_NICE,
    load_optimisation_config
)
from src.what_if.scenario import normalize_scenario, DEFAULT_SCENARIO

from tests.conftest import make_job_data


def test_actions_prefer_nice_to_have_first():
    job_data = make_job_data()
    config = load_optimisation_config(
        {
            "target": {"candidate_count": 1},
            "strategy": {"name": "beam"},
            "constraints": {
                "allowed_relaxations": [
                    RELAX_REMOVE_NICE,
                    RELAX_DEMOTE_MUST,
                    RELAX_REMOVE_MUST
                ]
            }
        }
    )
    scenario, _ = normalize_scenario(DEFAULT_SCENARIO, job_data)
    space = RelaxationSpace(job_data, config)

    actions = space.list_actions(scenario, [])
    kinds = [action.kind for action in actions]

    first_must = kinds.index(RELAX_DEMOTE_MUST) if RELAX_DEMOTE_MUST in kinds else len(kinds)
    first_remove_must = kinds.index(RELAX_REMOVE_MUST) if RELAX_REMOVE_MUST in kinds else len(kinds)
    last_nice = max(i for i, kind in enumerate(kinds) if kind == RELAX_REMOVE_NICE)

    assert last_nice < first_must
    assert last_nice < first_remove_must
