from __future__ import annotations

from dataclasses import dataclass


class PrivateMealSolverUnavailable(RuntimeError):
    """Raised when proprietary meal solver code is not installed locally."""


@dataclass
class FullPipelineRunResult:
    generated_meal_count: int
    selected_candidate_count: int
    step1_row_count: int
    note: str


def _load_private_pipeline():
    try:
        from private_meal_solver.pipeline_private import run_steps_2_to_10_for_day as private_runner
    except ImportError as exc:
        raise PrivateMealSolverUnavailable(
            "Private meal-plan solver is not installed. "
            "Restore backend/private_meal_solver/ from your private source before running full meal generation."
        ) from exc
    return private_runner


def run_steps_2_to_10_for_day(*, job, day_payload: dict) -> FullPipelineRunResult:
    private_runner = _load_private_pipeline()
    return private_runner(job=job, day_payload=day_payload)
