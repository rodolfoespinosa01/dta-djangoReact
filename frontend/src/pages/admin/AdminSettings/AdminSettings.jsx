import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import './AdminSettings.css';

function AdminSettings() {
  const { user, isAuthenticated, accessToken } = useAuth();
  const navigate = useNavigate();

  const [dashboardData, setDashboardData] = useState(null);
  const [paymentMethod, setPaymentMethod] = useState(null);
  const [planPriceMap, setPlanPriceMap] = useState({});
  const [message, setMessage] = useState('');
  const [loadingAction, setLoadingAction] = useState(null); // 'cancel' | 'upgrade' | 'downgrade' | null

  // modal for plan selection
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTitle, setModalTitle] = useState('');
  const [modalOptions, setModalOptions] = useState([]); // [{label, value, action:'upgrade'|'downgrade'}]
  const [modalRequireAcknowledge, setModalRequireAcknowledge] = useState(false);
  const [selectedModalOption, setSelectedModalOption] = useState(null);
  const [acknowledgePlanChange, setAcknowledgePlanChange] = useState(false);

  // ---------- helpers ----------
  const authHeaders = () => ({
    Authorization: `Bearer ${accessToken}`,
    'Content-Type': 'application/json',
  });

  const extractError = async (res) => {
    try {
      const data = await res.json();
      const payload = data?.detail && typeof data.detail === 'object' ? data.detail : data;
      return payload?.error || payload?.message || 'request failed.';
    } catch {
      return 'request failed.';
    }
  };

  const isAuthedGuard = (res) => {
    if (res.status === 401 || res.status === 403) {
      navigate('/admin_login');
      return false;
    }
    return true;
  };

  const updateFromSnapshot = (payload, fallbackMsg = 'ok') => {
    if (!payload) return;
    const { snapshot, message } = payload;
    if (snapshot) setDashboardData(snapshot);
    setMessage(message || fallbackMsg);
  };

  const formatDate = (str) => (str ? new Date(str).toLocaleDateString() : '—');
  const formatAmount = (cents) => (typeof cents === 'number' ? `$${(cents / 100).toFixed(2)}` : '—');
  const daysUntil = (str) => {
    if (!str) return null;
    const end = new Date(str);
    const now = new Date();
    const ms = end.getTime() - now.getTime();
    if (Number.isNaN(ms)) return null;
    return Math.max(Math.ceil(ms / (1000 * 60 * 60 * 24)), 0);
  };

  const subscriptionLabels = {
    admin_trial: 'Free Trial',
    admin_monthly: 'Monthly Plan',
    admin_quarterly: 'Quarterly Plan',
    admin_annual: 'Annual Plan',
  };

  const toPlanKeyFromDisplay = (displayName = '') => {
    const v = displayName.toLowerCase();
    if (v.includes('monthly')) return 'admin_monthly';
    if (v.includes('quarterly')) return 'admin_quarterly';
    if (v.includes('annual')) return 'admin_annual';
    return null;
  };

  // ---------- initial load ----------
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/admin_login');
      return;
    }

    let ignore = false;

    const fetchDashboard = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/users/admin/dashboard/', {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (!isAuthedGuard(res)) return;
        const data = await res.json();
        if (!ignore && res.ok) setDashboardData(data);
      } catch (err) {
        console.error('error fetching dashboard:', err);
      }
    };

    const fetchPlanMap = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/users/admin/reactivation/preview/', {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (!isAuthedGuard(res)) return;
        const data = await res.json();
        if (!ignore && res.ok && Array.isArray(data.plans)) {
          const map = {};
          data.plans.forEach((p) => {
            const key = toPlanKeyFromDisplay(p.display_name);
            if (key && p.price_id) map[key] = p.price_id;
          });
          setPlanPriceMap(map);
        }
      } catch (err) {
        console.error('error fetching plan map:', err);
      }
    };

    const fetchPaymentMethod = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/users/admin/payment_method/', {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (!isAuthedGuard(res)) return;
        const data = await res.json();
        if (!ignore && res.ok) setPaymentMethod(data);
      } catch (err) {
        console.error('error fetching payment method:', err);
      }
    };

    fetchDashboard();
    fetchPlanMap();
    fetchPaymentMethod();
    return () => { ignore = true; };
  }, [accessToken, isAuthenticated, navigate]);

  const openPlanModal = (title, options, requireAcknowledge = false) => {
    setModalTitle(title);
    setModalOptions(options);
    setModalRequireAcknowledge(requireAcknowledge);
    setSelectedModalOption(null);
    setAcknowledgePlanChange(false);
    setModalOpen(true);
  };

  // ---------- actions ----------
  const handleCancel = async () => {
    if (!dashboardData) return;
    const canCancel = dashboardData.subscription_active && !dashboardData.is_canceled;
    if (!canCancel) {
      setMessage('Nothing to cancel.');
      return;
    }

    try {
      setLoadingAction('cancel');
      setMessage('');
      const res = await fetch('http://localhost:8000/api/users/admin/cancel_subscription/', {
        method: 'POST',
        headers: authHeaders(),
      });
      if (!isAuthedGuard(res)) return;

      if (res.ok) {
        const payload = await res.json();
        updateFromSnapshot(payload, 'auto-renew canceled');
      } else {
        setMessage(await extractError(res));
      }
    } catch (err) {
      console.error('cancel error:', err);
      setMessage('network error.');
    } finally {
      setLoadingAction(null);
    }
  };

  // Stripe checkout creator (used for upgrades that require payment)
  const startCheckout = async (target_plan) => {
    try {
      setLoadingAction('upgrade');
      setMessage('');
      const targetPriceId = planPriceMap[target_plan];
      if (!targetPriceId) {
        setMessage('Could not resolve plan pricing. Refresh and try again.');
        return;
      }

      const res = await fetch('http://localhost:8000/api/users/admin/reactivation/start/', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ target_price_id: targetPriceId, with_trial: false }),
      });
      if (!isAuthedGuard(res)) return;

      if (res.ok) {
        const { action, url, error: errMsg } = await res.json();
        if (action === 'checkout' && url) {
          setMessage('redirecting to checkout…');
          window.location.assign(url);
          return;
        }
        setMessage(errMsg || 'Could not start checkout.');
        // Redirect to Stripe
      } else {
        setMessage(await extractError(res));
      }
    } catch (err) {
      console.error('checkout error:', err);
      setMessage('network error.');
    } finally {
      setLoadingAction(null);
      setModalOpen(false);
    }
  };

  // Plan change path uses the authenticated reactivation checkout flow.
  const changePlan = async (target_plan) => {
    try {
      setLoadingAction('downgrade');
      setMessage('');
      const res = await fetch('http://localhost:8000/api/users/admin/change_subscription/', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ target_plan }),
      });
      if (!isAuthedGuard(res)) return;

      const payload = await res.json().catch(() => ({}));
      if (res.ok) {
        setMessage(payload.message || 'Plan change scheduled for next billing cycle.');
        const refreshed = await fetch('http://localhost:8000/api/users/admin/dashboard/', {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (refreshed.ok) {
          const data = await refreshed.json();
          setDashboardData(data);
        }
      } else {
        setMessage(payload.error || 'Could not schedule plan change.');
      }
    } catch (err) {
      console.error('change plan error:', err);
      setMessage('network error.');
    } finally {
      setLoadingAction(null);
      setModalOpen(false);
      setSelectedModalOption(null);
      setAcknowledgePlanChange(false);
    }
  };

  // ---------- button handlers per your rules ----------
  const onUpgradeClick = () => {
    if (!dashboardData) return;
    const { subscription_status } = dashboardData;

    if (subscription_status === 'admin_trial') {
      openPlanModal('Choose your upgrade plan', [
        { label: 'Monthly', value: 'admin_monthly', action: 'upgrade' },
        { label: 'Quarterly', value: 'admin_quarterly', action: 'upgrade' },
        { label: 'Annual', value: 'admin_annual', action: 'upgrade' },
      ], false);
      return;
    }

    if (subscription_status === 'admin_monthly') {
      openPlanModal('Schedule your upgrade', [
        { label: 'Quarterly', value: 'admin_quarterly', action: 'schedule' },
        { label: 'Annual', value: 'admin_annual', action: 'schedule' },
      ], true);
      return;
    }

    if (subscription_status === 'admin_quarterly') {
      openPlanModal('Schedule your upgrade', [
        { label: 'Annual', value: 'admin_annual', action: 'schedule' },
      ], true);
      return;
    }

    // Annual has no upgrade path
  };

  const onDowngradeClick = () => {
    if (!dashboardData) return;
    const { subscription_status } = dashboardData;

    if (subscription_status === 'admin_quarterly') {
      openPlanModal('Schedule your downgrade', [
        { label: 'Monthly', value: 'admin_monthly', action: 'schedule' },
      ], true);
      return;
    }

    if (subscription_status === 'admin_annual') {
      openPlanModal('Schedule your downgrade', [
        { label: 'Quarterly', value: 'admin_quarterly', action: 'schedule' },
        { label: 'Monthly', value: 'admin_monthly', action: 'schedule' },
      ], true);
      return;
    }

    // Monthly has no downgrade path
  };

  const onModalOptionSelect = (opt) => {
    if (!opt) return;
    if (opt.action === 'upgrade') {
      // upgrades via Stripe
      startCheckout(opt.value);
    } else if (opt.action === 'schedule') {
      setSelectedModalOption(opt);
    } else {
      changePlan(opt.value);
    }
  };

  const onConfirmScheduledChange = () => {
    if (!selectedModalOption || !acknowledgePlanChange) return;
    changePlan(selectedModalOption.value);
  };

  const onUpdateCard = async () => {
    try {
      setMessage('');
      const res = await fetch('http://localhost:8000/api/users/admin/payment_method/update_session/', {
        method: 'POST',
        headers: authHeaders(),
      });
      if (!isAuthedGuard(res)) return;
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.url) {
        window.location.assign(data.url);
        return;
      }
      setMessage(data.error || 'Could not open billing portal.');
    } catch (err) {
      console.error('update card error:', err);
      setMessage('network error.');
    }
  };

  // Determine which buttons to show (active & not canceled)
  const getActions = (status, active, canceled) => {
    if (!active || canceled) {
      return { showUpgrade: false, showDowngrade: false, showCancel: false };
    }
    switch (status) {
      case 'admin_trial':
        return { showUpgrade: true, showDowngrade: false, showCancel: true };
      case 'admin_monthly':
        return { showUpgrade: true, showDowngrade: false, showCancel: true };
      case 'admin_quarterly':
        return { showUpgrade: true, showDowngrade: true, showCancel: true };
      case 'admin_annual':
        return { showUpgrade: false, showDowngrade: true, showCancel: true };
      default:
        // unknown: no actions
        return { showUpgrade: false, showDowngrade: false, showCancel: false };
    }
  };

