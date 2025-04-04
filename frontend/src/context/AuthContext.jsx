import React, { createContext, useContext, useEffect, useState } from 'react';
import { jwtDecode } from 'jwt-decode';
import { useNavigate } from 'react-router-dom';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [auth, setAuth] = useState({
    user: null,
    accessToken: null,
    isAuthenticated: false,
  });

  const navigate = useNavigate();

  const login = (token) => {
    try {
      const decoded = jwtDecode(token);
      setAuth({
        user: decoded,
        accessToken: token,
        isAuthenticated: true,
      });
      localStorage.setItem('access_token', token);
    } catch (err) {
      console.error('Failed to decode token in login()', err);
    }
  };
  

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    try {
      const decoded = jwtDecode(token);
      const isExpired = decoded.exp * 1000 < Date.now();

      if (isExpired) {
        handleLogout();
        return;
      }

      setAuth({
        user: decoded,
        accessToken: token,
        isAuthenticated: true,
      });
    } catch (err) {
      console.error('Error decoding token:', err);
      handleLogout();
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setAuth({ user: null, accessToken: null, isAuthenticated: false });
    navigate('/adminlogin');
  };

  const value = {
    ...auth,
    logout: handleLogout,
    login,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};



export const useAuth = () => useContext(AuthContext);
