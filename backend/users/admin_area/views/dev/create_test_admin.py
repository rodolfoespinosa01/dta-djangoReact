from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from users.admin_area.configs.admin_parameter_defaults import get_admin_parameter_defaults_v1
from users.admin_area.models import AdminIdentity, AdminParameterSettings, Plan
from users.admin_area.utils.log_Profile import log_Profile
from users.admin_area.views.api_contract import error, ok


User = get_user_model()

PLAN_NAME_TO_STATUS = {
    "adminMonthly": "admin_monthly",
    "adminQuarterly": "admin_quarterly",
    "adminAnnual": "admin_annual",
}


def _truthy(v):
    return str(v).strip().lower() in ("true", "1", "yes", "y", "t")


@api_view(["POST"])
@permission_classes([AllowAny])
def create_test_admin(request):
    if not settings.DEBUG:
        return error(
            code="NOT_AVAILABLE",
            message="This endpoint is only available in DEBUG mode.",
            http_status=status.HTTP_404_NOT_FOUND,
        )

    data = request.data or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or "TestAdmin123!"
    plan_name = data.get("plan_name") or "adminMonthly"
    make_trial = _truthy(data.get("is_trial")) if "is_trial" in data else False
    initialize_parameters = _truthy(data.get("initialize_parameters")) if "initialize_parameters" in data else False
    use_default_parameters = _truthy(data.get("use_default_parameters")) if "use_default_parameters" in data else True

    if not email:
        return error(code="MISSING_EMAIL", message="`email` is required.", http_status=400)
    if not password:
        return error(code="MISSING_PASSWORD", message="`password` is required.", http_status=400)

    if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
        return error(
            code="USER_EXISTS",
            message="User already exists. Use a new email or reset data first.",
            http_status=400,
        )

    if plan_name == "adminTrial":
        make_trial = True
        actual_plan_name = "adminMonthly"
    else:
        actual_plan_name = plan_name

    try:
        plan = Plan.objects.get(name=actual_plan_name)
    except Plan.DoesNotExist:
        return error(
            code="PLAN_NOT_FOUND",
            message=f"Plan `{actual_plan_name}` not found. Seed plans first.",
            http_status=404,
        )

    subscription_status = PLAN_NAME_TO_STATUS.get(actual_plan_name, "admin_monthly")

    user = User.objects.create_user(username=email, email=email, password=password)
    user.role = "admin"
    user.is_staff = True
    user.subscription_status = subscription_status
    user.save()

    AdminIdentity.objects.get_or_create(admin_email=email)

    now = timezone.now()
    trial_start = now if make_trial else None
    next_billing = now + timedelta(days=14 if make_trial else 30)
    subscription_start = None if make_trial else now

    log_Profile(
        user=user,
        plan=plan,
        stripe_transaction_id="dev_postman_seed",
        is_trial=make_trial,
        trial_start=trial_start,
        subscription_start=subscription_start,
        subscription_end=None,
        next_billing=next_billing,
        is_canceled=False,
        is_active=True,
    )

    parameter_state = {"exists": False, "initialized": False}
    if initialize_parameters:
        identity = AdminIdentity.objects.get(admin_email=email)
        settings_obj, _ = AdminParameterSettings.objects.get_or_create(admin=identity)
        parameter_state["exists"] = True
        if use_default_parameters:
            defaults = get_admin_parameter_defaults_v1()
            settings_obj.parameters_json = defaults
            settings_obj.defaults_version_applied = defaults.get("version", "v1")
            settings_obj.initialized = True
            settings_obj.save(update_fields=["parameters_json", "defaults_version_applied", "initialized", "updated_at"])
            parameter_state["initialized"] = True
        else:
            parameter_state["initialized"] = bool(settings_obj.initialized)

    refresh = RefreshToken.for_user(user)
    refresh["email"] = user.email
    refresh["role"] = user.role
    refresh["subscription_status"] = user.subscription_status
    refresh["is_canceled"] = False

    return ok(
        {
            "message": "Test admin created.",
            "email": user.email,
            "password_hint": "Use the password you sent in the request.",
            "role": user.role,
            "subscription_status": user.subscription_status,
            "is_trial": make_trial,
            "parameter_settings": parameter_state,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        },
        http_status=status.HTTP_201_CREATED,
    )

