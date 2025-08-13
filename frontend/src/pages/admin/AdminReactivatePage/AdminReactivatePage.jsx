import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import './AdminReactivatePage.css';

function AdminReactivatePage() {
  const { accessToken, logout } = useAuth();
  const navigate = useNavigate();

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
          setError(data?.error || 'Failed to load reactivation status.');
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
        setError('Network error loading reactivation status.');
      }
    })();

    return () => { alive = false; };
  }, [API_BASE, accessToken, navigate]);

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
        setError(data?.error || 'Something went wrong.');
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
      setError('Network error.');
      setLoading(false);
    }
  };

  const disabled = loading
    || mode === 'none'
    || ((mode === 'new_subscription' || mode === 'uncancel') && !selectedPriceId);

  return (
    <div className="admin-reactivate-wrapper">
      <div className="admin-reactivate-card" role="region" aria-label="Reactivate subscription">
        <h2 className="admin-reactivate-title">🔄 Reactivate your admin subscription</h2>

        {mode === 'loading' && <p>Checking your subscription…</p>}

        {mode === 'error' && (
          <p className="admin-reactivate-error">{error || 'Unable to load reactivation info.'}</p>
        )}

        {mode === 'done' && (
          <p className="admin-reactivate-success">✅ You’re all set. Thanks for reactivating!</p>
        )}

        {mode !== 'loading' && mode !== 'error' && mode !== 'done' && (
          <>
            <p className="admin-reactivate-description">
              {mode === 'uncancel'
                ? 'Your subscription is set to end at the period’s end. Keep it going or upgrade below.'
                : mode === 'new_subscription'
                ? 'Pick a plan to resume access. If eligible, you can start with a trial.'
                : 'There’s nothing to change right now.'}
            </p>

            {(mode === 'new_subscription' || mode === 'uncancel') && (
              <>
                {plans.length === 0 && (
                  <div className="admin-reactivate-hint">No plans available. Please contact support.</div>
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
                            {isCurrent && <span className="plan-badge">Current</span>}
                          </div>
                          {plan.price_display && (
                            <div className="plan-price">{plan.price_display}</div>
                          )}
                          {plan.allow_trial ? (
                            <div className="plan-trial">
                              Trial available{plan.trial_days ? ` • ${plan.trial_days} days` : ''}
                            </div>
                          ) : (
                            <div className="plan-trial-disabled">No trial</div>
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
                      Start with trial
                      {selectedPlan?.trial_days ? ` (${selectedPlan.trial_days} days)` : ''}
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
                  ? 'Redirecting…'
                  : mode === 'uncancel'
                  ? (selectedPriceId && selectedPriceId !== currentPriceId ? 'Upgrade plan' : 'Keep my current plan')
                  : allowTrialForSelected && trialOptIn
                  ? 'Start free trial'
                  : 'Reactivate plan'}
              </button>
            )}

            {mode === 'none' && (
              <p className="admin-reactivate-hint">
                You’re active and not canceling. If you canceled previously, plans will appear here.
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
            Back to settings
          </button>
          <button onClick={() => logout()} className="btn btn-danger">
          🚪 Logout
        </button>
        </div>
      </div>
    </div>
  );
}

export default AdminReactivatePage;
