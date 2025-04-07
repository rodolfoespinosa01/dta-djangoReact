import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

function AdminDashboard() {
  const { user, isAuthenticated, loading, logout } = useAuth();
  const navigate = useNavigate();

  const [cancelled, setCancelled] = useState(false);
  const [cancelMessage, setCancelMessage] = useState('');

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      navigate('/adminlogin');
    }
  }, [isAuthenticated, loading, navigate]);

  const handleCancelAutoRenew = async () => {
    const token = localStorage.getItem('access_token');
    const response = await fetch('http://localhost:8000/api/users/admin/cancel-auto-renew/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
    });

    const data = await response.json();
    if (response.ok) {
      setCancelled(true);
      setCancelMessage(data.message);
    } else {
      setCancelMessage(data.error || 'Failed to cancel auto-renewal.');
    }
  };

  if (loading) {
    return <p style={{ padding: '2rem' }}>Loading your dashboard...</p>;
  }

  if (!isAuthenticated || !user) {
    return <p style={{ padding: '2rem', color: 'red' }}>You are not authorized to view this page.</p>;
  }

  return (
    <div style={{ padding: '2rem', textAlign: 'center' }}>
      <h1>Welcome to your dashboard</h1>
      <p>Your all-in-one platform for creating personalized diet plans for your clients.</p>

      <div style={{ marginTop: '2rem' }}>
        <p><strong>Email:</strong> {user.email}</p>
        <p><strong>Role:</strong> {user.role}</p>
        <p><strong>User ID:</strong> {user.user_id}</p>
      </div>

      {/* Cancel Auto-Renewal Button for Trial Admins */}
      {user?.role === 'admin' && user?.subscription_status === 'admin_trial' && !cancelled && (
        <div style={{ marginTop: '2rem' }}>
          <button
            onClick={handleCancelAutoRenew}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: '#fbbf24',
              color: 'black',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
            }}
          >
            Cancel Auto-Renewal
          </button>
        </div>
      )}

      {cancelMessage && (
        <p style={{ marginTop: '1rem', color: cancelled ? 'green' : 'red' }}>{cancelMessage}</p>
      )}

      <button
        onClick={logout}
        style={{
          marginTop: '2rem',
          padding: '0.75rem 1.5rem',
          backgroundColor: '#dc2626',
          color: 'white',
          border: 'none',
          borderRadius: '6px',
          cursor: 'pointer'
        }}
      >
        Logout
      </button>

      <br />

      <button
        onClick={() => navigate('/adminsettings')}
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
        Go to Settings
      </button>
    </div>
  );
}

export default AdminDashboard;
