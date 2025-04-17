import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

function AdminDashboard() {
  const { user, isAuthenticated, accessToken, logout } = useAuth();
  const navigate = useNavigate();

  const [daysLeft, setDaysLeft] = useState(null);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/admin-login');
      return;
    }

    const fetchTrialStatus = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/users/admin-dashboard/', {
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        });
    
        if (res.status === 403) {
          const data = await res.json();
          if (data.redirect_to) {
            navigate(data.redirect_to);
          }
          return;
        }
    
        const data = await res.json();
        if (res.ok && data.trial_active) {
          setDaysLeft(data.days_remaining);
        }
      } catch (err) {
        console.error('Error fetching trial info:', err);
      }
    };

    fetchTrialStatus();
  }, [accessToken, isAuthenticated, navigate]);

  return (
    <div style={{ padding: '2rem', textAlign: 'center' }}>
      <h1>Welcome to your dashboard</h1>
      <p>Your all-in-one platform for creating personalized diet plans for your clients.</p>

      <div style={{ marginTop: '2rem' }}>
        <p><strong>Email:</strong> {user?.email}</p>
        <p><strong>Role:</strong> {user?.role}</p>
        <p><strong>User ID:</strong> {user?.user_id}</p>
        {user?.subscription_status === 'admin_trial' && daysLeft !== null && (
          <p style={{ marginTop: '1rem' }}>⏳ Trial Days Left: <strong>{daysLeft}</strong></p>
        )}
      </div>

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
        onClick={() => navigate('/admin-settings')}
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
