const resolveDefaultApiBase = () => {
  // In local development, use same-origin requests so CRA dev server can proxy /api to Django.
  // This avoids direct phone->:8000 LAN calls that can be flaky on some networks/firewalls.
  if (process.env.NODE_ENV !== 'production') {
    return '';
  }
  if (typeof window === 'undefined' || !window.location?.hostname) {
    return 'http://localhost:8000';
  }
  const hostname = window.location.hostname;
  // lvh.me subdomains are frontend-only branding in local dev; always target local backend host.
  if (hostname.endsWith('.lvh.me')) {
    return `${window.location.protocol}//localhost:8000`;
  }
  return `${window.location.protocol}//${hostname}:8000`;
};

const defaultApiBase = resolveDefaultApiBase();

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || defaultApiBase;

if (process.env.NODE_ENV !== 'production') {
  // Helps debug local mixed-content issues (http API on https frontend).
  console.log('[api] API_BASE_URL:', API_BASE_URL);
}

export function buildApiUrl(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

export default API_BASE_URL;
