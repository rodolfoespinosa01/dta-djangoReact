import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import { useLanguage } from '../../../context/LanguageContext';
import { apiRequest } from '../../../api/client';
import './AdminDashboard.css';

const SUBDOMAIN_RE = /^[a-z]+(?:-[a-z]+)*$/;

function normalizeSubdomain(value) {
  return String(value || '').trim().toLowerCase().replace(/\s+/g, '');
}

function validateSubdomainSlug(value) {
  const slug = normalizeSubdomain(value);
  if (!slug) return 'Subdomain is required.';
  if (slug.length < 3 || slug.length > 40) return 'Subdomain must be between 3 and 40 characters.';
  if (!SUBDOMAIN_RE.test(slug)) return 'Use only letters and hyphens.';
  return '';
}

function AdminDashboard() {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const { t } = useLanguage();

  const [dashboardData, setDashboardData] = useState(null);
  const [status, setStatus] = useState('loading'); // 'loading' | 'ok' | 'blocked' | 'error'
  const [paramStatus, setParamStatus] = useState({
    loading: true,
    initialized: true,
    setupCompleted: true,
    subdomain: null,
    error: '',
  });
  const [applyingDefaults, setApplyingDefaults] = useState(false);
  const [paramMessage, setParamMessage] = useState('');
  const [subdomainInput, setSubdomainInput] = useState('');
  const [subdomainError, setSubdomainError] = useState('');
  const isParamSetupRequired = status === 'ok' && !paramStatus.loading && !paramStatus.setupCompleted;
  const normalizedSubdomain = normalizeSubdomain(subdomainInput);

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
            setParamStatus({
              loading: false,
              initialized: true,
              setupCompleted: true,
              subdomain: null,
              error: 'Could not check parameter settings.',
            });
            return;
          }
          const settingsStatus = paramRes.data?.parameter_settings || {};
          const subdomain = paramRes.data?.subdomain || null;
          const initialized = Boolean(settingsStatus.initialized);
          const setupCompleted = Boolean(settingsStatus.setup_completed);
          setParamStatus({ loading: false, initialized, setupCompleted, subdomain, error: '' });
          setSubdomainInput(subdomain?.slug || '');
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
        body: {
          subdomain_slug: normalizedSubdomain,
        },
      });
      if (res.status === 401) {
        navigate('/admin_login');
        return;
      }
      if (!res.ok) {
        const apiMessage = res.data?.error?.message || 'Unable to apply DTA defaults.';
        setParamMessage(apiMessage);
        if ((res.data?.error?.code || '') === 'INVALID_SUBDOMAIN_SLUG') {
          setSubdomainError(apiMessage);
        }
        return;
      }
      const nextSubdomain = res.data?.subdomain || { slug: normalizedSubdomain };
      setParamStatus({
        loading: false,
        initialized: true,
        setupCompleted: Boolean(res.data?.parameter_settings?.setup_completed),
        subdomain: nextSubdomain,
        error: '',
      });
      setSubdomainInput(nextSubdomain?.slug || normalizedSubdomain);
      setSubdomainError('');
      setParamMessage('DTA defaults applied. You can edit parameters later anytime.');
    } catch (err) {
      console.error('Error applying parameter defaults:', err);
      setParamMessage('Network error while applying DTA defaults.');
    } finally {
      setApplyingDefaults(false);
    }
  };

  const handleSubdomainChange = (value) => {
    const next = normalizeSubdomain(value);
    setSubdomainInput(next);
    if (subdomainError) {
      setSubdomainError(validateSubdomainSlug(next));
    }
  };

  const currentSubdomainLocked = Boolean(paramStatus.subdomain?.locked);
  const effectiveSubdomainError = currentSubdomainLocked ? '' : (subdomainError || validateSubdomainSlug(subdomainInput));
  const canProceedWithSetup = currentSubdomainLocked || !effectiveSubdomainError;

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

          {!paramStatus.loading && paramStatus.initialized && paramMessage && (
            <p className="banner-setup-message success-inline">{paramMessage}</p>
          )}
          {!!paramStatus.error && (
            <p className="banner-setup-message">{paramStatus.error}</p>
          )}
          {!!paramStatus.subdomain?.slug && (
            <div className="admin-subdomain-summary" aria-label="Your admin subdomain">
              <p className="admin-subdomain-summary-label">Your DTA Link</p>
              <p className="admin-subdomain-summary-value">
                {paramStatus.subdomain.slug}.dtameals.com
              </p>
              <p className="admin-subdomain-summary-dev">
                Dev: {paramStatus.subdomain.slug}.lvh.me:3000
              </p>
            </div>
          )}
        </div>
      )}

      {status === 'error' && (
        <p className="error">{t('admin_dashboard.error_loading')}</p>
      )}

      {!isParamSetupRequired && (
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
      )}

      {isParamSetupRequired && (
        <div className="admin-setup-modal-backdrop" role="presentation">
          <div
            className="admin-setup-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="admin-setup-modal-title"
          >
            <h2 id="admin-setup-modal-title" className="admin-setup-modal-title">
              Admin Parameter Settings Required
            </h2>
            <p className="admin-setup-modal-text">
              Before moving forward in your dashboard, you must acknowledge your admin parameter settings and set your subdomain.
              Choose DTA defaults or go to the parameter editor to set your own values.
            </p>
            <p className="admin-setup-modal-note">
              This is required before continuing. If you log out and come back, you will be prompted again until completed.
            </p>

            <div className="admin-setup-modal-subdomain">
              <label htmlFor="admin-subdomain-input">Choose your subdomain (one time only)</label>
              <div className="admin-setup-subdomain-row">
                <input
                  id="admin-subdomain-input"
                  type="text"
                  value={subdomainInput}
                  onChange={(e) => handleSubdomainChange(e.target.value)}
                  placeholder="coachmike"
                  disabled={currentSubdomainLocked || applyingDefaults}
                  autoComplete="off"
                />
                <span className="admin-setup-subdomain-suffix">.lvh.me:3000</span>
              </div>
              <p className="admin-setup-modal-preview">
                Dev preview: {normalizedSubdomain ? `${normalizedSubdomain}.lvh.me:3000` : '—'}
              </p>
              <p className="admin-setup-modal-preview">
                Production: {normalizedSubdomain ? `${normalizedSubdomain}.dtameals.com` : '—'}
              </p>
              {effectiveSubdomainError && (
                <p className="admin-params-error">{effectiveSubdomainError}</p>
              )}
              {currentSubdomainLocked && (
                <p className="admin-params-success">Subdomain locked: {paramStatus.subdomain?.slug}.dtameals.com</p>
              )}
            </div>

            <div className="admin-setup-modal-actions">
              <button className="btn btn-primary" onClick={handleUseDefaults} disabled={applyingDefaults || !canProceedWithSetup}>
                {applyingDefaults ? 'Applying Defaults…' : 'Use DTA Defaults'}
              </button>
              <button
                className="btn btn-outline"
                onClick={() => navigate('/admin_parameter_settings', { state: { suggestedSubdomain: normalizedSubdomain } })}
                disabled={applyingDefaults || !canProceedWithSetup}
              >
                Go to Edit Parameters
              </button>
              <button className="btn btn-danger" onClick={() => logout()} disabled={applyingDefaults}>
                Log Out
              </button>
            </div>

            {paramMessage && (
              <p className={paramMessage.toLowerCase().includes('unable') || paramMessage.toLowerCase().includes('error') ? 'admin-params-error' : 'admin-params-success'}>
                {paramMessage}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminDashboard;
