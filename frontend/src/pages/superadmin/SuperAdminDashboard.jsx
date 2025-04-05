import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

function SuperAdminDashboard() {
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    // Protect route
    if (!isAuthenticated || !user?.is_superuser) {
      navigate('/superadminlogin');
      return;
    }

    const token = localStorage.getItem('access_token');
    if (!token) {
      navigate('/superadminlogin');
      return;
    }

    // Fetch superadmin stats
    fetch('http://localhost:8000/api/users/superadmin/dashboard/', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then(res => res.json())
      .then(data => setStats(data))
      .catch(err => {
        console.error('Failed to fetch dashboard data:', err);
        navigate('/superadminlogin');
      });
  }, [isAuthenticated, user, navigate]);

  if (!stats) {
    return <p style={{ padding: '2rem' }}>Loading SuperAdmin dashboard...</p>;
  }

  return (
    <div style={{ padding: '2rem' }}>
      <h2>SuperAdmin Dashboard</h2>

      <h3>Active Admins</h3>

      <div>
        <h4>🧪 Free Trial</h4>
        <ul>
          {stats.trial_admins.map(email => (
            <li key={email}>{email}</li>
          ))}
        </ul>

        <h4>💳 Monthly</h4>
        <ul>
          {stats.monthly_admins.map(email => (
            <li key={email}>{email}</li>
          ))}
        </ul>

        <h4>📅 Annual</h4>
        <ul>
          {stats.annual_admins.map(email => (
            <li key={email}>{email}</li>
          ))}
        </ul>
      </div>

      <hr />

      <p><strong>💰 Total Revenue Generated:</strong> {stats.total_revenue}</p>
      <p><strong>📈 Projected Next Month Income:</strong> {stats.projected_monthly_income}</p>

      <button
        onClick={() => {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          navigate('/superadminlogin');
        }}
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
    </div>
  );
}

export default SuperAdminDashboard;
