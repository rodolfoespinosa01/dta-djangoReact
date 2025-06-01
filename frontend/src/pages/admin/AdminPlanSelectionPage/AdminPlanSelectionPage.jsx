// AdminPlanSelectionPage.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './AdminPlanSelectionPage.css';

const adminPlans = [
  {
    id: 'adminTrial',
    name: 'Free Admin Trial',
    price: 'Free for 14 days',
    description: 'Try all features free for 14 days. After the trial, you will be billed $29.99/month unless canceled.',
  },
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
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleHomeCTA = () => {
    navigate('/');
  };

  const handleSelectAdminPlan = async (planId) => {
    if (!email) {
      setError('Please enter your email before continuing to checkout.');
      return;
    }

    setError('');
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/users/admin/create_checkout_session/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan_name: planId, email }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data?.error || 'Something went wrong.');
        return;
      }

      if (data.url) {
        window.location.href = data.url;;
      } else {
        setError('Could not initiate checkout session.');
      }
    } catch (err) {
      console.error('error starting checkout:', err);
      setError('something went wrong. please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="admin-plan-wrapper">
      <h2 className="admin-plan-title">🧾 choose your admin plan</h2>

      <div className="admin-plan-email">
        <input
          type="email"
          placeholder="enter your email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="admin-plan-input"
        />
        {error && <p className="admin-plan-error">{error}</p>}
      </div>

      <div className="admin-plan-list">
        {adminPlans.map((adminPlan) => (
          <div
            key={adminPlan.id}
            className="admin-plan-card"
            onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.03)')}
            onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
          >
            <h3>{adminPlan.name}</h3>
            <p className="admin-plan-price">{adminPlan.price}</p>
            <p className="admin-plan-description">{adminPlan.description}</p>
            <button onClick={() => handleSelectAdminPlan(adminPlan.id)} disabled={loading} className="admin-plan-button">
              {loading ? 'processing...' : 'continue to checkout'}
            </button>
          </div>
        ))}
      </div>

      <div className="admin-plan-footer">
        <button onClick={handleHomeCTA} className="admin-plan-back-button">
          back to main page
        </button>
      </div>
    </div>
  );
}

export default AdminPlanSelectionPage;
