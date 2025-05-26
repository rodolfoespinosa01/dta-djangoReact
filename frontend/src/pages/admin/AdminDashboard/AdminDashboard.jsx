import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';

// import css specific to the admin dashboard
import './AdminDashboard.css';

function AdminDashboard() {
  const { user, isAuthenticated, accessToken, logout } = useAuth();
  const navigate = useNavigate();
  const [dashboardData, setDashboardData] = useState(null);
  const [daysLeft, setDaysLeft] = useState(null);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/admin_login');
      return;
    }

    if (user?.role === 'admin' && user?.is_canceled === true) {
      console.warn('🚫 Admin is canceled. Redirecting to reactivation...');
      navigate('/admin_reactivate');
      return;
    }

    const fetchDashboard = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/users/admin/dashboard/', {
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        });

        const data = await res.json();
        if (res.ok) {
          setDashboardData(data);
          if (data.trial_active) {
            setDaysLeft(data.days_remaining);
          }
        }
      } catch (err) {
        console.error('Error loading dashboard data:', err);
      }
    };

    fetchDashboard();
  }, [isAuthenticated, accessToken, user, navigate]);

  const formatDate = (dateStr) => {
    return dateStr ? new Date(dateStr).toLocaleDateString() : '—';
  };

  const subscriptionLabels = {
    admin_trial: 'Free Trial',
    admin_monthly: 'Monthly Plan',
    admin_quarterly: 'Quarterly Plan',
    admin_annual: 'Annual Plan',
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '720px', margin: '0 auto', fontFamily: 'Arial, sans-serif' }}>
      <h1 style={{ textAlign: 'center' }}>🎯 Admin Dashboard</h1>
      <p style={{ textAlign: 'center' }}>
        Your all-in-one platform for generating tailored diet plans for your clients.
      </p>

      {dashboardData ? (
        <div
          style={{
            marginTop: '2rem',
            padding: '1.5rem',
            backgroundColor: '#f1f5f9',
            border: '1px solid #cbd5e1',
            borderRadius: '10px',
          }}
        >
          <h2 style={{ marginBottom: '1rem' }}>📊 Subscription Summary</h2>

          <ul style={{ listStyle: 'none', paddingLeft: 0, lineHeight: 1.6 }}>
            <li><strong>Plan:</strong> {subscriptionLabels[dashboardData.subscription_status]}</li>

            {dashboardData.trial_start && (
              <li><strong>Trial Started:</strong> {formatDate(dashboardData.trial_start)}</li>
            )}
            {dashboardData.monthly_start && (
              <li><strong>Monthly Plan Start:</strong> {formatDate(dashboardData.monthly_start)}</li>
            )}
            {dashboardData.quarterly_start && (
              <li><strong>Quarterly Plan Start:</strong> {formatDate(dashboardData.quarterly_start)}</li>
            )}
            {dashboardData.annual_start && (
              <li><strong>Annual Plan Start:</strong> {formatDate(dashboardData.annual_start)}</li>
            )}
            {dashboardData.next_billing_date && (
              <li><strong>Next Billing:</strong> {formatDate(dashboardData.next_billing_date)}</li>
            )}
          </ul>

          {dashboardData.is_trial && daysLeft !== null && (
            <p style={{ marginTop: '1rem', color: '#d97706', fontWeight: 'bold' }}>
              ⏳ Trial Days Remaining: {daysLeft}
            </p>
          )}

          {dashboardData.subscription_active && !dashboardData.is_canceled && (
            <p style={{ marginTop: '1rem', color: '#22c55e', fontWeight: 'bold' }}>
              ✅ Your subscription is active and set to renew.
            </p>
          )}

          {dashboardData.is_canceled && dashboardData.subscription_end_date && (
            <p style={{ marginTop: '1rem', color: '#ef4444' }}>
              ⚠️ Your subscription has been canceled. Access ends on: <strong>{formatDate(dashboardData.subscription_end_date)}</strong>
            </p>
          )}
        </div>
      ) : (
        <p style={{ marginTop: '2rem', textAlign: 'center', color: '#64748b' }}>
          Loading your subscription details...
        </p>
      )}

      <div style={{ marginTop: '2.5rem', textAlign: 'center' }}>
        <button
          onClick={() => navigate('/admin_settings')}
          style={{
            marginRight: '1rem',
            padding: '0.75rem 1.5rem',
            backgroundColor: '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '1rem'
          }}
        >
          ⚙️ Account Settings
        </button>

        <button
          onClick={logout}
          style={{
            padding: '0.75rem 1.5rem',
            backgroundColor: '#ef4444',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '1rem'
          }}
        >
          🚪 Logout
        </button>
      </div>
    </div>
  );
}

export default AdminDashboard;

// admin dashboard page
// this component displays the logged-in admin's subscription status, including plan type, start dates, billing info, and trial countdown.
// on component mount, it sends a GET request to /api/users/admin/dashboard/ with the jwt access token in the header.
// the backend responds with subscription data, which is stored in local state and conditionally rendered based on trial or plan status.