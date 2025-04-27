import React from 'react';
import { useNavigate } from 'react-router-dom';

function AdminTrialEnded() {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('access');
    localStorage.removeItem('refresh');
    localStorage.removeItem('user_id');
    localStorage.removeItem('email');
    localStorage.removeItem('role');
    localStorage.removeItem('subscription_status');

    navigate('/admin_login');
  };

  return (
    <div style={{ padding: '2rem', textAlign: 'center' }}>
      <h2>Your Free Trial Has Ended</h2>
      <p style={{ marginTop: '1rem' }}>
        Your trial has either expired or been cancelled. To regain access to your dashboard,
        please choose a monthly or annual plan.
      </p>

      <div style={{ marginTop: '2rem' }}>
        <button
          onClick={() => navigate('/admin_plans')}
          style={{
            marginRight: '1rem',
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

        <button
          onClick={handleLogout}
          style={{
            padding: '0.75rem 1.5rem',
            backgroundColor: '#ef4444',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer'
          }}
        >
          Log Out
        </button>
      </div>
    </div>
  );
}

export default AdminTrialEnded;
