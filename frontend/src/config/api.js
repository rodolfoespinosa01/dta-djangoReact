const defaultApiBase =
  (typeof window !== 'undefined' && window.location?.protocol === 'https:')
    ? 'https://localhost:8000'
    : 'http://localhost:8000';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || defaultApiBase;

export function buildApiUrl(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

export default API_BASE_URL;
