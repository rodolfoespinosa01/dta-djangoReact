import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import './SuperAdminDashboard.css';

function SuperAdminDashboard() {
  const { user, isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (loading) return;

    if (!isAuthenticated || !user?.is_superuser) {
      navigate('/superadmin_login');
      return;
    }

    const token = localStorage.getItem('access_token');
    if (!token) {
      navigate('/superadmin_login');
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
        navigate('/superadmin_login');
      });
  }, [loading, isAuthenticated, user, navigate]);

  if (loading || !stats) {
    return <p className="superadmin-loading">Loading SuperAdmin dashboard...</p>;
  }

  return (
    <div className="superadmin-dashboard-page">
      <h2>SuperAdmin Dashboard</h2>

      <h3 className="superadmin-section-title">All Admins</h3>
      <table className="superadmin-admins-table">
        <thead>
          <tr>
            <th>Email</th>
            <th>Plan</th>
            <th>Price</th>
            <th>Next Billing Date</th>
          </tr>
        </thead>
        <tbody>
          {stats.admins.map((admin, idx) => {
            const isInactive = admin.plan === 'admin_inactive';

            return (
              <tr key={idx} className={isInactive ? 'row-inactive' : ''}>
                <td>{admin.email}</td>
                <td>
                  {admin.plan}
                  {admin.plan === 'admin_trial' && admin.cancelled && (
                    <span className="superadmin-cancelled-tag">
                      (Cancelled)
                    </span>
                  )}
                </td>
                <td>{admin.price || ''}</td>
                <td>{admin.next_billing || ''}</td>
              </tr>
            );
          })}
        </tbody>

      </table>

      <button
        onClick={() => {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          navigate('/superadmin_login');
        }}
        className="superadmin-logout-button"
      >
        Logout
      </button>
    </div>
  );
}

export default SuperAdminDashboard;
