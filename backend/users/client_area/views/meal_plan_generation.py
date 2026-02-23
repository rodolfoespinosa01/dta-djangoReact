from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from users.client_area.services.meal_plan_generation import (
    get_generation_job_snapshot,
    run_step1_for_day,
)
from users.client_area.views.api_contract import error, ok, require_client


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
def client_meal_plan_generation_job_status(request, job_id: int):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    snapshot = get_generation_job_snapshot(request.user, job_id)
    if not snapshot:
        return error("JOB_NOT_FOUND", "Generation job not found.", http_status=404)

    return ok({"generation": snapshot})
