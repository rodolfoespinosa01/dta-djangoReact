import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

function AdminReactivatePage() {
  const { accessToken } = useAuth();
  const navigate = useNavigate();
  const [selectedPlan, setSelectedPlan] = useState('adminMonthly');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleReactivate = async () => {
    setLoading(true);
    setError(null);

    try {
      const res = await fetch('http://localhost:8000/api/users/admin/reactivate_checkout/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ plan_name: selectedPlan }),
      });

      const data = await res.json();

      if (res.ok && data.url) {
        window.location.href = data.url;
      } else {
        setError(data.error || 'Something went wrong.');
        setLoading(false);
      }
    } catch (err) {
      console.error('Error:', err);
      setError('Network error.');
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '3rem', backgroundColor: '#f3f4f6', minHeight: '100vh' }}>
      <div
        style={{
          maxWidth: '500px',
          margin: '0 auto',
          backgroundColor: '#fff',
          padding: '2rem',
          borderRadius: '10px',
          boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
        }}
      >
        <h2 style={{ marginBottom: '1rem', textAlign: 'center' }}>🔄 Reactivate Your Admin Subscription</h2>
        <p style={{ textAlign: 'center', marginBottom: '1.5rem', color: '#4b5563' }}>
          Select a plan to resume your access. Your new billing cycle will start based on your current subscription status.
        </p>

        <label style={{ fontWeight: 'bold', marginBottom: '0.5rem', display: 'block' }}>
          Choose a Plan:
        </label>
        <select
          value={selectedPlan}
          onChange={(e) => setSelectedPlan(e.target.value)}
          style={{
            padding: '0.75rem',
            width: '100%',
            borderRadius: '6px',
            border: '1px solid #d1d5db',
            marginBottom: '1.5rem',
          }}
        >
          <option value="adminMonthly">📆 Monthly – $29/month</option>
          <option value="adminQuarterly">📅 Quarterly – $75/quarter</option>
          <option value="adminAnnual">📈 Annual – $250/year</option>
        </select>

        <button
          onClick={handleReactivate}
          disabled={loading}
          style={{
            width: '100%',
            backgroundColor: '#10b981',
            color: 'white',
            padding: '0.75rem',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 'bold',
          }}
        >
          {loading ? 'Redirecting to Stripe...' : 'Reactivate Plan'}
        </button>

        {error && (
          <p style={{ color: 'red', marginTop: '1rem', textAlign: 'center' }}>{error}</p>
        )}

        <div style={{ marginTop: '2rem', textAlign: 'center' }}>
          <button
            onClick={() => navigate('/admin_settings')}
            style={{
              backgroundColor: '#2563eb',
              color: 'white',
              padding: '0.5rem 1.25rem',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
            }}
          >
            Back to Settings
          </button>
        </div>
      </div>
    </div>
  );
}

export default AdminReactivatePage;
