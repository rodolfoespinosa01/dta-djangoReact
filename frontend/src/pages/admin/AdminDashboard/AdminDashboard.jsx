import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import { useLanguage } from '../../../context/LanguageContext';
import { apiRequest } from '../../../api/client';
import './AdminDashboard.css';

function AdminDashboard() {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const { t } = useLanguage();

  const [dashboardData, setDashboardData] = useState(null);
  const [status, setStatus] = useState('loading'); // 'loading' | 'ok' | 'blocked' | 'error'

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/admin_login');
      return;
    }

    const fetchDashboard = async () => {
      try {
        const { status: resStatus, ok: resOk, data } = await apiRequest('/api/v1/users/admin/dashboard/', { auth: true });

        if (resStatus === 401) { navigate('/admin_login'); return; }
        if (resStatus === 403 || resStatus === 404) { setStatus('blocked'); return; }

        if (resOk && data) {
          setDashboardData(data);
          setStatus('ok');
        } else {
          setStatus('error');
        }
      } catch (err) {
        console.error('Error loading dashboard data:', err);
        setStatus('error');
      }
    };

    fetchDashboard();
  }, [isAuthenticated, navigate]);

  return (
    <div className="admin-dashboard-wrapper">
      <h1 className="admin-dashboard-title">🎯 {t('admin_dashboard.title')}</h1>
      <p className="admin-dashboard-subtitle">{t('admin_dashboard.subtitle')}</p>

      {status === 'loading' && (
        <p className="loading">{t('admin_dashboard.loading')}</p>
      )}

      {status === 'blocked' && (
        <div className="banner banner-canceled">
          <p>⚠️ {t('admin_dashboard.plan_inactive')}</p>
          <p>{t('admin_dashboard.trial_ended')}</p>
          <button className="btn btn-reactivate" onClick={() => navigate('/admin_reactivate')}>
            🔁 {t('admin_dashboard.reactivate')}
          </button>
        </div>
      )}

      {status === 'ok' && dashboardData && (
        <div className="admin-dashboard-card">
          {dashboardData.is_active ? (
            <p className="badge badge-active">✅ {t('admin_dashboard.account_active')}</p>
          ) : (
            <p className="error">⚠️ {t('admin_dashboard.account_inactive')}</p>
          )}

          {/* Safety: if API returned ok but user has no access (edge), show reactivation banner */}
          {dashboardData.is_active === false && (
            <div className="banner banner-canceled">
              <p>⚠️ {t('admin_dashboard.account_inactive')}</p>
              <button className="btn btn-reactivate" onClick={() => navigate('/admin_reactivate')}>
                🔁 {t('admin_dashboard.reactivate')}
              </button>
            </div>
          )}
        </div>
      )}

      {status === 'error' && (
        <p className="error">{t('admin_dashboard.error_loading')}</p>
      )}

      <div className="actions">
        <button onClick={() => navigate('/admin_settings')} className="btn btn-primary">
          ⚙️ {t('admin_dashboard.account_settings')}
        </button>
        <button onClick={() => logout()} className="btn btn-danger">
          🚪 {t('common.logout')}
        </button>
      </div>
    </div>
  );
}

export default AdminDashboard;
