import React, { createContext, useContext, useEffect, useState } from 'react';
import { jwtDecode } from 'jwt-decode';
import { useNavigate } from 'react-router-dom';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [auth, setAuth] = useState({
    user: null,
    accessToken: null,
    isAuthenticated: false,
    loading: true,
  });

  const navigate = useNavigate();

  const login = (loginData) => {
    try {
      const decoded = jwtDecode(loginData.access);
      setAuth({
        user: decoded,
        accessToken: loginData.access,
        isAuthenticated: true,
        loading: false, // ✅ THIS is required
      });
  
      localStorage.setItem('access_token', loginData.access);
      localStorage.setItem('refresh_token', loginData.refresh);
  
      console.log('✅ Auth state updated');
    } catch (err) {
      console.error('Failed to decode access token in login()', err);
    }
  };
  

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setAuth({ user: null, accessToken: null, isAuthenticated: false, loading: false });
    navigate('/adminlogin');
  };

  // ✅ Rehydrate session from localStorage on refresh
  useEffect(() => {
    const access = localStorage.getItem('access_token');
    const refresh = localStorage.getItem('refresh_token');

    console.log('🧪 Checking for stored tokens...');
    console.log('Access token:', access);
    console.log('Refresh token:', refresh);

    if (!access || !refresh) {
      console.warn('❌ No tokens found in localStorage');
      setAuth({ user: null, accessToken: null, isAuthenticated: false, loading: false });
      return;
    }

    try {
      const decoded = jwtDecode(access);
      console.log('✅ Decoded access token:', decoded);

      const isExpired = decoded.exp * 1000 < Date.now();
      console.log('⏰ Token expired?', isExpired);

      if (isExpired) {
        console.warn('🔁 Token is expired, logging out...');
        handleLogout();
        return;
      }

      setAuth({
        user: decoded,
        accessToken: access,
        isAuthenticated: true,
        loading: false,
      });

      console.log('✅ Session restored on refresh');
    } catch (err) {
      console.error('❌ Error decoding token on refresh:', err);
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

export const useAuth = () => useContext(AuthContext);
