import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { jwtDecode } from 'jwt-decode';
import { useNavigate, useLocation } from 'react-router-dom';

const AuthContext = createContext(null);

// Public routes (no auth required)
const PUBLIC_PATHS = new Set([
  '/',
  '/welcome',
  '/admin_homepage',
  '/admin_plans',
  '/admin_checkout',
  '/admin_thank_you',
  '/admin_register',
  '/admin_trial_ended',
  '/admin_login',
  '/admin_forgot_password',         // forgot page
  '/user_homepage',
  '/user_plans',
  '/user_login',
  '/client_login',
  '/client_register',
  '/client_signup_success',
  '/macro_calculator',
  '/superadmin_login',
]);

// Public routes that may include tokens / dynamic parts
const PUBLIC_PREFIXES = [
  '/admin_reset_password',          // e.g. /admin_reset_password?token=...
  '/start/',                       // admin-branded end-user marketing pages
];

const getDefaultLoginRouteForPath = (pathname) => {
  if ((pathname || '').startsWith('/superadmin')) return '/superadmin_login';
  if ((pathname || '').startsWith('/client')) return '/client_login';
  return '/admin_login';
};

const isPublicRoute = (pathname) =>
  PUBLIC_PATHS.has(pathname) || PUBLIC_PREFIXES.some(p => pathname.startsWith(p));

const ACCESS_KEY = 'access_token';
const REFRESH_KEY = 'refresh_token';

const safeStorage = {
  get(key) {
    try {
      return localStorage.getItem(key);
    } catch (err) {
      console.error('[Auth] localStorage get failed:', err);
      return null;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, value);
      return true;
    } catch (err) {
      console.error('[Auth] localStorage set failed:', err);
      return false;
    }
  },
  remove(key) {
    try {
      localStorage.removeItem(key);
      return true;
    } catch (err) {
      console.error('[Auth] localStorage remove failed:', err);
      return false;
    }
  },
};

const isExpired = (token) => {
  try {
    const { exp } = jwtDecode(token) || {};
    return !exp || exp * 1000 < Date.now();
  } catch {
    return true;
  }
};

export const AuthProvider = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const [auth, setAuth] = useState({
    user: null,
    accessToken: null,
    isAuthenticated: false,
    loading: true,
  });

  const login = useCallback((loginData) => {
    try {
      const decoded = jwtDecode(loginData.access);
      safeStorage.set(ACCESS_KEY, loginData.access);
      safeStorage.set(REFRESH_KEY, loginData.refresh);
      setAuth({
        user: decoded,
        accessToken: loginData.access,
        isAuthenticated: true,
        loading: false,
      });
    } catch (err) {
      console.error('❌ Failed to decode access token in login()', err);
    }
  }, []);

  const logout = useCallback((redirectTo = '/admin_login') => {
    safeStorage.remove(ACCESS_KEY);
    safeStorage.remove(REFRESH_KEY);
    setAuth({ user: null, accessToken: null, isAuthenticated: false, loading: false });
    if (location.pathname !== redirectTo) navigate(redirectTo, { replace: true });
  }, [location.pathname, navigate]);

  // Rehydrate & guard routes
  useEffect(() => {
    const access = safeStorage.get(ACCESS_KEY);
    const refresh = safeStorage.get(REFRESH_KEY);

    // Unauthenticated: allow public routes; otherwise redirect
    if (!access || !refresh) {
      setAuth({ user: null, accessToken: null, isAuthenticated: false, loading: false });
      if (!isPublicRoute(location.pathname)) logout(getDefaultLoginRouteForPath(location.pathname));
      return;
    }

    // Tokens present: validate access token
    if (isExpired(access)) {
      console.warn('⏰ Access token expired — logging out');
      logout(isPublicRoute(location.pathname) ? location.pathname : getDefaultLoginRouteForPath(location.pathname));
      return;
    }

    try {
      const decoded = jwtDecode(access);
      setAuth({
        user: decoded,
        accessToken: access,
        isAuthenticated: true,
        loading: false,
      });

      // Optional: redirect canceled trial admins
      if (
        decoded.role === 'admin' &&
        decoded.subscription_status === 'admin_trial' &&
        decoded.is_canceled
      ) {
        if (location.pathname !== '/admin_trial_ended') {
          navigate('/admin_trial_ended', { replace: true });
        }
      }
    } catch (err) {
      console.error('❌ Error decoding token on rehydrate:', err);
      logout(isPublicRoute(location.pathname) ? location.pathname : getDefaultLoginRouteForPath(location.pathname));
    }
    // Re-run on path change so public-route checks apply to direct navigations
  }, [location.pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  const value = useMemo(
    () => ({
      ...auth,
      login,
      logout,
    }),
    [auth, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => useContext(AuthContext);
