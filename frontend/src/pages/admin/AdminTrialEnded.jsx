import React from 'react';
import { useNavigate } from 'react-router-dom';

function AdminTrialEnded() {
  const navigate = useNavigate();

  return (
    <div style={{ padding: '2rem', textAlign: 'center' }}>
      <h2>Your Free Trial Has Ended</h2>
      <p style={{ marginTop: '1rem' }}>
        Your trial has either expired or been cancelled. To regain access to your dashboard,
        please choose a monthly or annual plan.
      </p>

      <button
        onClick={() => navigate('/adminplans')}
        style={{
          marginTop: '2rem',
          padding: '0.75rem 1.5rem',
          backgroundColor: '#2563eb',
          color: 'white',
          border: 'none',
          borderRadius: '6px',
          cursor: 'pointer'
        }}
      >
        View Plans
      </button>
    </div>
  );
}

export default AdminTrialEnded;
