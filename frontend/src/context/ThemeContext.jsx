import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { apiRequest } from '../api/client';
import { useAuth } from './AuthContext';
import {
  DEFAULT_THEME,
  getThemeRoleConfig,
  isThemeRole,
  normalizeTheme,
  THEME_ROLE_CONFIG,
} from '../theme/themeConfig';
import { dispatchThemeChanged, readStoredTheme, writeStoredTheme } from '../theme/themeStorage';

const ThemeContext = createContext(null);

function initialThemes() {
  return {
    admin: readStoredTheme('admin'),
    client: readStoredTheme('client'),
  };
}

export function ThemeProvider({ children }) {
  const { isAuthenticated, user } = useAuth();
  const [themes, setThemes] = useState(initialThemes);
  const [savingByRole, setSavingByRole] = useState({ admin: false, client: false });

  const applyLocalTheme = useCallback((role, theme) => {
    const normalized = normalizeTheme(theme);
    if (!isThemeRole(role)) return normalized;
    setThemes((prev) => ({ ...prev, [role]: normalized }));
    writeStoredTheme(role, normalized);
    dispatchThemeChanged(role);
    return normalized;
  }, []);

  const fetchServerTheme = useCallback(async (role) => {
    if (!isThemeRole(role)) return null;
    const config = getThemeRoleConfig(role);
    if (!config || !isAuthenticated) return null;

    const res = await apiRequest(config.endpoint, { auth: true });
    if (!res.ok || !res.data?.theme) return null;
    return applyLocalTheme(role, res.data.theme);
  }, [applyLocalTheme, isAuthenticated]);

  const updateTheme = useCallback(async (role, nextTheme) => {
    if (!isThemeRole(role)) {
      return { ok: false, error: 'Unsupported theme role.' };
    }

    const normalized = normalizeTheme(nextTheme);
    const previous = themes[role] || DEFAULT_THEME;
    const config = getThemeRoleConfig(role);

    applyLocalTheme(role, normalized);
    setSavingByRole((prev) => ({ ...prev, [role]: true }));

    try {
      const res = await apiRequest(config.endpoint, {
        method: 'PUT',
        auth: true,
        body: { theme: normalized },
      });
      if (!res.ok) {
        applyLocalTheme(role, previous);
        return {
          ok: false,
          error: res.data?.error?.message || res.data?.error || 'Unable to update theme preference.',
        };
      }
      applyLocalTheme(role, res.data?.theme || normalized);
      return { ok: true, theme: normalizeTheme(res.data?.theme || normalized) };
    } catch {
      applyLocalTheme(role, previous);
      return { ok: false, error: 'Network error while updating theme preference.' };
    } finally {
      setSavingByRole((prev) => ({ ...prev, [role]: false }));
    }
  }, [applyLocalTheme, themes]);

  useEffect(() => {
    const subscriptions = Object.entries(THEME_ROLE_CONFIG).map(([role, config]) => {
      const onThemeChanged = () => {
        setThemes((prev) => ({ ...prev, [role]: readStoredTheme(role) }));
      };
      window.addEventListener(config.eventName, onThemeChanged);
      return () => window.removeEventListener(config.eventName, onThemeChanged);
    });

    const onStorage = () => {
      setThemes({
        admin: readStoredTheme('admin'),
        client: readStoredTheme('client'),
      });
    };

    window.addEventListener('storage', onStorage);
    return () => {
      subscriptions.forEach((unsubscribe) => unsubscribe());
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  useEffect(() => {
    if (!isAuthenticated || !isThemeRole(user?.role)) return;
    fetchServerTheme(user.role).catch(() => {});
  }, [fetchServerTheme, isAuthenticated, user?.role]);

  const value = useMemo(
    () => ({
      themes,
      savingByRole,
      getTheme: (role) => normalizeTheme(themes[role]),
      fetchServerTheme,
      updateTheme,
    }),
    [themes, savingByRole, fetchServerTheme, updateTheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}
