// AdminProtectedRoute.jsx
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function AdminProtectedRoute({ children }) {
  const { user, isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) return <p>Loading...</p>;

  if (!isAuthenticated) {
    console.warn('[Guard] not authed -> /admin_login');
    return <Navigate to="/admin_login" replace state={{ from: location }} />;
  }
  if (user?.role !== 'admin') {
    console.warn('[Guard] wrong role -> /admin_login');
    return <Navigate to="/admin_login" replace />;
  }

  if (location.pathname === '/admin_reactivate') {
    console.log('[Guard] allow /admin_reactivate');
    return children;
  }

  console.log('[Guard] allow', location.pathname);
  return children;
}
export default AdminProtectedRoute;
