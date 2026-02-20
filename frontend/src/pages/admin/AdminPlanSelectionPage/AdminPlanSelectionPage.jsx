import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../../../context/LanguageContext';
import './AdminPlanSelectionPage.css';

function AdminPlanSelectionPage() {
  const { t } = useLanguage();
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [loadingAction, setLoadingAction] = useState(null);
  const navigate = useNavigate();
  const getActionKey = (planId, isTrial) => `${planId}:${isTrial ? 'trial' : 'paid'}`;
  const adminPlans = [
    {
      id: 'adminMonthly',
      name: t('admin_plan.monthly_name'),
      price: '$29 / month',
      description: t('admin_plan.monthly_desc'),
    },
    {
      id: 'adminQuarterly',
      name: t('admin_plan.quarterly_name'),
      price: '$79 / 3 months',
      description: t('admin_plan.quarterly_desc'),
    },
    {
      id: 'adminAnnual',
      name: t('admin_plan.annual_name'),
      price: '$299 / year',
      description: t('admin_plan.annual_desc'),
    },
  ];

  const handleHomeCTA = () => {
    navigate('/');
  };

  const handleSelectAdminPlan = async (planId, isTrial) => {
    if (loadingAction) return;
    if (!email) {
      setError(t('admin_plan.email_required'));
      return;
    }

    const actionKey = getActionKey(planId, isTrial);
    setError('');
    setLoadingAction(actionKey);

    try {
      const response = await fetch('http://localhost:8000/api/users/admin/create_checkout_session/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan_name: planId, email, is_trial: isTrial }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data?.error || t('admin_plan.generic_error'));
        return;
      }

      if (data.url) {
        window.location.href = data.url;
      } else {
        setError(t('admin_plan.checkout_failed'));
      }
    } catch (err) {
      console.error('Error starting checkout:', err);
      setError(t('admin_login.err_generic'));
    } finally {
      setLoadingAction(null);
    }
  };

  return (
    <div className="admin-plan-wrapper">
      <h2 className="admin-plan-title">🧾 {t('admin_plan.title')}</h2>

      <div className="admin-plan-email">
        <input
          type="email"
          placeholder={t('admin_plan.email_placeholder')}
          required
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (error) setError('');
          }}
          className={`admin-plan-input ${error ? 'has-error' : ''}`}
        />
        {error && <p className="admin-plan-error" role="alert" aria-live="assertive">⚠ {error}</p>}
      </div>

      <div className="admin-plan-list">
        {adminPlans.map((plan) => (
          <div
            key={plan.id}
            className="admin-plan-card"
            onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.03)')}
            onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
          >
            <h3>{plan.name}</h3>
            <p className="admin-plan-price">{plan.price}</p>
            <p className="admin-plan-description">{plan.description}</p>

            <button
              onClick={() => handleSelectAdminPlan(plan.id, true)}
              disabled={!!loadingAction}
              className="admin-plan-button"
            >
              {loadingAction === getActionKey(plan.id, true) ? t('admin_plan.processing') : t('admin_plan.start_trial')}
            </button>

            <button
              onClick={() => handleSelectAdminPlan(plan.id, false)}
              disabled={!!loadingAction}
              className="admin-plan-button"
            >
              {loadingAction === getActionKey(plan.id, false) ? t('admin_plan.processing') : t('admin_plan.buy_now')}
            </button>
          </div>
        ))}
      </div>

      <div className="admin-plan-footer">
        <button onClick={handleHomeCTA} className="admin-plan-back-button">
          {t('common.back_to_main_page')}
        </button>
      </div>
    </div>
  );
}

export default AdminPlanSelectionPage;
