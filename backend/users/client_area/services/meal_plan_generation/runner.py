from __future__ import annotations

from dataclasses import asdict, dataclass
import uuid
from typing import Any

from django.db import transaction
from django.utils import timezone

from users.client_area.models import (
    ClientMealPlanGeneratedMeal,
    ClientMealPlanGenerationJob,
    ClientMealPlanGenerationStep1Row,
    ClientProfile,
    ClientQuestionnaireProgress,
)
from users.client_area.services.results_engine import BuildResultsContext, build_questionnaire_results

from .step1 import build_step1_rows_for_day
from .pipeline import run_steps_2_to_10_for_day


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


@dataclass
class FullGenerationRunResult:
    job_id: int
    status: str
    day_of_week: str
    row_count: int
    generated_meal_count: int
    current_step: int
    progress_percent: int
    note: str


@dataclass
class FullWeekGenerationRunResult:
    days_requested: list[str]
    days_completed: list[str]
    jobs: list[dict[str, Any]]
    note: str


def _normalize_day(day: str | None) -> str:
    value = (day or "sunday").strip().lower()
    return value if value in WEEK_DAYS else "sunday"


def _normalize_days(days: list[str] | None) -> list[str]:
    if not days:
        return list(WEEK_DAYS)
    normalized = []
    for day in days:
        value = (day or "").strip().lower()
        if value in WEEK_DAYS and value not in normalized:
            normalized.append(value)
    return normalized or list(WEEK_DAYS)


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


def _seed_job_input_snapshot(*, day_payload, results, progress, note: str):
    return {
        "day_payload": day_payload,
        "profile": results.get("profile") or {},
        "core_calculations": results.get("core_calculations") or {},
        "parameter_settings": results.get("parameter_settings") or {},
        "generated_at": results.get("generated_at"),
        "questionnaire_completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
        "implementation_note": note,
    }


def _with_optional_batch_snapshot(snapshot: dict[str, Any], batch_id: str | None = None, batch_mode: str | None = None):
    if batch_id:
        snapshot["batch_id"] = batch_id
    if batch_mode:
        snapshot["batch_mode"] = batch_mode
    return snapshot


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
        input_snapshot_json=_seed_job_input_snapshot(
            day_payload=day_payload,
            results=results,
            progress=progress,
            note="Only Step1 is currently ported from the WordPress meal generation pipeline.",
        ),
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


@transaction.atomic
def run_full_generation_for_day(
    user,
    day_of_week: str | None = None,
    *,
    batch_id: str | None = None,
    batch_mode: str | None = None,
) -> FullGenerationRunResult:
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
        input_snapshot_json=_with_optional_batch_snapshot(
            _seed_job_input_snapshot(
                day_payload=day_payload,
                results=results,
                progress=progress,
                note="Running full WP-style meal generation port (Steps 1-10).",
            ),
            batch_id=batch_id,
            batch_mode=batch_mode,
        ),
    )

    try:
        row_count = build_step1_rows_for_day(job, day_payload)
        job.current_step = 1
        job.progress_percent = 10
        job.save(update_fields=["current_step", "progress_percent", "updated_at"])

        pipeline_result = run_steps_2_to_10_for_day(job=job, day_payload=day_payload)
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        raise

    job.status = "completed"
    job.current_step = 10
    job.progress_percent = 100
    job.completed_at = timezone.now()
    snapshot = dict(job.input_snapshot_json or {})
    snapshot["pipeline_summary"] = {
        "step1_rows": pipeline_result.step1_row_count,
        "generated_meals": pipeline_result.generated_meal_count,
        "selected_candidates": pipeline_result.selected_candidate_count,
    }
    job.input_snapshot_json = snapshot
    job.save(
        update_fields=[
            "status",
            "current_step",
            "progress_percent",
            "completed_at",
            "input_snapshot_json",
            "updated_at",
        ]
    )

    return FullGenerationRunResult(
        job_id=job.id,
        status=job.status,
        day_of_week=job.day_of_week,
        row_count=row_count,
        generated_meal_count=pipeline_result.generated_meal_count,
        current_step=job.current_step,
        progress_percent=job.progress_percent,
        note=pipeline_result.note,
    )


def run_full_generation_for_week(
    user,
    days: list[str] | None = None,
    *,
    batch_id: str | None = None,
    batch_mode: str | None = "week",
) -> FullWeekGenerationRunResult:
    requested_days = _normalize_days(days)
    jobs: list[dict[str, Any]] = []
    completed: list[str] = []

    for day in requested_days:
        result = run_full_generation_for_day(user, day_of_week=day, batch_id=batch_id, batch_mode=batch_mode)
        jobs.append(
            {
                "day_of_week": result.day_of_week,
                "job_id": result.job_id,
                "status": result.status,
                "step1_row_count": result.row_count,
                "generated_meal_count": result.generated_meal_count,
                "current_step": result.current_step,
                "progress_percent": result.progress_percent,
                "note": result.note,
            }
        )
        completed.append(result.day_of_week)

    return FullWeekGenerationRunResult(
        days_requested=requested_days,
        days_completed=completed,
        jobs=jobs,
        note="Completed full-week meal generation using the WP-style Steps 1-10 pipeline for each requested day.",
    )


