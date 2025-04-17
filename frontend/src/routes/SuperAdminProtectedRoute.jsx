import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function SuperAdminProtectedRoute({ children }) {
  const { user, isAuthenticated, loading } = useAuth();

  if (loading) return <p>Loading...</p>;
  if (!isAuthenticated || !user?.is_superuser) {
    return <Navigate to="/superadmin-login" />;
  }

  return children;
}

export default SuperAdminProtectedRoute;
