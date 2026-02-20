import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';

function SuperAdminProtectedRoute({ children }) {
  const { user, isAuthenticated, loading } = useAuth();
  const { t } = useLanguage();

  if (loading) return <p>{t('guard.loading')}</p>;
  if (!isAuthenticated || !user?.is_superuser) {
    return <Navigate to="/superadmin_login" />;
  }

  return children;
}

export default SuperAdminProtectedRoute;
