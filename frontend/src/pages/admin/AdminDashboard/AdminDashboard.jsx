import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import './AdminDashboard.css';

function AdminDashboard() {
  const { isAuthenticated, accessToken, logout } = useAuth();
  const navigate = useNavigate();

  const [dashboardData, setDashboardData] = useState(null);
  const [daysLeft, setDaysLeft] = useState(null);
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
          if ((data.is_trial || data.trial_active) && typeof data.days_remaining === 'number') {
            setDaysLeft(data.days_remaining);
          }
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

  const formatDate = (d) => (d ? new Date(d).toLocaleDateString() : '—');

  const subscriptionLabels = {
    admin_trial: 'Free Trial',
    admin_monthly: 'Monthly Plan',
    admin_quarterly: 'Quarterly Plan',
    admin_annual: 'Annual Plan',
  };

  // Shows renewal/cancel state based on is_canceled
  const RenewalBadge = ({ data }) => {
    if (!data) return null;
    if (data.is_active === false) return null; // banner handles inactive

    if (!data.is_canceled) {
      return <p className="badge badge-active">✅ Your subscription is active and set to auto-renew.</p>;
    }
    if (data.is_canceled && data.subscription_end) {
      return (
        <div className="banner">
          <p>ℹ️ Auto-renew is <strong>off</strong>. You keep access until <strong>{formatDate(data.subscription_end)}</strong>.</p>
          <button className="btn btn-reactivate" onClick={() => navigate('/admin_reactivate')}>
            🔁 Reactivate (turn auto-renew on)
          </button>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="admin-dashboard-wrapper">
      <h1 className="admin-dashboard-title">🎯 Admin Dashboard</h1>
      <p className="admin-dashboard-subtitle">
        Your all-in-one platform for generating tailored diet plans for your clients.
      </p>

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
          <h2 className="admin-dashboard-section-title">📊 Subscription Summary</h2>

          <ul className="summary-list">
            <li><span className="label">Plan:</span> {subscriptionLabels[dashboardData.subscription_status] || '—'}</li>

            {dashboardData.trial_start && (
              <li><span className="label">Trial Started:</span> {formatDate(dashboardData.trial_start)}</li>
            )}
            {dashboardData.monthly_start && (
              <li><span className="label">Monthly Plan Start:</span> {formatDate(dashboardData.monthly_start)}</li>
            )}
            {dashboardData.quarterly_start && (
              <li><span className="label">Quarterly Plan Start:</span> {formatDate(dashboardData.quarterly_start)}</li>
            )}
            {dashboardData.annual_start && (
              <li><span className="label">Annual Plan Start:</span> {formatDate(dashboardData.annual_start)}</li>
            )}

            {/* Show one of these depending on renewal state */}
            {dashboardData.next_billing && !dashboardData.is_canceled && (
              <li><span className="label">Next Billing:</span> {formatDate(dashboardData.next_billing)}</li>
            )}
            {dashboardData.is_canceled && dashboardData.subscription_end && (
              <li><span className="label">Access Until:</span> {formatDate(dashboardData.subscription_end)}</li>
            )}
          </ul>

          {(dashboardData.is_trial || dashboardData.trial_active) && daysLeft !== null && (
            <p className="badge badge-trial">⏳ Trial Days Remaining: {daysLeft}</p>
          )}

          {/* Renewal / scheduled-end messaging */}
          <RenewalBadge data={dashboardData} />

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
