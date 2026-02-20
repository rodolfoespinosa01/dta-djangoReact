from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


ERROR_CODE_CATALOG = {
    "auth": [
        "UNAUTHENTICATED",
        "FORBIDDEN",
        "USER_NOT_FOUND",
        "WRONG_PASSWORD",
        "INACTIVE",
    ],
    "admin_profile": [
        "PROFILE_NOT_FOUND",
        "SUBSCRIPTION_INACTIVE",
    ],
    "billing": [
        "MISSING_FIELDS",
        "EMAIL_ALREADY_REGISTERED",
        "PENDING_SIGNUP_EXISTS",
        "TRIAL_NOT_ALLOWED",
        "PLAN_NOT_FOUND",
        "CHECKOUT_SESSION_ERROR",
        "INVALID_TARGET_PLAN",
        "TRANSITION_NOT_ALLOWED",
        "TARGET_PLAN_NOT_CONFIGURED",
        "NO_ACTIVE_SUBSCRIPTION",
        "SUBSCRIPTION_DETAILS_UNAVAILABLE",
        "BILLING_BOUNDARY_UNAVAILABLE",
        "PLAN_CHANGE_SCHEDULE_FAILED",
        "CHECKOUT_SESSION_FAILED",
        "STRIPE_UNCANCEL_FAILED",
        "CUSTOMER_NOT_FOUND",
        "BILLING_PORTAL_UNAVAILABLE",
    ],
    "validation": [
        "VALIDATION_ERROR",
        "INVALID_TOKEN",
        "INVALID_PERIOD",
    ],
    "internal": [
        "DASHBOARD_PAYLOAD_INVALID",
        "PAGINATION_PAYLOAD_INVALID",
    ],
}


@api_view(["GET"])
@permission_classes([AllowAny])
def error_codes(_request):
    return Response(
        {
            "ok": True,
            "catalog_version": "2026-02-20",
            "groups": ERROR_CODE_CATALOG,
        }
    )
