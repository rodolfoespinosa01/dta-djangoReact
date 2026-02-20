const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export function buildApiUrl(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

export default API_BASE_URL;
