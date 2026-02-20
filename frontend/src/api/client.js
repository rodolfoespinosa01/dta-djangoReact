import { buildApiUrl } from '../config/api';

let refreshPromise = null;

function getAccessToken() {
  return localStorage.getItem('access_token');
}

function getRefreshToken() {
  return localStorage.getItem('refresh_token');
}

async function refreshAccessToken() {
  if (refreshPromise) return refreshPromise;

  const refresh = getRefreshToken();
  if (!refresh) return null;

  refreshPromise = fetch(buildApiUrl('/api/v1/users/auth/refresh/'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })
    .then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data?.access) return null;
      localStorage.setItem('access_token', data.access);
      return data.access;
    })
    .catch(() => null)
    .finally(() => {
      refreshPromise = null;
    });

  return refreshPromise;
}

function normalizeBody(body, headers) {
  if (body == null) return { body, headers };
  if (typeof body === 'string' || body instanceof FormData) return { body, headers };

  return {
    body: JSON.stringify(body),
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  };
}

function uuid() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function createIdempotencyKey(scope = 'web') {
  return `${scope}:${uuid()}`;
}

export async function apiRequest(path, options = {}) {
  const {
    method = 'GET',
    body,
    headers = {},
    auth = false,
    retryOnUnauthorized = true,
    credentials,
    idempotencyKey,
  } = options;

  const payload = normalizeBody(body, headers);

  const doFetch = async (token) => {
    const requestHeaders = { ...payload.headers };
    if (idempotencyKey) {
      requestHeaders['Idempotency-Key'] = idempotencyKey;
    }
    if (auth && token) {
      requestHeaders.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(buildApiUrl(path), {
      method,
      headers: requestHeaders,
      body: payload.body,
      ...(credentials ? { credentials } : {}),
    });

    const data = await response.json().catch(() => null);
    return { response, data };
  };

  let token = auth ? getAccessToken() : null;
  let { response, data } = await doFetch(token);

  if (auth && retryOnUnauthorized && response.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      ({ response, data } = await doFetch(refreshed));
    }
  }

  return {
    ok: response.ok,
    status: response.status,
    data,
    response,
  };
}
