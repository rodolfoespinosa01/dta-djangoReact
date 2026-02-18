import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import './AdminDashboard.css';

function AdminDashboard() {
  const { isAuthenticated, accessToken, logout } = useAuth();
  const navigate = useNavigate();

  const [dashboardData, setDashboardData] = useState(null);
  const [status, setStatus] = useState('loading'); // 'loading' | 'ok' | 'blocked' | 'error'

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/admin_login');
      return;
    }

    const fetchDashboard = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/users/admin/dashboard/', {
          headers: { Authorization: `Bearer ${accessToken}` }
        });

        if (res.status === 401) { navigate('/admin_login'); return; }
        if (res.status === 403 || res.status === 404) { setStatus('blocked'); return; }

        let data = null;
        try { data = await res.json(); } catch { /* ignore */ }

        if (res.ok && data) {
          setDashboardData(data);
          setStatus('ok');
        } else {
          setStatus('error');
        }
      } catch (err) {
        console.error('Error loading dashboard data:', err);
        setStatus('error');
      }
    };

    fetchDashboard();
  }, [isAuthenticated, accessToken, navigate]);

  return (
    <div className="admin-dashboard-wrapper">
      <h1 className="admin-dashboard-title">🎯 Admin Dashboard</h1>
      <p className="admin-dashboard-subtitle">LETS GET YOUR CLIENTS IN PRIME SHAPE!</p>

      {status === 'loading' && (
        <p className="loading">Loading your subscription details...</p>
      )}

      {status === 'blocked' && (
        <div className="banner banner-canceled">
          <p>⚠️ Your plan is inactive.</p>
          <p>It looks like your free trial ended or your subscription has been canceled. To regain access, please reactivate.</p>
          <button className="btn btn-reactivate" onClick={() => navigate('/admin_reactivate')}>
            🔁 Reactivate
          </button>
        </div>
      )}

      {status === 'ok' && dashboardData && (
        <div className="admin-dashboard-card">
          {dashboardData.is_active ? (
            <p className="badge badge-active">✅ Your account is currently active.</p>
          ) : (
            <p className="error">⚠️ Your account is currently inactive.</p>
          )}

          {/* Safety: if API returned ok but user has no access (edge), show reactivation banner */}
          {dashboardData.is_active === false && (
            <div className="banner banner-canceled">
              <p>⚠️ Your account is currently inactive.</p>
              <button className="btn btn-reactivate" onClick={() => navigate('/admin_reactivate')}>
                🔁 Reactivate
              </button>
            </div>
          )}
        </div>
      )}

      {status === 'error' && (
        <p className="error">We couldn’t load your subscription details. Please try again.</p>
      )}

      <div className="actions">
        <button onClick={() => navigate('/admin_settings')} className="btn btn-primary">
          ⚙️ Account Settings
        </button>
        <button onClick={() => logout()} className="btn btn-danger">
          🚪 Logout
        </button>
      </div>
    </div>
  );
}

export default AdminDashboard;