def launch_full_generation_for_week_background(user, days: list[str] | None = None) -> dict[str, Any]:
    requested_days = _normalize_days(days)
    batch_id = str(uuid.uuid4())
    # Lazy import keeps the synchronous generation path free of task import side effects.
    try:
        from users.client_area.tasks import run_week_generation_batch_task
    except ModuleNotFoundError as exc:
        if "celery" in str(exc).lower():
            raise ValueError(
                "Celery is not installed in the backend virtual environment. "
                "Install backend requirements and restart Django/Celery."
            ) from exc
        raise

    async_result = run_week_generation_batch_task.apply_async(
        kwargs={"user_id": int(user.id), "days": requested_days, "batch_id": batch_id}
    )
    return {
        "batch_id": batch_id,
        "task_id": async_result.id,
        "days_requested": requested_days,
        "queued_at": timezone.now(),
    }


def get_generation_week_batch_status(user, batch_id: str, days: list[str] | None = None) -> dict[str, Any]:
    requested_days = _normalize_days(days)
    jobs_qs = (
        ClientMealPlanGenerationJob.objects.filter(user=user, input_snapshot_json__batch_id=batch_id)
        .order_by("day_of_week", "-created_at")
    )
    latest_by_day: dict[str, ClientMealPlanGenerationJob] = {}
    for job in jobs_qs:
        if job.day_of_week not in latest_by_day:
            latest_by_day[job.day_of_week] = job

    jobs = []
    days_completed = []
    any_running = False
    any_failed = False
    for day in requested_days:
        job = latest_by_day.get(day)
        if not job:
            jobs.append(
                {
                    "day_of_week": day,
                    "job_id": None,
                    "status": "queued",
                    "current_step": 0,
                    "progress_percent": 0,
                    "generated_meal_count": 0,
                }
            )
            continue

        generated_count = ClientMealPlanGeneratedMeal.objects.filter(job=job).count() if job.status == "completed" else 0
        jobs.append(
            {
                "day_of_week": day,
                "job_id": job.id,
                "status": job.status,
                "current_step": job.current_step,
                "progress_percent": job.progress_percent,
                "generated_meal_count": generated_count,
                "error_message": job.error_message,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
            }
        )
        if job.status == "completed":
            days_completed.append(day)
        elif job.status == "running" or job.status == "pending":
            any_running = True
        elif job.status == "failed":
            any_failed = True

    if len(days_completed) == len(requested_days):
        batch_status = "completed"
    elif any_failed:
        batch_status = "failed"
    elif any_running or any(job["status"] == "queued" for job in jobs):
        batch_status = "running"
    else:
        batch_status = "pending"

    return {
        "batch_id": batch_id,
        "status": batch_status,
        "days_requested": requested_days,
        "days_completed": days_completed,
        "jobs": jobs,
    }


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
    generated_rows = list(
        ClientMealPlanGeneratedMeal.objects.filter(job=job)
        .select_related("combo_template")
        .order_by("meal_number")
        .values(
            "meal_number",
            "error_code",
            "combo_template_id",
            "protein1_total",
            "protein2_total",
            "carbs1_total",
            "carbs2_total",
            "fats1_total",
            "fats2_total",
        )[:10]
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
        "generated_meals": {
            "row_count": ClientMealPlanGeneratedMeal.objects.filter(job=job).count(),
            "sample_rows": generated_rows,
        },
        "input_snapshot": job.input_snapshot_json or {},
    }


def get_generated_meal_day_detail(user, day_of_week: str | None = None, job_id: int | None = None) -> dict[str, Any] | None:
    day = _normalize_day(day_of_week)
    base_qs = ClientMealPlanGenerationJob.objects.filter(user=user, day_of_week=day)
    if job_id is not None:
        job = base_qs.filter(id=job_id).first()
    else:
        job = base_qs.order_by("-created_at").first()
    if not job:
        return None

    rows = list(
        ClientMealPlanGeneratedMeal.objects.filter(job=job)
        .select_related("combo_template")
        .order_by("meal_number")
    )
    if not rows:
        return {
            "job_id": job.id,
            "day_of_week": day,
            "training_time": ((job.input_snapshot_json or {}).get("day_payload") or {}).get("training_before_meal") or "none",
            "meals": [],
        }

    day_payload = ((job.input_snapshot_json or {}).get("day_payload") or {})
    training_time = day_payload.get("training_before_meal") or "none"

    def _slot_payload(name: str, amount):
        amount_oz = float(amount or 0)
        return {
            "name": name or "-",
            "amount_oz": amount_oz,
            "amount_g": round(amount_oz * 28.3495, 2),
        }

    meals = []
    for row in rows:
        combo = row.combo_template
        meals.append(
            {
                "meal_number": row.meal_number,
                "combo_id": row.combo_template_id,
                "error_code": row.error_code,
                "slots": {
                    "protein_1": _slot_payload(combo.protein_slot_1, row.protein1_total),
                    "protein_2": _slot_payload(combo.protein_slot_2, row.protein2_total),
                    "carbs_1": _slot_payload(combo.carb_slot_1, row.carbs1_total),
                    "carbs_2": _slot_payload(combo.carb_slot_2, row.carbs2_total),
                    "fats_1": _slot_payload(combo.fat_slot_1, row.fats1_total),
                    "fats_2": _slot_payload(combo.fat_slot_2, row.fats2_total),
                },
            }
        )

    return {
        "job_id": job.id,
        "day_of_week": day,
        "job_status": job.status,
        "progress_percent": job.progress_percent,
        "training_time": training_time,
        "meals_per_day": day_payload.get("meals_per_day"),
        "meals": meals,
    }
