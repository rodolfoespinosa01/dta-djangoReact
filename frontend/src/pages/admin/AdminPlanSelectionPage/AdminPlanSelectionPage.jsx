import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './AdminPlanSelectionPage.css';

const adminPlans = [
  {
    id: 'adminMonthly',
    name: 'Monthly Admin Plan',
    price: '$29 / month',
    description: 'Unlimited users. Billed monthly.',
  },
  {
    id: 'adminQuarterly',
    name: 'Quarterly Admin Plan',
    price: '$79 / 3 months',
    description: 'Save 10% with quarterly billing.',
  },
  {
    id: 'adminAnnual',
    name: 'Annual Admin Plan',
    price: '$299 / year',
    description: 'Best value. Save 14% annually.',
  },
];

function AdminPlanSelectionPage() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [loadingAction, setLoadingAction] = useState(null);
  const navigate = useNavigate();
  const getActionKey = (planId, isTrial) => `${planId}:${isTrial ? 'trial' : 'paid'}`;

  const handleHomeCTA = () => {
    navigate('/');
  };

  const handleSelectAdminPlan = async (planId, isTrial) => {
    if (loadingAction) return;
    if (!email) {
      setError('Please enter your email before continuing to checkout.');
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
        setError(data?.error || 'Something went wrong.');
        return;
      }

      if (data.url) {
        window.location.href = data.url;
      } else {
        setError('Could not initiate checkout session.');
      }
    } catch (err) {
      console.error('Error starting checkout:', err);
      setError('Something went wrong. Please try again.');
    } finally {
      setLoadingAction(null);
    }
  };

  return (
    <div className="admin-plan-wrapper">
      <h2 className="admin-plan-title">🧾 Choose Your Admin Plan</h2>

      <div className="admin-plan-email">
        <input
          type="email"
          placeholder="Enter your email"
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
              {loadingAction === getActionKey(plan.id, true) ? 'Processing...' : 'Start Free Trial'}
            </button>

            <button
              onClick={() => handleSelectAdminPlan(plan.id, false)}
              disabled={!!loadingAction}
              className="admin-plan-button"
            >
              {loadingAction === getActionKey(plan.id, false) ? 'Processing...' : 'Buy Now'}
            </button>
          </div>
        ))}
      </div>

      <div className="admin-plan-footer">
        <button onClick={handleHomeCTA} className="admin-plan-back-button">
          Back to Main Page
        </button>
      </div>
    </div>
  );
}

export default AdminPlanSelectionPage;
