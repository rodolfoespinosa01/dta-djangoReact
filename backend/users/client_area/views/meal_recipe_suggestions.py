from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from users.client_area.services.ai_recipe_suggestions import generate_recipe_ideas_for_day
from users.client_area.services.meal_plan_generation import get_generated_meal_day_detail
from users.client_area.views.api_contract import error, ok, require_client


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def client_meal_plan_day_recipe_ideas(request, day_of_week: str):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    payload = request.data or {}
    raw_job_id = payload.get("job_id")
    raw_meal_number = payload.get("meal_number")

    job_id = None
    if raw_job_id is not None:
        try:
            job_id = int(raw_job_id)
        except (TypeError, ValueError):
            return error("INVALID_JOB_ID", "`job_id` must be an integer.", http_status=400)

    meal_number = None
    if raw_meal_number is not None:
        try:
            meal_number = int(raw_meal_number)
        except (TypeError, ValueError):
            return error("INVALID_MEAL_NUMBER", "`meal_number` must be an integer.", http_status=400)

    day_detail = get_generated_meal_day_detail(request.user, day_of_week=day_of_week, job_id=job_id)
    if not day_detail:
        return error("DAY_PLAN_NOT_FOUND", "No generated meal plan found for that day.", http_status=404)
    if not (day_detail.get("meals") or []):
        return error("DAY_PLAN_EMPTY", "Meal plan exists but no generated meals are available yet.", http_status=400)

    try:
        recipe_ideas = generate_recipe_ideas_for_day(
            day_detail=day_detail,
            ideas_per_meal=payload.get("ideas_per_meal"),
            provider=payload.get("provider"),
            meal_number=meal_number,
        )
    except ValueError as exc:
        return error("RECIPE_IDEAS_CONFIG_ERROR", str(exc), http_status=400)
    except Exception as exc:
        return error("RECIPE_IDEAS_FAILED", f"Unable to generate recipe ideas: {exc}", http_status=500)

    return ok({"recipe_ideas": recipe_ideas})
