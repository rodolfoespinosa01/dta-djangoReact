import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function AdminProtectedRoute({ children }) {
  const { user, isAuthenticated, loading } = useAuth();

  if (loading) return <p>Loading...</p>;
  if (!isAuthenticated || user?.role !== 'admin') {
    return <Navigate to="/admin-login" />;
  }

  return children;
}

export default AdminProtectedRoute;
