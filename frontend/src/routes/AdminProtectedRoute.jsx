import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function AdminProtectedRoute({ children }) {
  const { user, isAuthenticated, loading } = useAuth();

  if (loading) return <p>Loading...</p>;

  if (!isAuthenticated || user?.role !== 'admin') {
    console.warn('🚫 Redirecting: not authenticated or wrong role');
    return <Navigate to="/admin-login" />;
  }

  return children; // ← this must be here
}

export default AdminProtectedRoute;
