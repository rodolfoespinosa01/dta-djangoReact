from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from users.client_area.services.meal_plan_generation import (
    get_generated_meal_day_detail,
    get_generation_job_snapshot,
    get_generation_week_batch_status,
    launch_full_generation_for_week_background,
    run_full_generation_for_day,
    run_full_generation_for_week,
    run_step1_for_day,
)
from users.client_area.views.api_contract import error, ok, require_client


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def client_meal_plan_generation_run_week(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    raw_days = (request.data or {}).get("days")
    days = raw_days if isinstance(raw_days, list) else None
    try:
        result = launch_full_generation_for_week_background(request.user, days=days)
    except ValueError as exc:
        return error("GENERATION_PRECONDITION_FAILED", str(exc), http_status=400)
    except Exception as exc:
        return error("GENERATION_FAILED", f"Weekly meal generation failed: {exc}", http_status=500)

    return ok(
        {
            "message": "Weekly meal generation queued in the background.",
            "generation_week": {
                "batch_id": result["batch_id"],
                "task_id": result.get("task_id"),
                "status": "queued",
                "days_requested": result["days_requested"],
                "days_completed": [],
                "jobs": [],
                "queued_at": result["queued_at"],
                "note": "Background week generation started. Poll the batch status endpoint for progress.",
            },
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def client_meal_plan_generation_run_full(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    day_of_week = ((request.data or {}).get("day_of_week") or "sunday").strip().lower()
    try:
        result = run_full_generation_for_day(request.user, day_of_week=day_of_week)
    except ValueError as exc:
        return error("GENERATION_PRECONDITION_FAILED", str(exc), http_status=400)
    except Exception as exc:
        return error("GENERATION_FAILED", f"Meal generation failed: {exc}", http_status=500)

    return ok(
        {
            "message": "Meal generation Steps 1-10 completed.",
            "generation": {
                "job_id": result.job_id,
                "status": result.status,
                "day_of_week": result.day_of_week,
                "step1_row_count": result.row_count,
                "generated_meal_count": result.generated_meal_count,
                "current_step": result.current_step,
                "progress_percent": result.progress_percent,
                "note": result.note,
            },
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def client_meal_plan_generation_step1_run(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    day_of_week = ((request.data or {}).get("day_of_week") or "sunday").strip().lower()
    try:
        result = run_step1_for_day(request.user, day_of_week=day_of_week)
    except ValueError as exc:
        return error("GENERATION_PRECONDITION_FAILED", str(exc), http_status=400)
    except Exception as exc:
        return error("GENERATION_FAILED", f"Step1 generation failed: {exc}", http_status=500)

    return ok(
        {
            "message": "Meal generation Step1 completed.",
            "generation": {
                "job_id": result.job_id,
                "status": result.status,
                "day_of_week": result.day_of_week,
                "row_count": result.row_count,
                "current_step": result.current_step,
                "progress_percent": result.progress_percent,
                "note": result.note,
            },
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def client_meal_plan_generation_run_week_status(request, batch_id: str):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    raw_days = request.query_params.getlist("day")
    days = raw_days if raw_days else None
    try:
        payload = get_generation_week_batch_status(request.user, batch_id=batch_id, days=days)
    except ValueError as exc:
        return error("INVALID_BATCH_QUERY", str(exc), http_status=400)

    return ok({"generation_week": payload})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def client_meal_plan_day_detail(request, day_of_week: str):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    raw_job_id = request.query_params.get("job_id")
    job_id = None
    if raw_job_id is not None:
        try:
            job_id = int(raw_job_id)
        except (TypeError, ValueError):
            return error("INVALID_JOB_ID", "`job_id` must be an integer.", http_status=400)

    payload = get_generated_meal_day_detail(request.user, day_of_week=day_of_week, job_id=job_id)
    if not payload:
        return error("DAY_PLAN_NOT_FOUND", "No generated meal plan found for that day.", http_status=404)

    return ok({"meal_plan_day": payload})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def client_meal_plan_generation_job_status(request, job_id: int):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    snapshot = get_generation_job_snapshot(request.user, job_id)
    if not snapshot:
        return error("JOB_NOT_FOUND", "Generation job not found.", http_status=404)

    return ok({"generation": snapshot})
