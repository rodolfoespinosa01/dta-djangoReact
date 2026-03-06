export const THEME_VALUES = ['light', 'dark'];
export const DEFAULT_THEME = 'light';

export const THEME_ROLE_CONFIG = {
  admin: {
    storageKey: 'admin_theme_preference',
    eventName: 'admin-theme-changed',
    endpoint: '/api/v1/users/admin/theme_preference/',
    shellClassPrefix: 'admin-theme',
  },
  client: {
    storageKey: 'client_theme_preference',
    eventName: 'client-theme-changed',
    endpoint: '/api/v1/users/client/app/theme_preference/',
    shellClassPrefix: 'client-theme',
  },
};

export function isThemeRole(role) {
  return role === 'admin' || role === 'client';
}

export function normalizeTheme(theme) {
  return theme === 'dark' ? 'dark' : DEFAULT_THEME;
}

export function getThemeRoleConfig(role) {
  return THEME_ROLE_CONFIG[role] || null;
}
