import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function ClientProtectedRoute({ children }) {
  const { user, isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) return <p>Loading…</p>;
  if (!isAuthenticated) {
    return <Navigate to="/client_login" replace state={{ from: location }} />;
  }
  if (user?.role !== 'client') {
    return <Navigate to="/client_login" replace />;
  }
  return children;
}

export default ClientProtectedRoute;
