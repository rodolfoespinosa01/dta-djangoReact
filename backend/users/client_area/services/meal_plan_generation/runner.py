from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from django.db import transaction
from django.utils import timezone

from users.client_area.models import (
    ClientMealPlanGenerationJob,
    ClientMealPlanGenerationStep1Row,
    ClientProfile,
    ClientQuestionnaireProgress,
)
from users.client_area.services.results_engine import BuildResultsContext, build_questionnaire_results

from .step1 import build_step1_rows_for_day


WEEK_DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]


@dataclass
class Step1RunResult:
    job_id: int
    status: str
    day_of_week: str
    row_count: int
    current_step: int
    progress_percent: int
    note: str


def _normalize_day(day: str | None) -> str:
    value = (day or "sunday").strip().lower()
    return value if value in WEEK_DAYS else "sunday"


def _get_client_generation_context(user):
    profile = ClientProfile.objects.filter(user=user).select_related("associated_admin").first()
    if not profile:
        raise ValueError("Client profile not found.")
    progress = ClientQuestionnaireProgress.objects.filter(user=user).first()
    if not progress or progress.status != "completed":
        raise ValueError("Complete the questionnaire before generating a meal plan.")
    results = build_questionnaire_results(
        BuildResultsContext(
            answers=progress.answers_json or {},
            admin_identity=profile.associated_admin if profile else None,
        )
    )
    if not results:
        raise ValueError("Could not build macro results from questionnaire answers.")
    return profile, progress, results


def _find_day_payload(results: dict[str, Any], day: str):
    for row in results.get("weekly_days") or []:
        if (row or {}).get("day") == day:
            return row
    return None


@transaction.atomic
def run_step1_for_day(user, day_of_week: str | None = None) -> Step1RunResult:
    day = _normalize_day(day_of_week)
    profile, progress, results = _get_client_generation_context(user)
    day_payload = _find_day_payload(results, day)
    if not day_payload:
        raise ValueError(f"No calculated macro schedule found for {day}.")

    job = ClientMealPlanGenerationJob.objects.create(
        user=user,
        client_profile=profile,
        day_of_week=day,
        status="running",
        current_step=0,
        progress_percent=0,
        started_at=timezone.now(),
        input_snapshot_json={
            "day_payload": day_payload,
            "profile": results.get("profile") or {},
            "core_calculations": results.get("core_calculations") or {},
            "generated_at": results.get("generated_at"),
            "questionnaire_completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
            "implementation_note": "Only Step1 is currently ported from the WordPress meal generation pipeline.",
        },
    )

    try:
        row_count = build_step1_rows_for_day(job, day_payload)
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        raise

    job.status = "completed"
    job.current_step = 1
    job.progress_percent = 10
    job.completed_at = timezone.now()
    job.save(update_fields=["status", "current_step", "progress_percent", "completed_at", "updated_at"])

    return Step1RunResult(
        job_id=job.id,
        status=job.status,
        day_of_week=job.day_of_week,
        row_count=row_count,
        current_step=job.current_step,
        progress_percent=job.progress_percent,
        note="Step1 completed. Steps 2-10 are not yet ported.",
    )


def get_generation_job_snapshot(user, job_id: int) -> dict[str, Any] | None:
    job = (
        ClientMealPlanGenerationJob.objects.filter(id=job_id, user=user)
        .select_related("client_profile")
        .first()
    )
    if not job:
        return None

    step1_qs = ClientMealPlanGenerationStep1Row.objects.filter(job=job)
    sample_rows = list(
        step1_qs.order_by("meal_number", "error_code")
        .values("meal_number", "error_code", "pro_negative", "carbs_negative", "fats_negative")[:10]
    )

    return {
        "job": {
            "id": job.id,
            "day_of_week": job.day_of_week,
            "status": job.status,
            "algorithm_version": job.algorithm_version,
            "current_step": job.current_step,
            "total_steps": job.total_steps,
            "progress_percent": job.progress_percent,
            "error_message": job.error_message,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
        },
        "step1": {
            "row_count": step1_qs.count(),
            "sample_rows": sample_rows,
        },
        "input_snapshot": job.input_snapshot_json or {},
    }