// ---------- render ----------
const actions = dashboardData
  ? getActions(
      dashboardData.subscription_status,
      dashboardData.subscription_active,
      dashboardData.is_canceled
    )
  : { showUpgrade: false, showDowngrade: false, showCancel: false };

const canReactivate =
  !!dashboardData && (dashboardData.is_canceled || !dashboardData.subscription_active);

return (
  <div className="admin-settings-wrapper">
    <h2>⚙️ admin settings</h2>

    {user?.email && (
      <p className="admin-settings-email">
        logged in as: <strong>{user.email}</strong>
      </p>
    )}

    {dashboardData ? (
      <div className="admin-settings-card">
        <h3>📄 subscription info</h3>

        <p>
          <strong>plan:</strong>{" "}
          {subscriptionLabels[dashboardData.subscription_status] || "—"}
        </p>

        {dashboardData.trial_start && (
          <p>
            <strong>trial start date:</strong> {formatDate(dashboardData.trial_start)}
          </p>
        )}
        {dashboardData.trial_ends_on && (
          <p>
            <strong>trial end date:</strong> {formatDate(dashboardData.trial_ends_on)}
          </p>
        )}
        {dashboardData.trial_converts_to && (
          <p>
            <strong>after trial:</strong> {subscriptionLabels[dashboardData.trial_converts_to] || "—"}
          </p>
        )}
        {dashboardData.is_trial && !dashboardData.trial_converts_to && dashboardData.is_canceled && (
          <p>
            <strong>after trial:</strong> No Plan
          </p>
        )}
        {dashboardData.current_cycle_ends_on && (
          <p>
            <strong>current cycle ends:</strong> {formatDate(dashboardData.current_cycle_ends_on)} ({dashboardData.days_left_in_cycle ?? 0} day(s) left)
          </p>
        )}
        {typeof dashboardData.days_left_in_cycle === "number" && (
          <p>
            <strong>days left on current plan:</strong> {dashboardData.days_left_in_cycle}
          </p>
        )}
        <p>
          <strong>next plan:</strong>{" "}
          {dashboardData.next_plan_status
            ? (subscriptionLabels[dashboardData.next_plan_status] || "—")
            : "No Plan"}
        </p>
        <p>
          <strong>next charge:</strong>{" "}
          {dashboardData.next_plan_status ? formatAmount(dashboardData.next_plan_price_cents) : "No Charge"}
        </p>
        {dashboardData.next_plan_effective_on && (
          <p>
            <strong>next plan starts:</strong> {formatDate(dashboardData.next_plan_effective_on)}
          </p>
        )}
        {dashboardData.monthly_start && (
          <p>
            <strong>monthly start date:</strong> {formatDate(dashboardData.monthly_start)}
          </p>
        )}
        {dashboardData.quarterly_start && (
          <p>
            <strong>quarterly start date:</strong> {formatDate(dashboardData.quarterly_start)}
          </p>
        )}
        {dashboardData.annual_start && (
          <p>
            <strong>annual start date:</strong> {formatDate(dashboardData.annual_start)}
          </p>
        )}

        {dashboardData.is_trial && dashboardData.days_remaining !== null && (
          <p className="trial-days-left">
            ⏳ trial days left: <strong>{dashboardData.days_remaining}</strong>
          </p>
        )}

        {dashboardData.next_billing && dashboardData.subscription_active && (
          <p>
            <strong>next billing date:</strong> {formatDate(dashboardData.next_billing)}
          </p>
        )}

        {dashboardData.subscription_active && !dashboardData.is_canceled && (
          <p className="subscription-active">
            ✅ your subscription is active and set to auto-renew.
          </p>
        )}

        {dashboardData.is_canceled && dashboardData.subscription_end && (
          <p className="subscription-canceled">
            🔒 your plan is canceled. access ends on{" "}
            <strong>{formatDate(dashboardData.subscription_end)}</strong>
            {" "}({daysUntil(dashboardData.subscription_end)} day(s) left)
          </p>
        )}

        <hr />
        <h3>💳 payment method</h3>
        {paymentMethod?.has_payment_method ? (
          <p>
            <strong>card on file:</strong> {String(paymentMethod.brand || '').toUpperCase()} ****{paymentMethod.last4} (exp {paymentMethod.exp_month}/{paymentMethod.exp_year})
          </p>
        ) : (
          <p><strong>card on file:</strong> No card available</p>
        )}
        <button type="button" onClick={onUpdateCard} className="btn-upgrade">
          update card
        </button>

        {/* Actions */}
        <div className="admin-settings-actions">
          {actions.showUpgrade && (
            <button
              onClick={onUpgradeClick}
              disabled={!!loadingAction || modalOpen}
              className="btn-upgrade"
            >
              {loadingAction === "upgrade" ? "processing…" : "upgrade"}
            </button>
          )}

          {actions.showDowngrade && (
            <button
              onClick={onDowngradeClick}
              disabled={!!loadingAction || modalOpen}
              className="btn-downgrade"
            >
              {loadingAction === "downgrade" ? "processing…" : "downgrade"}
            </button>
          )}

          {actions.showCancel && (
            <button
              onClick={handleCancel}
              disabled={!!loadingAction || modalOpen}
              className="btn-cancel"
            >
              {loadingAction === "cancel" ? "processing…" : "cancel subscription"}
            </button>
          )}

          {canReactivate && (
            <button
              type="button"
              onClick={() => { console.log('[Settings] -> /admin_reactivate'); navigate('/admin_reactivate'); }}
              className="btn-reactivate"
            >
              Reactivate plan
            </button>
          )}

        </div>

        {message && <p className="cancel-message">{message}</p>}

        {/* Minimal modal (no external libs) */}
        {modalOpen && (
          <div className="modal-overlay" role="dialog" aria-modal="true" aria-label={modalTitle}>
            <div className="modal-card">
              <h4>{modalTitle}</h4>
              <div className="modal-options">
                {modalOptions.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => onModalOptionSelect(opt)}
                    className="modal-option-btn"
                    disabled={!!loadingAction}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              {modalRequireAcknowledge && (
                <>
                  <p>
                    Your current plan stays active until this billing cycle ends.
                    Then your selected plan begins and is charged on the next renewal date.
                  </p>
                  <label>
                    <input
                      type="checkbox"
                      checked={acknowledgePlanChange}
                      onChange={(e) => setAcknowledgePlanChange(e.target.checked)}
                    />
                    {' '}I understand and confirm this scheduled plan change.
                  </label>
                  <button
                    onClick={onConfirmScheduledChange}
                    className="modal-option-btn"
                    disabled={!selectedModalOption || !acknowledgePlanChange || !!loadingAction}
                  >
                    {loadingAction ? 'processing…' : 'confirm scheduled change'}
                  </button>
                </>
              )}
              <button
                onClick={() => {
                  setModalOpen(false);
                  setSelectedModalOption(null);
                  setAcknowledgePlanChange(false);
                }}
                className="modal-cancel-btn"
                disabled={!!loadingAction}
              >
                close
              </button>
            </div>
          </div>
        )}
      </div>
    ) : (
      <p className="load-error">unable to load your subscription details.</p>
    )}

    <button onClick={() => navigate("/admin_dashboard")} className="btn-back">
      ← back to dashboard
    </button>
    </div>
); // <- end of return
}   // <- end of function AdminSettings

export default AdminSettings; // <- outside, top-level
