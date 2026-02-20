# DTA API v1

Base path: `/api/v1`

## Docs
- Schema JSON: `/api/v1/schema/`
- Lightweight docs page: `/api/v1/docs/`
- Error code catalog (machine-readable): `/api/v1/meta/error-codes/`

## Auth
- Refresh access token: `POST /api/v1/users/auth/refresh/`
  - Request: `{ "refresh": "<jwt_refresh_token>" }`
  - Success: `{ "access": "<new_access_token>" }`

## Endpoint Examples

### Admin Login
- `POST /api/v1/users/admin/login/`
- Request:
```json
{
  "username": "coach@example.com",
  "password": "your-password"
}
```
- Success:
```json
{
  "ok": true,
  "access": "jwt-access",
  "refresh": "jwt-refresh",
  "email": "coach@example.com",
  "role": "admin",
  "subscription_status": "admin_monthly",
  "is_canceled": false
}
```
- Error:
```json
{
  "ok": false,
  "error": {
    "code": "WRONG_PASSWORD",
    "message": "Account found, but the password is incorrect."
  },
  "error_code": "WRONG_PASSWORD"
}
```

### Admin Dashboard
- `GET /api/v1/users/admin/dashboard/`
- Success:
```json
{
  "ok": true,
  "subscription_status": "admin_monthly",
  "subscription_active": true,
  "is_canceled": false,
  "next_billing": "2026-03-01T00:00:00Z"
}
```
- Inactive (still includes payload details for UI state):
```json
{
  "ok": false,
  "error": {
    "code": "SUBSCRIPTION_INACTIVE",
    "message": "Subscription is inactive."
  },
  "subscription_status": "admin_inactive",
  "subscription_active": false
}
```

### Create Checkout Session
- `POST /api/v1/users/admin/create_checkout_session/`
- Optional header for safe retries: `Idempotency-Key: <unique-client-key>`
- Request:
```json
{
  "plan_name": "admin_monthly",
  "email": "coach@example.com",
  "is_trial": false
}
```
- Success:
```json
{
  "ok": true,
  "url": "https://checkout.stripe.com/..."
}
```

### SuperAdmin Dashboard (Paginated)
- `GET /api/v1/users/superadmin/dashboard/?page=1&page_size=25`
- Success:
```json
{
  "ok": true,
  "admins": [
    {
      "email": "coach@example.com",
      "plan": "admin_monthly",
      "amount_spent": 58.0
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 25,
    "total_pages": 4,
    "total_items": 97,
    "has_next": true,
    "has_previous": false
  }
}
```

### SuperAdmin Analytics
- `GET /api/v1/users/superadmin/analytics/?period=day|week|month`
- Default: `period=day` (today, midnight to now in server timezone)
- Success:
```json
{
  "ok": true,
  "period": "day",
  "currency": "USD",
  "total_revenue": 128.0,
  "total_revenue_cents": 12800,
  "transactions": 4,
  "generated_at": "2026-02-20T11:32:05Z",
  "window": {
    "started_at": "2026-02-20T00:00:00Z",
    "ended_at": "2026-02-20T11:32:05Z",
    "timezone": "UTC",
    "bucket": "hour"
  },
  "points": [
    { "label": "00:00", "amount": 0.0, "amount_cents": 0 }
  ]
}
```

## Response Contract (new/standardized endpoints)
- Success: `{ "ok": true, ...payload }`
- Error:
  - `{
      "ok": false,
      "error": {
        "code": "SOME_CODE",
        "message": "Human readable message",
        "details": { ...optional }
      }
    }`

## Notes
- Legacy `/api/users/...` routes remain available for backward compatibility.
- New clients should use `/api/v1/users/...`.

## Pagination Convention
- List endpoints should return:
  - `pagination.page`
  - `pagination.page_size`
  - `pagination.total_pages`
  - `pagination.total_items`
  - `pagination.has_next`
  - `pagination.has_previous`
- Query params:
  - `page` (default `1`)
  - `page_size` (default endpoint-specific, capped at `100`)

## Mobile-First Rules
- Never rely on browser-only state (cookies/localStorage) for API contract behavior.
- Return stable JSON field names and ISO 8601 timestamps.
- Prefer additive changes; avoid breaking response shape in v1.
- Keep business logic in backend services/views so iOS/Android can reuse behavior exactly.

## Canonical Signup Token Endpoint
- Use only:
  - `GET /api/v1/users/admin/pending_signup/{token}/`
- The legacy duplicate import path is retained as compatibility alias in backend code, but clients should always use the route above.

## Error Code Handling (Client Guidance)
- Mobile clients should branch on `error.code`, not on HTTP text messages.
- Suggested fallback:
  - if unknown `error.code`: show `error.message` and log the code to telemetry.

## Idempotency (Retry Safety)
- Supported on billing mutation endpoints:
  - `POST /api/v1/users/admin/create_checkout_session/`
  - `POST /api/v1/users/admin/change_subscription/`
  - `POST /api/v1/users/admin/cancel_subscription/`
  - `POST /api/v1/users/admin/payment_method/update_session/`
  - `POST /api/v1/users/admin/reactivate/start/`
- Send `Idempotency-Key` header for client retries (especially mobile networks/timeouts).
- Same key + same request payload returns the same cached response.
- Same key + different payload returns:
  - `409` with `error.code = "IDEMPOTENCY_KEY_REUSED"`
- Recommendation:
  - generate one key per user action attempt and reuse it only for retries of that same action.
