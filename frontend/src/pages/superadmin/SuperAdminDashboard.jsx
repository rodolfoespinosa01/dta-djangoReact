import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

function SuperAdminDashboard() {
  const { user, isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    // Don't check auth until loading is done
    if (loading) return;

    if (!isAuthenticated || !user?.is_superuser) {
      navigate('/superadmin-login');
      return;
    }

    const token = localStorage.getItem('access_token');
    if (!token) {
      navigate('/superadmin-login');
      return;
    }

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
  }, [loading, isAuthenticated, user, navigate]);

  if (loading || !stats) {
    return <p style={{ padding: '2rem' }}>Loading SuperAdmin dashboard...</p>;
  }

  return (
    <div style={{ padding: '2rem' }}>
      <h2>SuperAdmin Dashboard</h2>

      <h3>All Admins</h3>
<table style={{ width: '100%', marginTop: '1rem', borderCollapse: 'collapse' }}>
  <thead>
    <tr>
      <th style={{ borderBottom: '1px solid #ccc', padding: '0.5rem' }}>Email</th>
      <th style={{ borderBottom: '1px solid #ccc', padding: '0.5rem' }}>Plan</th>
      <th style={{ borderBottom: '1px solid #ccc', padding: '0.5rem' }}>Price</th>
      <th style={{ borderBottom: '1px solid #ccc', padding: '0.5rem' }}>Next Billing Date</th>
    </tr>
  </thead>
  <tbody>
    {stats.admins.map((admin, idx) => (
      <tr key={idx}>
        <td style={{ padding: '0.5rem' }}>{admin.email}</td>
        <td style={{ padding: '0.5rem' }}>{admin.plan}</td>
        <td style={{ padding: '0.5rem' }}>{admin.price}</td>
        <td style={{ padding: '0.5rem' }}>{admin.next_billing_date}</td>
      </tr>
    ))}
  </tbody>
</table>

    </div>
  );
}

export default SuperAdminDashboard;
