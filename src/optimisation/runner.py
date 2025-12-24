"""Orchestration for optimisation runs."""
from typing import Any, Dict, List, Optional, cast
import json

from sqlalchemy.orm import Session

from src.database.models import Job, Application, Candidate
from src.what_if.evaluator import evaluate_applications
from src.what_if.scenario import (
    DEFAULT_SCENARIO,
    build_shock_report,
    normalize_scenario
)
from src.optimisation.factory import StrategyFactory
from src.optimisation.models import (
    OptimisationConfig,
    OptimisationResult,
    OptimisationValidationError,
    load_optimisation_config
)
from src.optimisation.space import RelaxationSpace
from src.optimisation.strategies.base import SearchContext


class ScenarioEvaluator:
    def __init__(self, job_data: Dict[str, Any], applications: List[Any]):
        self.job_data = job_data
        self.applications = applications
        self._cache: Dict[Any, Dict[str, Any]] = {}

    def key_for(self, scenario: Dict[str, Any]) -> Any:
        scenario_block = scenario["scenario"]
        evaluation = scenario["evaluation"]
        optimization = scenario["optimization"]

        weights = evaluation.get("weights_override") or {}
        weights_key = tuple(sorted(weights.items()))

        return (
            scenario_block.get("min_years_override"),
            scenario_block.get("education_required_override"),
            tuple(sorted(scenario_block["skills_add"]["must_have"])),
            tuple(sorted(scenario_block["skills_add"]["nice_to_have"])),
            tuple(sorted(scenario_block["skills_remove"]["must_have"])),
            tuple(sorted(scenario_block["skills_remove"]["nice_to_have"])),
            evaluation.get("match_mode"),
            evaluation.get("partial_match_weight"),
            evaluation.get("must_have_gate_mode"),
            evaluation.get("must_have_coverage_min"),
            evaluation.get("include_nice_to_have"),
            weights_key,
            optimization.get("overall_score_threshold")
        )

    def evaluate(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        key = self.key_for(scenario)
        if key in self._cache:
            return self._cache[key]
        evaluation = evaluate_applications(
            self.applications,
            self.job_data,
            scenario,
            include_details=False,
            include_summary_table=False
        )
        summary = evaluation.get("summary", {})
        payload = {
            "summary": summary,
            "candidate_count": summary.get("applications_passed", 0)
        }
        self._cache[key] = payload
        return payload

    def make_result(
        self,
        scenario: Dict[str, Any],
        changes: List[Any],
        cost: float
    ) -> OptimisationResult:
        evaluation = self.evaluate(scenario)
        return OptimisationResult(
            scenario=scenario,
            changes=changes,
            cost=cost,
            summary=evaluation["summary"],
            candidate_count=evaluation["candidate_count"]
        )


def run_optimisation(
    db: Session,
    job_id: int,
    optimisation_payload: Dict[str, Any],
    candidate_count_override: Optional[int] = None,
    top_k_override: Optional[int] = None,
    include_details: bool = False,
    include_summary_table: bool = False,
    include_best_only: bool = True
) -> Dict[str, Any]:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise OptimisationValidationError([f"Job {job_id} not found."])

    config = load_optimisation_config(optimisation_payload)

    job_data = cast(Dict[str, Any], job.job_data)
    target_count = candidate_count_override or config.target.candidate_count
    if target_count is None:
        raise OptimisationValidationError(
            ["target.candidate_count is required (or provide an override)."]
        )

    if top_k_override is not None:
        if isinstance(top_k_override, bool) or not isinstance(top_k_override, int):
            raise OptimisationValidationError(["top_k override must be an integer."])
        if top_k_override <= 0:
            raise OptimisationValidationError(["top_k override must be positive."])
        config.top_k = top_k_override

    baseline_scenario, _ = normalize_scenario(
        json.loads(json.dumps(DEFAULT_SCENARIO)),
        job_data,
        strict=True
    )

    applications = (
        db.query(Application)
        .join(Candidate)
        .filter(Application.job_id == job_id)
        .all()
    )

    evaluator = ScenarioEvaluator(job_data, applications)
    space = RelaxationSpace(job_data, config)

    strategy = StrategyFactory.create(config.strategy)
    context = SearchContext(
        space=space,
        evaluator=evaluator,
        config=config,
        target_count=target_count,
        ranker=_rank_result,
        baseline_scenario=baseline_scenario
    )

    results = strategy.run(context)
    results.sort(key=lambda item: _rank_result(item, target_count))

    top_results = results[: config.top_k]
    output_results = []
    for result in top_results:
        result_payload = result.to_dict()
        result_payload["shock_report"] = build_shock_report(job_data, result.scenario)
        output_results.append(result_payload)

    baseline_summary = evaluator.evaluate(baseline_scenario)
    output = {
        "job_id": job_id,
        "target": {"candidate_count": target_count, "mode": config.target.mode},
        "baseline": {
            "candidate_count": baseline_summary["candidate_count"],
            "summary": baseline_summary["summary"]
        },
        "results": output_results
    }

    if include_details or include_summary_table:
        detail_count = 1 if include_best_only else len(top_results)
        for index in range(detail_count):
            scenario = top_results[index].scenario
            evaluation = evaluate_applications(
                applications,
                job_data,
                scenario,
                include_details=include_details,
                include_summary_table=include_summary_table
            )
            if include_details:
                output_results[index]["candidates"] = evaluation.get("candidates", [])
            if include_summary_table:
                output_results[index]["summary_table"] = evaluation.get("summary_table", [])

    return output


def _rank_result(result: OptimisationResult, target_count: int) -> tuple:
    meets_target = result.candidate_count >= target_count
    average_score = result.summary.get("average_score", 0.0)
    return (
        0 if meets_target else 1,
        result.cost,
        -result.candidate_count,
        -average_score
    )
