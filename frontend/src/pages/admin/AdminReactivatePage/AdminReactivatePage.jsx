import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import './AdminReactivatePage.css';

function AdminReactivatePage() {
  const { accessToken, logout } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState('loading'); // 'loading' | 'uncancel' | 'new_subscription' | 'none' | 'done' | 'error'
  const [plans, setPlans] = useState([]);
  const [selectedPriceId, setSelectedPriceId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // ✅ flip this on to force the plan picker while backend work continues
  const DEV_FORCE_REACTIVATE = false; // set to true during FE-only testing
  const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000';

  useEffect(() => {
    console.log('[AdminReactivatePage] mounted');
    let alive = true;

    if (DEV_FORCE_REACTIVATE) {
      setMode('new_subscription');
      const mockPlans = [
        { id: 'p_basic', name: 'Basic', display_name: 'Basic', price_id: 'price_basic', price_display: '$9.99/mo' },
        { id: 'p_pro',   name: 'Pro',   display_name: 'Pro',   price_id: 'price_pro',   price_display: '$19.99/mo' },
      ];
      setPlans(mockPlans);
      setSelectedPriceId(mockPlans[0].price_id);
      return () => { alive = false; };
    }

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/users/admin/reactivation/preview/`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });

        if (res.status === 401 || res.status === 403) {
          navigate('/admin_login');
          return;
        }

        const data = await res.json().catch(() => ({}));
        if (!alive) return;

        if (!res.ok) {
          setError(data?.error || 'Failed to load reactivation status.');
          setMode('error');
          return;
        }

        const nextMode = data.reactivation_mode || 'none';
        setMode(nextMode);
        setPlans(Array.isArray(data.plans) ? data.plans : []);

        if (nextMode === 'new_subscription') {
          if (data.plan_price_id) {
            setSelectedPriceId(data.plan_price_id);
          } else if (data.plans?.length) {
            setSelectedPriceId(data.plans[0].price_id);
          } else {
            setSelectedPriceId('');
          }
        }

        // ⛔️ No auto-navigate on 'none' — keep the user on this page
      } catch (e) {
        if (!alive) return;
        setError('Network error loading reactivation status.');
        setMode('error');
      }
    })();

    return () => { alive = false; };
  }, [API_BASE, accessToken, navigate, DEV_FORCE_REACTIVATE]);

  const handleReactivate = async () => {
    setLoading(true);
    setError(null);

    try {
      const needsPlan = mode === 'new_subscription';
      const body = needsPlan ? JSON.stringify({ target_price_id: selectedPriceId }) : null;

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
        window.location.href = data.url; // Stripe Checkout
        return;
      }

      // ✅ Stay on page and show success instead of navigating away
      setMode('done');
      setLoading(false);
    } catch (err) {
      setError('Network error.');
      setLoading(false);
    }
  };

  const disabled =
    loading ||
    mode === 'none' ||
    (mode === 'new_subscription' && !selectedPriceId);

  return (
    <div className="admin-reactivate-wrapper">
      <div className="admin-reactivate-card">
        <h2 className="admin-reactivate-title">🔄 Reactivate your admin subscription</h2>

        {mode === 'loading' && <p>Checking your subscription…</p>}

        {mode === 'error' && (
          <p className="admin-reactivate-error">{error || 'Unable to load reactivation info.'}</p>
        )}

        {mode === 'done' && (
          <p className="admin-reactivate-success">✅ Reactivation updated. You’re all set.</p>
        )}

        {/* if backend says 'none', keep the user here and show a simple message rather than auto-redirect */}
        {mode === 'none' && (
          <p className="admin-reactivate-hint">
            There’s nothing to change right now. You can pick a new plan below when available, or go back to settings.
          </p>
        )}

        {mode !== 'loading' && mode !== 'error' && mode !== 'done' && (
          <>
            <p className="admin-reactivate-description">
              {mode === 'uncancel'
                ? 'Your subscription is still active but set to end at the period’s end. Click below to keep it going.'
                : 'Select a plan to resume access. Trials are not available on reactivations.'}
            </p>

            {mode === 'new_subscription' && (
              <>
                <label className="admin-reactivate-label">Choose a plan:</label>
                {plans.length > 0 ? (
                  <select
                    value={selectedPriceId}
                    onChange={(e) => setSelectedPriceId(e.target.value)}
                    className="admin-reactivate-select"
                  >
                    {plans.map((plan) => (
                      <option key={plan.id} value={plan.price_id}>
                        {(plan.display_name || plan.name) + (plan.price_display ? ` – ${plan.price_display}` : '')}
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="admin-reactivate-hint">No plans available. Please contact support.</div>
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
                  : 'Reactivate plan'}
              </button>
            )}
          </>
        )}

        {error && mode !== 'error' && (
          <p className="admin-reactivate-error">{error}</p>
        )}

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
