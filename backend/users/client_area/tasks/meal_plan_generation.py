from __future__ import annotations

from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import close_old_connections

from users.client_area.services.meal_plan_generation.runner import run_full_generation_for_week


@shared_task(bind=True, autoretry_for=(), retry_backoff=False)
def run_week_generation_batch_task(self, *, user_id: int, days: list[str], batch_id: str):
    """
    Execute week generation in a Celery worker. Progress is tracked through the existing
    per-day ClientMealPlanGenerationJob rows (with input_snapshot_json.batch_id).
    """
    close_old_connections()
    try:
        User = get_user_model()
        user = User.objects.get(id=user_id)
        result = run_full_generation_for_week(user, days=days, batch_id=batch_id, batch_mode="week")
        return {
            "batch_id": batch_id,
            "days_requested": result.days_requested,
            "days_completed": result.days_completed,
            "job_count": len(result.jobs),
        }
    finally:
        close_old_connections()

