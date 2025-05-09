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
    <div style={{ padding: '3rem', maxWidth: '600px', margin: '0 auto', textAlign: 'center' }}>
      <h2 style={{ color: '#dc2626' }}>🚫 Your Admin Access is Inactive</h2>
      <p style={{ marginTop: '1rem', fontSize: '1.1rem', lineHeight: '1.6' }}>
        Your free trial has ended or was cancelled. To continue using the DTA dashboard and tools,
        you'll need to select a paid plan and reactivate your subscription.
      </p>

      <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'center', gap: '1rem' }}>
        <button
          onClick={() => navigate('/admin_reactivate')}
          style={{
            padding: '0.75rem 1.5rem',
            backgroundColor: '#10b981',
            color: 'white',
            fontWeight: 'bold',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
          }}
        >
          Reactivate Account
        </button>

        <button
          onClick={handleLogout}
          style={{
            padding: '0.75rem 1.5rem',
            backgroundColor: '#ef4444',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
          }}
        >
          Log Out
        </button>
      </div>

      <p style={{ marginTop: '2rem', fontSize: '0.95rem', color: '#6b7280' }}>
        Need help? Contact support at <a href="mailto:support@dta.com">support@dta.com</a>
      </p>
    </div>
  );
}

export default AdminTrialEnded;
