import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import { useLanguage } from '../../../context/LanguageContext';
import './AdminReactivatePage.css';

function AdminReactivatePage() {
  const { accessToken, logout } = useAuth();
  const navigate = useNavigate();
  const { t } = useLanguage();

  // 'loading' | 'uncancel' | 'new_subscription' | 'none' | 'done' | 'error'
  const [mode, setMode] = useState('loading');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const [plans, setPlans] = useState([]); // [{price_id, display_name, price_display, allow_trial, trial_days}]
  const [selectedPriceId, setSelectedPriceId] = useState('');
  const [currentPriceId, setCurrentPriceId] = useState(null);

  const [allowTrialForSelected, setAllowTrialForSelected] = useState(false);
  const [trialOptIn, setTrialOptIn] = useState(false);

  const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000';

  const selectedPlan = useMemo(
    () => plans.find(p => p.price_id === selectedPriceId) || null,
    [plans, selectedPriceId]
  );

  // Fetch preview
  useEffect(() => {
    let alive = true;

    const normalizePlans = (arr) =>
      (arr || []).map(p => ({
        price_id: p.price_id,
        display_name: p.display_name || p.name || 'Plan',
        price_display: p.price_display || null,
        allow_trial: !!p.allow_trial,
        trial_days: p.trial_days || 0,
      }));

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/users/admin/reactivation/preview/`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });

        if (res.status === 401 || res.status === 403) {
          navigate('/admin_login');
          return;
        }

        const data = await res.json();
        if (!alive) return;

        if (!res.ok) {
          setMode('error');
          setError(data?.error || t('admin_reactivate.unable_load'));
          return;
        }

        const nextMode = data?.reactivation_mode || 'none';
        setMode(nextMode);

        const normalized = normalizePlans(data?.plans || []);
        setPlans(normalized);

        // Preselect: current plan if present; otherwise first plan
        const current = data?.current_price_id || null;
        setCurrentPriceId(current);

        if (normalized.length) {
          const defaultChoice =
            (nextMode === 'uncancel' && current && normalized.some(p => p.price_id === current))
              ? current
              : normalized[0].price_id;

          setSelectedPriceId(defaultChoice);
          const defaultPlan = normalized.find(p => p.price_id === defaultChoice);
          setAllowTrialForSelected(!!defaultPlan?.allow_trial);
          setTrialOptIn(false);
        } else {
          setSelectedPriceId('');
          setAllowTrialForSelected(false);
          setTrialOptIn(false);
        }
      } catch {
        if (!alive) return;
        setMode('error');
        setError(t('admin_reactivate.network'));
      }
    })();

    return () => { alive = false; };
  }, [API_BASE, accessToken, navigate, t]);

  // Keep trial checkbox in sync with selected plan
  useEffect(() => {
    if (!selectedPlan) {
      setAllowTrialForSelected(false);
      setTrialOptIn(false);
      return;
    }
    setAllowTrialForSelected(!!selectedPlan.allow_trial);
    if (!selectedPlan.allow_trial) setTrialOptIn(false);
  }, [selectedPlan]);

  const handleReactivate = async () => {
    setLoading(true);
    setError(null);

    try {
      const isUpgradeWhileUncancel = (mode === 'uncancel' && selectedPriceId && selectedPriceId !== currentPriceId);
      const isNewSub = (mode === 'new_subscription');
      const wantsCheckout = isNewSub || isUpgradeWhileUncancel;

      const body = wantsCheckout
        ? JSON.stringify({ target_price_id: selectedPriceId, with_trial: !!trialOptIn })
        : null;

      const res = await fetch(`${API_BASE}/api/users/admin/reactivation/start/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          ...(body ? { 'Content-Type': 'application/json' } : {}),
        },
        body,
      });

      if (res.status === 401 || res.status === 403) {
        navigate('/admin_login');
        return;
      }

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        setError(data?.error || t('admin_plan.generic_error'));
        setLoading(false);
        return;
      }

      if (data.action === 'checkout' && data.url) {
        window.location.href = data.url;
        return; // browser navigating
      }

      setMode('done');
      setLoading(false);
    } catch {
      setError(t('admin_reactivate.network'));
      setLoading(false);
    }
  };

  const disabled = loading
    || mode === 'none'
    || ((mode === 'new_subscription' || mode === 'uncancel') && !selectedPriceId);

  return (
    <div className="admin-reactivate-wrapper">
      <div className="admin-reactivate-card" role="region" aria-label={t('admin_reactivate.region_label')}>
        <h2 className="admin-reactivate-title">🔄 {t('admin_reactivate.title')}</h2>

        {mode === 'loading' && <p>{t('admin_reactivate.checking')}</p>}

        {mode === 'error' && (
          <p className="admin-reactivate-error">{error || t('admin_reactivate.unable_load')}</p>
        )}

        {mode === 'done' && (
          <p className="admin-reactivate-success">✅ {t('admin_reactivate.success')}</p>
        )}

        {mode !== 'loading' && mode !== 'error' && mode !== 'done' && (
          <>
            <p className="admin-reactivate-description">
              {mode === 'uncancel'
                ? t('admin_reactivate.desc_uncancel')
                : mode === 'new_subscription'
                ? t('admin_reactivate.desc_new')
                : t('admin_reactivate.desc_none')}
            </p>

            {(mode === 'new_subscription' || mode === 'uncancel') && (
              <>
                {plans.length === 0 && (
                  <div className="admin-reactivate-hint">{t('admin_reactivate.no_plans')}</div>
                )}

                {plans.length > 0 && (
                  <div className="plan-grid" role="list">
                    {plans.map((plan) => {
                      const active = selectedPriceId === plan.price_id;
                      const isCurrent = currentPriceId && plan.price_id === currentPriceId;

                      return (
                        <button
                          key={plan.price_id}
                          type="button"
                          role="listitem"
                          className={`plan-card ${active ? 'active' : ''}`}
                          aria-pressed={active}
                          onClick={() => setSelectedPriceId(plan.price_id)}
                        >
                          <div className="plan-name">
                            {plan.display_name}
                            {isCurrent && <span className="plan-badge">{t('admin_reactivate.current')}</span>}
                          </div>
                          {plan.price_display && (
                            <div className="plan-price">{plan.price_display}</div>
                          )}
                          {plan.allow_trial ? (
                            <div className="plan-trial">
                              {t('admin_reactivate.trial_available')}
                              {plan.trial_days ? ` • ${plan.trial_days} ${t('admin_reactivate.days')}` : ''}
                            </div>
                          ) : (
                            <div className="plan-trial-disabled">{t('admin_reactivate.no_trial')}</div>
                          )}
                        </button>
                      );
                    })}
                  </div>
                )}

                {/* Trial toggle */}
                {allowTrialForSelected && (
                  <label className="trial-toggle">
                    <input
                      type="checkbox"
                      checked={trialOptIn}
                      onChange={(e) => setTrialOptIn(e.target.checked)}
                    />
                    <span>
                      {t('admin_reactivate.start_with_trial')}
                      {selectedPlan?.trial_days ? ` (${selectedPlan.trial_days} ${t('admin_reactivate.days')})` : ''}
                    </span>
                  </label>
                )}
              </>
            )}

            {(mode === 'uncancel' || mode === 'new_subscription') && (
              <button
                type="button"
                onClick={handleReactivate}
                disabled={disabled}
                className="admin-reactivate-button"
              >
                {loading
                  ? t('admin_reactivate.redirecting')
                  : mode === 'uncancel'
                  ? (selectedPriceId && selectedPriceId !== currentPriceId ? t('admin_reactivate.upgrade_plan') : t('admin_reactivate.keep_current'))
                  : allowTrialForSelected && trialOptIn
                  ? t('admin_reactivate.start_free_trial')
                  : t('admin_reactivate.reactivate_plan')}
              </button>
            )}

            {mode === 'none' && (
              <p className="admin-reactivate-hint">
                {t('admin_reactivate.hint_none')}
              </p>
            )}
          </>
        )}

        {error && mode !== 'error' && <p className="admin-reactivate-error">{error}</p>}

        <div className="admin-reactivate-footer">
          <button
            type="button"
            onClick={() => navigate('/admin_settings')}
            className="admin-reactivate-settings-btn"
          >
            {t('admin_reactivate.back_settings')}
          </button>
          <button onClick={() => logout()} className="btn btn-danger">
          🚪 {t('common.logout')}
        </button>
        </div>
      </div>
    </div>
  );
}

export default AdminReactivatePage;
