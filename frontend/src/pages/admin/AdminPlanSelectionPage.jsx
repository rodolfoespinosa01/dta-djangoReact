import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const adminPlans = [
  {
    id: 'adminTrial',
    name: 'Free Admin Trial',
    price: 'Free for 14 days',
    description: 'Start with up to 10 clients. No charge until trial ends.',
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
      const response = await fetch('http://localhost:8000/api/create-checkout-session/', {
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
        window.location.href = data.url;
      } else {
        setError('Could not initiate checkout session.');
      }
    } catch (err) {
      console.error('Error starting checkout:', err);
      setError('Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '2rem', textAlign: 'center' }}>
      <h2>Select Your Admin Plan</h2>

      <input
        type="email"
        placeholder="Enter your email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        style={{
          marginBottom: '0.5rem',
          padding: '0.5rem',
          width: '300px',
        }}
      />
      {error && <p style={{ color: 'red', marginBottom: '1rem' }}>{error}</p>}

      <div style={{ display: 'flex', justifyContent: 'center', gap: '2rem', flexWrap: 'wrap', marginTop: '2rem' }}>
        {adminPlans.map((adminPlan) => (
          <div
            key={adminPlan.id}
            style={{
              border: '1px solid #ccc',
              borderRadius: '8px',
              padding: '1.5rem',
              width: '250px',
              textAlign: 'left',
            }}
          >
            <h3>{adminPlan.name}</h3>
            <p><strong>{adminPlan.price}</strong></p>
            <p>{adminPlan.description}</p>
            <button
              onClick={() => handleSelectAdminPlan(adminPlan.id)}
              disabled={loading}
              style={{
                marginTop: '1rem',
                width: '100%',
                padding: '0.75rem',
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                cursor: 'pointer',
              }}
            >
              {loading ? 'Processing...' : 'Continue to Checkout'}
            </button>
          </div>
        ))}
      </div>

      <button
        onClick={handleHomeCTA}
        style={{ marginTop: '2rem', padding: '1rem 2rem', fontSize: '1rem' }}
      >
        Back to Main Page
      </button>
    </div>
  );
}

export default AdminPlanSelectionPage;
