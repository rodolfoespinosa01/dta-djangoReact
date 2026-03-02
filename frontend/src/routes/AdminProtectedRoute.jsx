// AdminProtectedRoute.jsx
import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';

function AdminProtectedRoute({ children }) {
  const { user, isAuthenticated, loading } = useAuth();
  const { t } = useLanguage();
  const location = useLocation();

  if (loading) return <p>{t('guard.loading')}</p>;

  if (!isAuthenticated) {
    console.warn('[Guard] not authed -> /admin_login');
    return <Navigate to="/admin_login" replace state={{ from: location }} />;
  }
  if (user?.role !== 'admin') {
    console.warn('[Guard] wrong role -> /admin_login');
    return <Navigate to="/admin_login" replace />;
  }

  console.log('[Guard] allow', location.pathname);
  return children;
}
export default AdminProtectedRoute;
