import React, { createContext, useContext, useEffect, useState } from 'react';
import { jwtDecode } from 'jwt-decode';  // 👉 used to decode the JWT and extract user info
import { useNavigate } from 'react-router-dom';  // 👉 allows programmatic navigation

const AuthContext = createContext();  // 🧠 creates a context to hold auth-related data across the app


export const AuthProvider = ({ children }) => {
  const [auth, setAuth] = useState({
    user: null, // 👤 decoded user info from token
    accessToken: null, // 🔑 raw JWT token for protected API calls
    isAuthenticated: false, // ✅ whether the user is logged in
    loading: true, // ⏳ whether auth state is still being resolved
  });

  const navigate = useNavigate(); // router hook for redirects

  const login = (loginData) => {
    try {
      const decoded = jwtDecode(loginData.access); // decode access token

      setAuth({
        user: decoded,
        accessToken: loginData.access,
        isAuthenticated: true,
        loading: false,
      });

      localStorage.setItem('access_token', loginData.access); // persist tokens
      localStorage.setItem('refresh_token', loginData.refresh);
    } catch (err) {
      console.error('❌ Failed to decode access token in login()', err);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token'); //  remove tokens for logout
    localStorage.removeItem('refresh_token');
    setAuth({ user: null, accessToken: null, isAuthenticated: false, loading: false });
    navigate('/admin_login');
  };

  //  Rehydrate session on reload
  useEffect(() => {
    const access = localStorage.getItem('access_token');
    const refresh = localStorage.getItem('refresh_token');

    if (!access || !refresh) {
      setAuth({ user: null, accessToken: null, isAuthenticated: false, loading: false });

      const publicPaths = [
        '/admin_plans',
        '/admin_checkout',
        '/admin_thank_you',
        '/admin_register',
        '/admin_trial_ended',
        '/'
      ];

      const currentPath = window.location.pathname;
      const isPublic = publicPaths.includes(currentPath);

      if (!isPublic) {
        console.warn('❌ No tokens found — redirecting to login');
        navigate('/admin_login');
      }

  return;
}


    try {
      const decoded = jwtDecode(access);
      const isExpired = decoded.exp * 1000 < Date.now(); // ⏰ check expiration

      if (isExpired) {
        console.warn('⏰ Token is expired, logging out...');
        handleLogout();
        return;
      }

      setAuth({
        user: decoded,
        accessToken: access,
        isAuthenticated: true,
        loading: false,
      });

      // ✅ Redirect if trial admin was canceled
      if (decoded.role === 'admin' && decoded.subscription_status === 'admin_trial' && decoded.is_canceled) {
        console.info('🔁 Trial account canceled — redirecting to trial-ended page...');
        navigate('/admin_trial_ended');
      }

    } catch (err) {
      console.error('❌ Error decoding token on rehydrate:', err);
      setAuth({ user: null, accessToken: null, isAuthenticated: false, loading: false });
    }
  }, []);

  const value = {
    ...auth,
    logout: handleLogout,
    login,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => useContext(AuthContext); // 🔄 custom hook to use auth state


// 👉 summary:
// Provides a global AuthContext for managing login state, token storage, and session restoration.
// Decodes JWT tokens to extract user info, checks for expiration, and redirects canceled trial users.
// Exposes `login` and `logout` functions and rehydrates session on page reload using localStorage.