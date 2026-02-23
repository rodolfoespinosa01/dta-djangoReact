// AdminProtectedRoute.jsx
import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { apiRequest } from '../api/client';

function AdminProtectedRoute({ children }) {
  const { user, isAuthenticated, loading } = useAuth();
  const { t } = useLanguage();
  const location = useLocation();
  const [gateState, setGateState] = useState({ checking: true, setupCompleted: true });

  const path = location.pathname;
  const isGateExemptPath = (
    path === '/admin_dashboard'
    || path === '/admin_parameter_settings'
    || path === '/admin_reactivate'
  );

  useEffect(() => {
    let ignore = false;

    const checkParameterInit = async () => {
      if (loading || !isAuthenticated || user?.role !== 'admin') return;

      if (isGateExemptPath) {
        if (!ignore) setGateState({ checking: false, setupCompleted: true });
        return;
      }

      if (!ignore) setGateState((prev) => ({ ...prev, checking: true }));

      try {
        const res = await apiRequest('/api/v1/users/admin/parameter_settings/status/', { auth: true });
        if (ignore) return;

        if (res.status === 401) {
          setGateState({ checking: false, setupCompleted: true });
          return;
        }

        if (!res.ok) {
          // Fail open on status-check errors so admins are not locked out by a transient issue.
          setGateState({ checking: false, setupCompleted: true });
          return;
        }

        const setupCompleted = Boolean(res.data?.parameter_settings?.setup_completed);
        setGateState({ checking: false, setupCompleted });
      } catch (err) {
        console.error('Admin parameter gate check failed:', err);
        if (!ignore) setGateState({ checking: false, setupCompleted: true });
      }
    };

    checkParameterInit();
    return () => { ignore = true; };
  }, [loading, isAuthenticated, user?.role, isGateExemptPath]);

  if (loading) return <p>{t('guard.loading')}</p>;

  if (!isAuthenticated) {
    console.warn('[Guard] not authed -> /admin_login');
    return <Navigate to="/admin_login" replace state={{ from: location }} />;
  }
  if (user?.role !== 'admin') {
    console.warn('[Guard] wrong role -> /admin_login');
    return <Navigate to="/admin_login" replace />;
  }

  if (!isGateExemptPath && gateState.checking) {
    return <p>{t('guard.loading')}</p>;
  }

  if (!isGateExemptPath && !gateState.setupCompleted) {
    console.warn('[Guard] admin setup incomplete -> /admin_dashboard');
    return <Navigate to="/admin_dashboard" replace />;
  }

  console.log('[Guard] allow', location.pathname);
  return children;
}
export default AdminProtectedRoute;
