import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { jwtDecode } from 'jwt-decode';
import { useNavigate, useLocation } from 'react-router-dom';

const AuthContext = createContext(null);

// Public routes (no auth required)
const PUBLIC_PATHS = new Set([
  '/',
  '/admin_plans',
  '/admin_checkout',
  '/admin_thank_you',
  '/admin_register',
  '/admin_trial_ended',
  '/admin_login',
  '/admin_forgot_password',         // forgot page
]);

// Public routes that may include tokens / dynamic parts
const PUBLIC_PREFIXES = [
  '/admin_reset_password',          // e.g. /admin_reset_password?token=...
];

const isPublicRoute = (pathname) =>
  PUBLIC_PATHS.has(pathname) || PUBLIC_PREFIXES.some(p => pathname.startsWith(p));

const ACCESS_KEY = 'access_token';
const REFRESH_KEY = 'refresh_token';

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

  const login = (loginData) => {
    try {
      const decoded = jwtDecode(loginData.access);
      localStorage.setItem(ACCESS_KEY, loginData.access);
      localStorage.setItem(REFRESH_KEY, loginData.refresh);
      setAuth({
        user: decoded,
        accessToken: loginData.access,
        isAuthenticated: true,
        loading: false,
      });
    } catch (err) {
      console.error('❌ Failed to decode access token in login()', err);
    }
  };

  const logout = (redirectTo = '/admin_login') => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    setAuth({ user: null, accessToken: null, isAuthenticated: false, loading: false });
    if (location.pathname !== redirectTo) navigate(redirectTo, { replace: true });
  };

  // Rehydrate & guard routes
  useEffect(() => {
    const access = localStorage.getItem(ACCESS_KEY);
    const refresh = localStorage.getItem(REFRESH_KEY);

    // Unauthenticated: allow public routes; otherwise redirect
    if (!access || !refresh) {
      setAuth({ user: null, accessToken: null, isAuthenticated: false, loading: false });
      if (!isPublicRoute(location.pathname)) logout('/admin_login');
      return;
    }

    // Tokens present: validate access token
    if (isExpired(access)) {
      console.warn('⏰ Access token expired — logging out');
      logout('/admin_login');
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
      logout('/admin_login');
    }
    // Re-run on path change so public-route checks apply to direct navigations
  }, [location.pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  const value = useMemo(
    () => ({
      ...auth,
      login,
      logout,
    }),
    [auth]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => useContext(AuthContext);
