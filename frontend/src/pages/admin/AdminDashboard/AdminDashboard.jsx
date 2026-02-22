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
  const [paramStatus, setParamStatus] = useState({ loading: true, initialized: true, error: '' });
  const [applyingDefaults, setApplyingDefaults] = useState(false);
  const [paramMessage, setParamMessage] = useState('');

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

          const paramRes = await apiRequest('/api/v1/users/admin/parameter_settings/status/', { auth: true });
          if (paramRes.status === 401) { navigate('/admin_login'); return; }
          if (!paramRes.ok) {
            setParamStatus({ loading: false, initialized: true, error: 'Could not check parameter settings.' });
            return;
          }
          const initialized = Boolean(paramRes.data?.parameter_settings?.initialized);
          setParamStatus({ loading: false, initialized, error: '' });
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

  const handleUseDefaults = async () => {
    try {
      setApplyingDefaults(true);
      setParamMessage('');
      const res = await apiRequest('/api/v1/users/admin/parameter_settings/use_defaults/', {
        method: 'POST',
        auth: true,
      });
      if (res.status === 401) {
        navigate('/admin_login');
        return;
      }
      if (!res.ok) {
        setParamMessage(res.data?.error?.message || 'Unable to apply DTA defaults.');
        return;
      }
      setParamStatus({ loading: false, initialized: true, error: '' });
      setParamMessage('DTA defaults applied. You can edit parameters later anytime.');
    } catch (err) {
      console.error('Error applying parameter defaults:', err);
      setParamMessage('Network error while applying DTA defaults.');
    } finally {
      setApplyingDefaults(false);
    }
  };

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

          {!paramStatus.loading && !paramStatus.initialized && (
            <div className="banner banner-setup">
              <p className="banner-setup-title">Admin Parameter Settings Required</p>
              <p>
                Before you start building client plans, set your admin parameter defaults.
                You can use DTA defaults now or open the parameter editor and customize everything.
              </p>
              <div className="banner-setup-actions">
                <button className="btn btn-primary" onClick={handleUseDefaults} disabled={applyingDefaults}>
                  {applyingDefaults ? 'Applying Defaults…' : 'Use DTA Defaults'}
                </button>
                <button className="btn btn-outline" onClick={() => navigate('/admin_parameter_settings')}>
                  Go to Edit Parameters
                </button>
              </div>
              {paramMessage && <p className="banner-setup-message">{paramMessage}</p>}
            </div>
          )}

          {!paramStatus.loading && paramStatus.initialized && paramMessage && (
            <p className="banner-setup-message success-inline">{paramMessage}</p>
          )}
          {!!paramStatus.error && (
            <p className="banner-setup-message">{paramStatus.error}</p>
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
        <button onClick={() => navigate('/admin_parameter_settings')} className="btn btn-outline">
          🧮 Admin Parameters
        </button>
        <button onClick={() => logout()} className="btn btn-danger">
          🚪 {t('common.logout')}
        </button>
      </div>
    </div>
  );
}

export default AdminDashboard;
