import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import { useLanguage } from '../../../context/LanguageContext';
import { apiRequest } from '../../../api/client';
import './AdminSettings.css';

function AdminSettings() {
  const { user, isAuthenticated } = useAuth();
  const { t } = useLanguage();
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
  const extractError = (data) => {
    const payload = data?.detail && typeof data.detail === 'object' ? data.detail : data;
    return payload?.error?.message || payload?.error || payload?.message || t('admin_settings.request_failed');
  };

  const isAuthedGuard = (res) => {
    if (res.status === 401) {
      navigate('/admin_login');
      return false;
    }
    return true;
  };

  const updateFromSnapshot = (payload, fallbackMsg = t('admin_settings.ok')) => {
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
    admin_trial: t('admin_settings.plan_free_trial'),
    admin_monthly: t('admin_settings.plan_monthly'),
    admin_quarterly: t('admin_settings.plan_quarterly'),
    admin_annual: t('admin_settings.plan_annual'),
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
        const { ok, status, data } = await apiRequest('/api/v1/users/admin/dashboard/', { auth: true });
        if (!isAuthedGuard({ status })) return;
        if (!ignore && ok) setDashboardData(data);
      } catch (err) {
        console.error('error fetching dashboard:', err);
      }
    };

    const fetchPlanMap = async () => {
      try {
        const { ok, status, data } = await apiRequest('/api/v1/users/admin/reactivation/preview/', { auth: true });
        if (!isAuthedGuard({ status })) return;
        if (!ignore && ok && Array.isArray(data.plans)) {
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
        const { ok, status, data } = await apiRequest('/api/v1/users/admin/payment_method/', { auth: true });
        if (!isAuthedGuard({ status })) return;
        if (!ignore && ok) setPaymentMethod(data);
      } catch (err) {
        console.error('error fetching payment method:', err);
      }
    };

    fetchDashboard();
    fetchPlanMap();
    fetchPaymentMethod();
    return () => { ignore = true; };
  }, [isAuthenticated, navigate]);

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
      setMessage(t('admin_settings.nothing_cancel'));
      return;
    }

    try {
      setLoadingAction('cancel');
      setMessage('');
      const { ok, status, data } = await apiRequest('/api/v1/users/admin/cancel_subscription/', {
        method: 'POST',
        auth: true,
      });
      if (!isAuthedGuard({ status })) return;

      if (ok) {
        updateFromSnapshot(data, t('admin_settings.auto_renew_canceled'));
      } else {
        setMessage(extractError(data));
      }
    } catch (err) {
      console.error('cancel error:', err);
      setMessage(t('admin_settings.network_error'));
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
        setMessage(t('admin_settings.cannot_resolve_plan'));
        return;
      }

      const { ok, status, data } = await apiRequest('/api/v1/users/admin/reactivation/start/', {
        method: 'POST',
        auth: true,
        body: { target_price_id: targetPriceId, with_trial: false },
      });
      if (!isAuthedGuard({ status })) return;

      if (ok) {
        const { action, url } = data || {};
        const errMsg = data?.error?.message || data?.error;
        if (action === 'checkout' && url) {
          setMessage(t('admin_settings.redirect_checkout'));
          window.location.assign(url);
          return;
        }
        setMessage(errMsg || t('admin_settings.could_not_checkout'));
        // Redirect to Stripe
      } else {
        setMessage(extractError(data));
      }
    } catch (err) {
      console.error('checkout error:', err);
      setMessage(t('admin_settings.network_error'));
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
      const { ok, status, data } = await apiRequest('/api/v1/users/admin/change_subscription/', {
        method: 'POST',
        auth: true,
        body: { target_plan },
      });
      if (!isAuthedGuard({ status })) return;

      if (ok) {
        setMessage(data?.message || t('admin_settings.change_scheduled'));
        const refreshed = await apiRequest('/api/v1/users/admin/dashboard/', { auth: true });
        if (refreshed.ok) {
          setDashboardData(refreshed.data);
        }
      } else {
        setMessage(data?.error?.message || data?.error || t('admin_settings.could_not_schedule'));
      }
    } catch (err) {
      console.error('change plan error:', err);
      setMessage(t('admin_settings.network_error'));
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
      openPlanModal(t('admin_settings.modal_upgrade_choose'), [
        { label: t('admin_settings.monthly'), value: 'admin_monthly', action: 'upgrade' },
        { label: t('admin_settings.quarterly'), value: 'admin_quarterly', action: 'upgrade' },
        { label: t('admin_settings.annual'), value: 'admin_annual', action: 'upgrade' },
      ], false);
      return;
    }

    if (subscription_status === 'admin_monthly') {
      openPlanModal(t('admin_settings.modal_upgrade_schedule'), [
        { label: t('admin_settings.quarterly'), value: 'admin_quarterly', action: 'schedule' },
        { label: t('admin_settings.annual'), value: 'admin_annual', action: 'schedule' },
      ], true);
      return;
    }

    if (subscription_status === 'admin_quarterly') {
      openPlanModal(t('admin_settings.modal_upgrade_schedule'), [
        { label: t('admin_settings.annual'), value: 'admin_annual', action: 'schedule' },
      ], true);
      return;
    }

    // Annual has no upgrade path
  };

  const onDowngradeClick = () => {
    if (!dashboardData) return;
    const { subscription_status } = dashboardData;

    if (subscription_status === 'admin_quarterly') {
      openPlanModal(t('admin_settings.modal_downgrade_schedule'), [
        { label: t('admin_settings.monthly'), value: 'admin_monthly', action: 'schedule' },
      ], true);
      return;
    }

    if (subscription_status === 'admin_annual') {
      openPlanModal(t('admin_settings.modal_downgrade_schedule'), [
        { label: t('admin_settings.quarterly'), value: 'admin_quarterly', action: 'schedule' },
        { label: t('admin_settings.monthly'), value: 'admin_monthly', action: 'schedule' },
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
      const { ok, status, data } = await apiRequest('/api/v1/users/admin/payment_method/update_session/', {
        method: 'POST',
        auth: true,
      });
      if (!isAuthedGuard({ status })) return;
      if (ok && data?.url) {
        window.location.assign(data.url);
        return;
      }
      setMessage(data?.error?.message || data?.error || t('admin_settings.could_not_billing'));
    } catch (err) {
      console.error('update card error:', err);
      setMessage(t('admin_settings.network_error'));
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
    <h2>⚙️ {t('admin_settings.title')}</h2>

    {user?.email && (
      <p className="admin-settings-email">
        {t('admin_settings.logged_in_as')} <strong>{user.email}</strong>
      </p>
    )}

    {dashboardData ? (
      <div className="admin-settings-card">
        <h3>📄 {t('admin_settings.subscription_info')}</h3>

        <p>
          <strong>{t('admin_settings.plan')}</strong>{" "}
          {subscriptionLabels[dashboardData.subscription_status] || "—"}
        </p>

        {dashboardData.trial_start && (
          <p>
            <strong>{t('admin_settings.trial_start')}</strong> {formatDate(dashboardData.trial_start)}
          </p>
        )}
        {dashboardData.trial_ends_on && (
          <p>
            <strong>{t('admin_settings.trial_end')}</strong> {formatDate(dashboardData.trial_ends_on)}
          </p>
        )}
        {dashboardData.trial_converts_to && (
          <p>
            <strong>{t('admin_settings.after_trial')}</strong> {subscriptionLabels[dashboardData.trial_converts_to] || "—"}
          </p>
        )}
        {dashboardData.is_trial && !dashboardData.trial_converts_to && dashboardData.is_canceled && (
          <p>
            <strong>{t('admin_settings.after_trial')}</strong> {t('admin_settings.no_plan')}
          </p>
        )}
        {dashboardData.current_cycle_ends_on && (
          <p>
            <strong>{t('admin_settings.current_cycle_ends')}</strong> {formatDate(dashboardData.current_cycle_ends_on)} ({dashboardData.days_left_in_cycle ?? 0} {t('admin_settings.days_left')})
          </p>
        )}
        {typeof dashboardData.days_left_in_cycle === "number" && (
          <p>
            <strong>{t('admin_settings.days_left_current')}</strong> {dashboardData.days_left_in_cycle}
          </p>
        )}
        <p>
          <strong>{t('admin_settings.next_plan')}</strong>{" "}
          {dashboardData.next_plan_status
            ? (subscriptionLabels[dashboardData.next_plan_status] || "—")
            : t('admin_settings.no_plan')}
        </p>
        <p>
          <strong>{t('admin_settings.next_charge')}</strong>{" "}
          {dashboardData.next_plan_status ? formatAmount(dashboardData.next_plan_price_cents) : t('admin_settings.no_charge')}
        </p>
        {dashboardData.next_plan_effective_on && (
          <p>
            <strong>{t('admin_settings.next_plan_starts')}</strong> {formatDate(dashboardData.next_plan_effective_on)}
          </p>
        )}
        {dashboardData.monthly_start && (
          <p>
            <strong>{t('admin_settings.monthly_start')}</strong> {formatDate(dashboardData.monthly_start)}
          </p>
        )}
        {dashboardData.quarterly_start && (
          <p>
            <strong>{t('admin_settings.quarterly_start')}</strong> {formatDate(dashboardData.quarterly_start)}
          </p>
        )}
        {dashboardData.annual_start && (
          <p>
            <strong>{t('admin_settings.annual_start')}</strong> {formatDate(dashboardData.annual_start)}
          </p>
        )}

        {dashboardData.is_trial && dashboardData.days_remaining !== null && (
          <p className="trial-days-left">
            ⏳ {t('admin_settings.trial_days_left')} <strong>{dashboardData.days_remaining}</strong>
          </p>
        )}

        {dashboardData.next_billing && dashboardData.subscription_active && (
          <p>
            <strong>{t('admin_settings.next_billing')}</strong> {formatDate(dashboardData.next_billing)}
          </p>
        )}

        {dashboardData.subscription_active && !dashboardData.is_canceled && (
          <p className="subscription-active">
            ✅ {t('admin_settings.active_auto_renew')}
          </p>
        )}

        {dashboardData.is_canceled && dashboardData.subscription_end && (
          <p className="subscription-canceled">
            🔒 {t('admin_settings.canceled_ends')}{" "}
            <strong>{formatDate(dashboardData.subscription_end)}</strong>
            {" "}({daysUntil(dashboardData.subscription_end)} {t('admin_settings.days_left')})
          </p>
        )}

        <hr />
        <h3>💳 {t('admin_settings.payment_method')}</h3>
        {paymentMethod?.has_payment_method ? (
          <p>
            <strong>{t('admin_settings.card_on_file')}</strong> {String(paymentMethod.brand || '').toUpperCase()} ****{paymentMethod.last4} (exp {paymentMethod.exp_month}/{paymentMethod.exp_year})
          </p>
        ) : (
          <p><strong>{t('admin_settings.card_on_file')}</strong> {t('admin_settings.no_card')}</p>
        )}
        <button type="button" onClick={onUpdateCard} className="btn-upgrade">
          {t('admin_settings.update_card')}
        </button>

        {/* Actions */}
        <div className="admin-settings-actions">
          {actions.showUpgrade && (
            <button
              onClick={onUpgradeClick}
              disabled={!!loadingAction || modalOpen}
              className="btn-upgrade"
            >
              {loadingAction === "upgrade" ? t('admin_settings.processing') : t('admin_settings.upgrade')}
            </button>
          )}

          {actions.showDowngrade && (
            <button
              onClick={onDowngradeClick}
              disabled={!!loadingAction || modalOpen}
              className="btn-downgrade"
            >
              {loadingAction === "downgrade" ? t('admin_settings.processing') : t('admin_settings.downgrade')}
            </button>
          )}

          {actions.showCancel && (
            <button
              onClick={handleCancel}
              disabled={!!loadingAction || modalOpen}
              className="btn-cancel"
            >
              {loadingAction === "cancel" ? t('admin_settings.processing') : t('admin_settings.cancel_subscription')}
            </button>
          )}

          {canReactivate && (
            <button
              type="button"
              onClick={() => { console.log('[Settings] -> /admin_reactivate'); navigate('/admin_reactivate'); }}
              className="btn-reactivate"
            >
              {t('admin_settings.reactivate_plan')}
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
                    {t('admin_settings.modal_schedule_msg')}
                  </p>
                  <label>
                    <input
                      type="checkbox"
                      checked={acknowledgePlanChange}
                      onChange={(e) => setAcknowledgePlanChange(e.target.checked)}
                    />
                    {' '}{t('admin_settings.modal_ack')}
                  </label>
                  <button
                    onClick={onConfirmScheduledChange}
                    className="modal-option-btn"
                    disabled={!selectedModalOption || !acknowledgePlanChange || !!loadingAction}
                  >
                    {loadingAction ? t('admin_settings.processing') : t('admin_settings.modal_confirm_change')}
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
                {t('common.close')}
              </button>
            </div>
          </div>
        )}
      </div>
    ) : (
      <p className="load-error">{t('admin_settings.load_error')}</p>
    )}

    <button onClick={() => navigate("/admin_dashboard")} className="btn-back">
      ← {t('admin_settings.back_dashboard')}
    </button>
    </div>
); // <- end of return
}   // <- end of function AdminSettings

export default AdminSettings; // <- outside, top-level
