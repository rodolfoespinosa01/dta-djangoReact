import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import './AdminSettings.css';

function AdminSettings() {
  const { user, isAuthenticated, accessToken } = useAuth();
  const navigate = useNavigate();

  const [dashboardData, setDashboardData] = useState(null);
  const [message, setMessage] = useState('');
  const [loadingAction, setLoadingAction] = useState(null); // 'cancel' | 'upgrade' | 'downgrade' | null

  // modal for plan selection
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTitle, setModalTitle] = useState('');
  const [modalOptions, setModalOptions] = useState([]); // [{label, value, action:'upgrade'|'downgrade'}]

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

  const subscriptionLabels = {
    admin_trial: 'Free Trial',
    admin_monthly: 'Monthly Plan',
    admin_quarterly: 'Quarterly Plan',
    admin_annual: 'Annual Plan',
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

    fetchDashboard();
    return () => { ignore = true; };
  }, [accessToken, isAuthenticated, navigate]);

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
      const res = await fetch('http://localhost:8000/api/users/admin/create_checkout_session/', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ target_plan }),
      });
      if (!isAuthedGuard(res)) return;

      if (res.ok) {
        const { url, message: msg } = await res.json();
        setMessage(msg || 'redirecting to checkout…');
        // Redirect to Stripe
        if (url) window.location.assign(url);
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

  // Plan change at next cycle (no Stripe)
  const changePlan = async (target_plan) => {
    try {
      setLoadingAction('downgrade'); // may also be used for auto-upgrade from quarterly->annual if you handle it server-side without Stripe
      setMessage('');
      const res = await fetch('http://localhost:8000/api/users/admin/change_subscription/', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ target_plan }),
      });
      if (!isAuthedGuard(res)) return;

      if (res.ok) {
        const payload = await res.json();
        updateFromSnapshot(payload, 'plan changed');
      } else {
        setMessage(await extractError(res));
      }
    } catch (err) {
      console.error('change plan error:', err);
      setMessage('network error.');
    } finally {
      setLoadingAction(null);
      setModalOpen(false);
    }
  };

  // ---------- button handlers per your rules ----------
  const onUpgradeClick = () => {
    if (!dashboardData) return;
    const { subscription_status } = dashboardData;

    if (subscription_status === 'admin_monthly') {
      // choose Quarterly or Annual (Stripe)
      setModalTitle('Choose your upgrade plan');
      setModalOptions([
        { label: 'Quarterly', value: 'admin_quarterly', action: 'upgrade' },
        { label: 'Annual', value: 'admin_annual', action: 'upgrade' },
      ]);
      setModalOpen(true);
      return;
    }

    if (subscription_status === 'admin_quarterly') {
      // direct to Annual (Stripe)
      startCheckout('admin_annual');
      return;
    }

    // Annual has no upgrade path
  };

  const onDowngradeClick = () => {
    if (!dashboardData) return;
    const { subscription_status } = dashboardData;

    if (subscription_status === 'admin_quarterly') {
      // direct to Monthly (no Stripe)
      changePlan('admin_monthly');
      return;
    }

    if (subscription_status === 'admin_annual') {
      // choose Monthly or Quarterly (no Stripe)
      setModalTitle('Choose your downgrade plan');
      setModalOptions([
        { label: 'Quarterly', value: 'admin_quarterly', action: 'downgrade' },
        { label: 'Monthly', value: 'admin_monthly', action: 'downgrade' },
      ]);
      setModalOpen(true);
      return;
    }

    // Monthly has no downgrade path
  };

  const onModalOptionSelect = (opt) => {
    if (!opt) return;
    if (opt.action === 'upgrade') {
      // upgrades via Stripe
      startCheckout(opt.value);
    } else {
      // downgrades without Stripe
      changePlan(opt.value);
    }
  };

  // Determine which buttons to show (active & not canceled)
  const getActions = (status, active, canceled) => {
    if (!active || canceled) {
      return { showUpgrade: false, showDowngrade: false, showCancel: false };
    }
    switch (status) {
      case 'admin_monthly':
        return { showUpgrade: true, showDowngrade: false, showCancel: true };
      case 'admin_quarterly':
        return { showUpgrade: true, showDowngrade: true, showCancel: true };
      case 'admin_annual':
        return { showUpgrade: false, showDowngrade: true, showCancel: true };
      default:
        // trial/unknown: no changes
        return { showUpgrade: false, showDowngrade: false, showCancel: false };
    }
  };

  // ---------- render ----------
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

          <p><strong>plan:</strong> {subscriptionLabels[dashboardData.subscription_status] || '—'}</p>

          {dashboardData.trial_start && (
            <p><strong>trial start date:</strong> {formatDate(dashboardData.trial_start)}</p>
          )}
          {dashboardData.monthly_start && (
            <p><strong>monthly start date:</strong> {formatDate(dashboardData.monthly_start)}</p>
          )}
          {dashboardData.quarterly_start && (
            <p><strong>quarterly start date:</strong> {formatDate(dashboardData.quarterly_start)}</p>
          )}
          {dashboardData.annual_start && (
            <p><strong>annual start date:</strong> {formatDate(dashboardData.annual_start)}</p>
          )}

          {dashboardData.is_trial && dashboardData.days_remaining !== null && (
            <p className="trial-days-left">
              ⏳ trial days left: <strong>{dashboardData.days_remaining}</strong>
            </p>
          )}

          {dashboardData.next_billing && dashboardData.subscription_active && (
            <p><strong>next billing date:</strong> {formatDate(dashboardData.next_billing)}</p>
          )}

          {dashboardData.subscription_active && !dashboardData.is_canceled && (
            <p className="subscription-active">
              ✅ your subscription is active and set to auto-renew.
            </p>
          )}

          {dashboardData.is_canceled && dashboardData.subscription_end && (
            <p className="subscription-canceled">
              🔒 your plan is canceled. access ends on <strong>{formatDate(dashboardData.subscription_end)}</strong>
            </p>
          )}

          {/* Actions */}
          {(() => {
            const { showUpgrade, showDowngrade, showCancel } = getActions(
              dashboardData.subscription_status,
              dashboardData.subscription_active,
              dashboardData.is_canceled
            );

            return (
              <div className="admin-settings-actions">
                {showUpgrade && (
                  <button
                    onClick={onUpgradeClick}
                    disabled={!!loadingAction || modalOpen}
                    className="btn-upgrade"
                  >
                    {loadingAction === 'upgrade' ? 'processing…' : 'upgrade'}
                  </button>
                )}

                {showDowngrade && (
                  <button
                    onClick={onDowngradeClick}
                    disabled={!!loadingAction || modalOpen}
                    className="btn-downgrade"
                  >
                    {loadingAction === 'downgrade' ? 'processing…' : 'downgrade'}
                  </button>
                )}

                {showCancel && (
                  <button
                    onClick={handleCancel}
                    disabled={!!loadingAction || modalOpen}
                    className="btn-cancel"
                  >
                    {loadingAction === 'cancel' ? 'processing…' : 'cancel subscription'}
                  </button>
                )}
              </div>
            );
          })()}

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
                <button onClick={() => setModalOpen(false)} className="modal-cancel-btn" disabled={!!loadingAction}>
                  close
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <p className="load-error">unable to load your subscription details.</p>
      )}

      <button onClick={() => navigate('/admin_dashboard')} className="btn-back">
        ← back to dashboard
      </button>
    </div>
  );
}

export default AdminSettings;

// summary:
// - monthly upgrade -> picker (quarterly/annual) -> Stripe checkout
// - quarterly upgrade -> annual (Stripe), downgrade -> monthly (no Stripe)
// - annual downgrade -> picker (monthly/quarterly) (no Stripe)
// - cancel stays the same
// - uses backend snapshots and redirects to Stripe when needed
