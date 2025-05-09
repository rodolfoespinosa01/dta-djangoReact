import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

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
    <div style={{ padding: '3rem', backgroundColor: '#f9fafb', minHeight: '100vh' }}>
      <h2 style={{ textAlign: 'center', marginBottom: '1.5rem' }}>🧾 Choose Your Admin Plan</h2>

      <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
        <input
          type="email"
          placeholder="Enter your email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{
            padding: '0.75rem',
            width: '280px',
            borderRadius: '6px',
            border: '1px solid #d1d5db',
            fontSize: '1rem',
          }}
        />
        {error && (
          <p style={{ color: 'red', marginTop: '0.5rem' }}>{error}</p>
        )}
      </div>

      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          gap: '2rem',
          flexWrap: 'wrap',
          marginTop: '2rem',
        }}
      >
        {adminPlans.map((adminPlan) => (
          <div
            key={adminPlan.id}
            style={{
              backgroundColor: '#ffffff',
              border: '1px solid #e5e7eb',
              borderRadius: '10px',
              padding: '2rem',
              width: '260px',
              textAlign: 'left',
              boxShadow: '0 2px 6px rgba(0, 0, 0, 0.04)',
              transition: 'transform 0.2s ease-in-out',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.03)')}
            onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
          >
            <h3 style={{ marginBottom: '0.25rem' }}>{adminPlan.name}</h3>
            <p style={{ fontWeight: 'bold', color: '#2563eb', marginBottom: '0.5rem' }}>{adminPlan.price}</p>
            <p style={{ fontSize: '0.95rem', color: '#4b5563' }}>{adminPlan.description}</p>
            <button
              onClick={() => handleSelectAdminPlan(adminPlan.id)}
              disabled={loading}
              style={{
                marginTop: '1.25rem',
                width: '100%',
                padding: '0.75rem',
                backgroundColor: '#2563eb',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: 'bold',
              }}
            >
              {loading ? 'Processing...' : 'Continue to Checkout'}
            </button>
          </div>
        ))}
      </div>

      <div style={{ textAlign: 'center' }}>
        <button
          onClick={handleHomeCTA}
          style={{
            marginTop: '3rem',
            padding: '0.75rem 1.5rem',
            fontSize: '1rem',
            backgroundColor: '#6b7280',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
          }}
        >
          Back to Main Page
        </button>
      </div>
    </div>
  );
}

export default AdminPlanSelectionPage;
