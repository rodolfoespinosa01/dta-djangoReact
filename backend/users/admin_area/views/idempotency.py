import hashlib
import json

from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response

from users.admin_area.views.api_contract import error

IDEMPOTENCY_HEADER = "Idempotency-Key"
DEFAULT_TTL_SECONDS = 60 * 60 * 24


def _canonical_body(request):
    data = getattr(request, "data", None)
    if data is None:
        return ""
    try:
        return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    except Exception:
        return str(data)


def _fingerprint(request, actor: str):
    material = "|".join(
        [
            getattr(request, "method", ""),
            getattr(request, "path", ""),
            actor,
            _canonical_body(request),
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _safe_payload(data):
    try:
        return json.loads(json.dumps(data, default=str))
    except Exception:
        return {}


def begin_idempotent_request(request, namespace: str, actor: str, ttl_seconds: int = DEFAULT_TTL_SECONDS):
    key = (request.headers.get(IDEMPOTENCY_HEADER) or "").strip()
    if not key:
        return None, lambda response: response

    fingerprint = _fingerprint(request, actor=actor)
    cache_key = f"idempotency:{namespace}:{actor}:{key}"
    cached = cache.get(cache_key)
    if cached:
        if cached.get("fingerprint") != fingerprint:
            return (
                error(
                    code="IDEMPOTENCY_KEY_REUSED",
                    message="Idempotency key was already used with a different request payload.",
                    http_status=status.HTTP_409_CONFLICT,
                ),
                lambda response: response,
            )
        return (
            Response(cached.get("payload", {}), status=int(cached.get("status", status.HTTP_200_OK))),
            lambda response: response,
        )

    def finalize(response):
        if not isinstance(response, Response):
            return response
        if response.status_code >= 500:
            return response
        cache.set(
            cache_key,
            {
                "fingerprint": fingerprint,
                "status": int(response.status_code),
                "payload": _safe_payload(response.data),
            },
            timeout=ttl_seconds,
        )
        return response

    return None, finalize
