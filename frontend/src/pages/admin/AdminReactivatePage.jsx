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
      const res = await fetch('http://localhost:8000/api/adminplans/admin_reactivate_checkout/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ plan_name: selectedPlan })
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
    <div style={{ padding: '2rem' }}>
      <h2>Reactivate Your Admin Subscription</h2>
      <p>Select a new plan to restart your access:</p>

      <select
        value={selectedPlan}
        onChange={(e) => setSelectedPlan(e.target.value)}
        style={{ padding: '0.5rem', marginBottom: '1rem' }}
      >
        <option value="adminMonthly">Monthly - $29/month</option>
        <option value="adminQuarterly">Quarterly - $75/quarter</option>
        <option value="adminAnnual">Annual - $250/year</option>
      </select>

      <br />
      <button
        onClick={handleReactivate}
        disabled={loading}
        style={{
          backgroundColor: '#10b981',
          color: 'white',
          padding: '0.75rem 1.5rem',
          border: 'none',
          borderRadius: '6px',
          cursor: 'pointer',
          fontWeight: 'bold'
        }}
      >
        {loading ? 'Redirecting to Stripe...' : 'Reactivate Plan'}
      </button>

      {error && <p style={{ marginTop: '1rem', color: 'red' }}>{error}</p>}

      <p style={{ marginTop: '2rem' }}>
        <button
          onClick={() => navigate('/admin_settings')}
          style={{ backgroundColor: '#2563eb', color: 'white', padding: '0.5rem 1rem', border: 'none', borderRadius: '4px' }}
        >
          Back to Settings
        </button>
      </p>
    </div>
  );
}

export default AdminReactivatePage;