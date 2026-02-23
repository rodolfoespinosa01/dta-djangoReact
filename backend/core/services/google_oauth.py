import os

from django.conf import settings


def get_google_client_ids():
    raw = (
        getattr(settings, "GOOGLE_OAUTH_CLIENT_IDS", None)
        or getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None)
        or os.getenv("GOOGLE_OAUTH_CLIENT_IDS")
        or os.getenv("GOOGLE_OAUTH_CLIENT_ID")
        or ""
    )
    return [value.strip() for value in str(raw).split(",") if value.strip()]


def verify_google_id_token(id_token: str):
    if not id_token:
        raise ValueError("Missing Google ID token.")

    client_ids = get_google_client_ids()
    if not client_ids:
        raise RuntimeError("Google OAuth client ID is not configured.")

    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token
    except Exception as exc:  # pragma: no cover - dependency missing in some envs
        raise RuntimeError("google-auth is not installed. Add it to backend requirements.") from exc

    request_adapter = google_requests.Request()
    last_error = None
    for audience in client_ids:
        try:
            payload = google_id_token.verify_oauth2_token(id_token, request_adapter, audience)
            return payload
        except Exception as exc:  # keep trying other client ids
            last_error = exc

    raise ValueError(f"Unable to verify Google token for configured audience(s): {last_error}")

