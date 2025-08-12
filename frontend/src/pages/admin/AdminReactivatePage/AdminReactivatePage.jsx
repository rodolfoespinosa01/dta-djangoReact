import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import './AdminReactivatePage.css';

function AdminReactivatePage() {
  const { accessToken, logout } = useAuth();
  const navigate = useNavigate();

  // 'loading' | 'uncancel' | 'new_subscription' | 'none' | 'done' | 'error'
  const [mode, setMode] = useState('loading');
  const [plans, setPlans] = useState([]);
  const [selectedPriceId, setSelectedPriceId] = useState('');
  const [allowTrialForSelected, setAllowTrialForSelected] = useState(false);
  const [trialOptIn, setTrialOptIn] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const DEV_FORCE_REACTIVATE = false; // set true to test FE without backend
  const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000';

  // Derived: currently selected plan object
  const selectedPlan = useMemo(
    () => plans.find(p => p.price_id === selectedPriceId) || null,
    [plans, selectedPriceId]
  );

  useEffect(() => {
    let alive = true;

    const primeFromPlans = (arr) => {
      const normalized = (arr || []).map(p => ({
        id: p.id ?? p.name ?? p.stripe_price_id ?? p.price_id,
        name: p.name ?? p.display_name ?? 'Plan',
        display_name: p.display_name ?? p.name ?? 'Plan',
        price_id: p.price_id ?? p.stripe_price_id,        // backend field can be either
        price_display: p.price_display ?? p.pretty_price, // optional string "$19.99/mo"
        allow_trial: !!p.allow_trial,                     // boolean
        trial_days: p.trial_days ?? 0
      }));
      setPlans(normalized);
      if (normalized.length) {
        setSelectedPriceId(normalized[0].price_id);
        setAllowTrialForSelected(!!normalized[0].allow_trial);
        setTrialOptIn(false);
      } else {
        setSelectedPriceId('');
        setAllowTrialForSelected(false);
        setTrialOptIn(false);
      }
    };

    if (DEV_FORCE_REACTIVATE) {
      setMode('new_subscription');
      primeFromPlans([
        { id: 'adminMonthly', display_name: 'Monthly', price_id: 'price_month', price_display: '$19/mo', allow_trial: true, trial_days: 7 },
        { id: 'adminQuarterly', display_name: 'Quarterly', price_id: 'price_quarter', price_display: '$49/qtr', allow_trial: true, trial_days: 7 },
        { id: 'adminAnnual', display_name: 'Annual', price_id: 'price_year', price_display: '$179/yr', allow_trial: false }
      ]);
      return () => { alive = false; };
    }

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/users/admin/reactivation/preview/`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });

        if (res.status === 401 || res.status === 403) { navigate('/admin_login'); return; }

        const data = await res.json().catch(() => ({}));
        if (!alive) return;

        if (!res.ok) {
          setError(data?.error || 'Failed to load reactivation status.');
          setMode('error');
          return;
        }

        // Expected from backend:
        // {
        //   reactivation_mode: 'uncancel' | 'new_subscription' | 'none',
        //   plans: [{ price_id, display_name, price_display, allow_trial, trial_days }, ...],
        //   reason: 'canceled' | 'trial_expired' | 'scheduled_cancel' | 'active'
        // }
        const nextMode = data.reactivation_mode || 'none';
        setMode(nextMode);
        primeFromPlans(data.plans);

      } catch {
        if (!alive) return;
        setError('Network error loading reactivation status.');
        setMode('error');
      }
    })();

    return () => { alive = false; };
  }, [API_BASE, accessToken, navigate, DEV_FORCE_REACTIVATE]);

  // Keep trial checkbox availability in sync with selection
  useEffect(() => {
    if (!selectedPlan) { setAllowTrialForSelected(false); setTrialOptIn(false); return; }
    setAllowTrialForSelected(!!selectedPlan.allow_trial);
    if (!selectedPlan.allow_trial) setTrialOptIn(false);
  }, [selectedPlan]);

  const handleReactivate = async () => {
    setLoading(true);
    setError(null);

    try {
      const body = (mode === 'new_subscription')
        ? JSON.stringify({
            target_price_id: selectedPriceId,
            with_trial: !!trialOptIn // backend decides eligibility; FE just requests
          })
        : null;

      const res = await fetch(`${API_BASE}/api/users/admin/reactivation/start/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          ...(body ? { 'Content-Type': 'application/json' } : {}),
        },
        body,
      });

      if (res.status === 401 || res.status === 403) { navigate('/admin_login'); return; }

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        setError(data?.error || 'Something went wrong.');
        setLoading(false);
        return;
      }

      // Backend responses:
      // { action: 'checkout', url: 'https://checkout.stripe.com/...' }
      // { action: 'uncancelled' }  (kept current plan)
      // { action: 'provisioned' }  (no checkout needed)
      if (data.action === 'checkout' && data.url) {
        window.location.href = data.url;
        return;
      }

      setMode('done');
      setLoading(false);
    } catch {
      setError('Network error.');
      setLoading(false);
    }
  };

  const disabled = loading || mode === 'none' || (mode === 'new_subscription' && !selectedPriceId);

  return (
    <div className="admin-reactivate-wrapper">
      <div className="admin-reactivate-card">
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
                ? 'Your subscription will end at period’s end. Keep it going below.'
                : 'Pick a plan to resume access. If eligible, you can start with a trial.'}
            </p>

            {/* Plans */}
            {mode === 'new_subscription' && (
              <>
                {plans.length === 0 && (
                  <div className="admin-reactivate-hint">No plans available. Please contact support.</div>
                )}

                {plans.length > 0 && (
                  <div className="plan-grid">
                    {plans.map((plan) => {
                      const active = selectedPriceId === plan.price_id;
                      return (
                        <button
                          key={plan.price_id}
                          type="button"
                          className={`plan-card ${active ? 'active' : ''}`}
                          onClick={() => setSelectedPriceId(plan.price_id)}
                        >
                          <div className="plan-name">{plan.display_name || plan.name}</div>
                          {plan.price_display && <div className="plan-price">{plan.price_display}</div>}
                          {plan.allow_trial ? (
                            <div className="plan-trial">Trial available{plan.trial_days ? ` • ${plan.trial_days} days` : ''}</div>
                          ) : (
                            <div className="plan-trial-disabled">No trial</div>
                          )}
                        </button>
                      );
                    })}
                  </div>
                )}

                {/* Trial toggle (only if selected plan supports it) */}
                {allowTrialForSelected && (
                  <label className="trial-toggle">
                    <input
                      type="checkbox"
                      checked={trialOptIn}
                      onChange={(e) => setTrialOptIn(e.target.checked)}
                    />
                    <span>Start with trial{selectedPlan?.trial_days ? ` (${selectedPlan.trial_days} days)` : ''}</span>
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
                  ? 'Keep my current plan'
                  : allowTrialForSelected && trialOptIn
                  ? 'Start free trial'
                  : 'Reactivate plan'}
              </button>
            )}

            {mode === 'none' && (
              <p className="admin-reactivate-hint">
                There’s nothing to change right now. If you canceled previously, pick a plan above to reactivate.
              </p>
            )}
          </>
        )}

        {error && mode !== 'error' && <p className="admin-reactivate-error">{error}</p>}

        <div className="admin-reactivate-footer">
          <button type="button" onClick={() => navigate('/admin_settings')} className="admin-reactivate-settings-btn">
            Back to settings
          </button>
          <button type="button" onClick={() => logout()} className="admin-reactivate-logout-btn">
            Log out
          </button>
        </div>
      </div>
    </div>
  );
}

export default AdminReactivatePage;
