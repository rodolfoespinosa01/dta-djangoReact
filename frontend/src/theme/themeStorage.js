import { getThemeRoleConfig, normalizeTheme } from './themeConfig';

function safeGetItem(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSetItem(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {}
}

export function readStoredTheme(role) {
  const config = getThemeRoleConfig(role);
  if (!config) return normalizeTheme(null);
  return normalizeTheme(safeGetItem(config.storageKey));
}

export function writeStoredTheme(role, theme) {
  const config = getThemeRoleConfig(role);
  if (!config) return;
  safeSetItem(config.storageKey, normalizeTheme(theme));
}

export function dispatchThemeChanged(role) {
  const config = getThemeRoleConfig(role);
  if (!config) return;
  window.dispatchEvent(new Event(config.eventName));
}
