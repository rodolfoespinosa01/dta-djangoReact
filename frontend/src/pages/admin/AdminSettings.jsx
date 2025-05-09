import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

function AdminSettings() {
  const { user, isAuthenticated, accessToken } = useAuth();
  const navigate = useNavigate();

  const [dashboardData, setDashboardData] = useState(null);
  const [cancelMessage, setCancelMessage] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/admin_login');
      return;
    }

    const fetchDashboardData = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/users/admin/dashboard/', {
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        });

        const data = await res.json();
        if (res.ok) {
          setDashboardData(data);
        }
      } catch (err) {
        console.error('Error fetching dashboard info:', err);
      }
    };

    fetchDashboardData();
  }, [accessToken, isAuthenticated, navigate]);

  const handleCancelAutoRenew = async () => {
    try {
      setLoading(true);
      const res = await fetch('http://localhost:8000/api/users/admin/cancel_subscription/', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      const data = await res.json();
      setCancelMessage(res.ok ? data.message : data.error || 'Failed to cancel.');

      const refresh = await fetch('http://localhost:8000/api/users/admin/dashboard/', {
        headers: { Authorization: `Bearer ${accessToken}` }
      });

      const refreshData = await refresh.json();
      setDashboardData(refreshData);
    } catch (err) {
      console.error('Cancel error:', err);
      setCancelMessage('Network error.');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (str) => str ? new Date(str).toLocaleDateString() : '—';

  const subscriptionLabels = {
    admin_trial: 'Free Trial',
    admin_monthly: 'Monthly Plan',
    admin_quarterly: 'Quarterly Plan',
    admin_annual: 'Annual Plan'
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '700px', margin: '0 auto' }}>
      <h2>⚙️ Admin Settings</h2>
      {user?.email && (
        <p style={{ marginBottom: '1rem', color: '#6b7280' }}>
          Logged in as: <strong>{user.email}</strong>
        </p>
      )}

      {dashboardData ? (
        <div
          style={{
            backgroundColor: '#f9fafb',
            border: '1px solid #e5e7eb',
            padding: '1.5rem',
            borderRadius: '8px',
          }}
        >
          <h3>📄 Subscription Info</h3>
          <p><strong>Plan:</strong> {subscriptionLabels[dashboardData.subscription_status]}</p>

          {dashboardData.trial_start && (
            <p><strong>Trial Start Date:</strong> {formatDate(dashboardData.trial_start)}</p>
          )}
          {dashboardData.monthly_start && (
            <p><strong>Monthly Start Date:</strong> {formatDate(dashboardData.monthly_start)}</p>
          )}
          {dashboardData.quarterly_start && (
            <p><strong>Quarterly Start Date:</strong> {formatDate(dashboardData.quarterly_start)}</p>
          )}
          {dashboardData.annual_start && (
            <p><strong>Annual Start Date:</strong> {formatDate(dashboardData.annual_start)}</p>
          )}

          {dashboardData.is_trial && dashboardData.days_remaining !== null && (
            <p style={{ marginTop: '0.5rem', color: '#d97706' }}>
              ⏳ Trial Days Left: <strong>{dashboardData.days_remaining}</strong>
            </p>
          )}

          {dashboardData.next_billing_date && dashboardData.subscription_active && (
            <p style={{ marginTop: '0.5rem' }}>
              <strong>Next Billing Date:</strong> {formatDate(dashboardData.next_billing_date)}
            </p>
          )}

          {dashboardData.subscription_active && !dashboardData.is_canceled && (
            <p style={{ marginTop: '0.75rem', color: '#16a34a' }}>
              ✅ Your subscription is active and set to auto-renew.
            </p>
          )}

          {dashboardData.is_canceled && dashboardData.subscription_end_date && (
            <p style={{ marginTop: '0.75rem', color: '#dc2626' }}>
              🔒 Your plan is canceled. Access ends on <strong>{formatDate(dashboardData.subscription_end_date)}</strong>
            </p>
          )}

          {/* 🔘 Actions */}
          <div style={{ marginTop: '1.5rem' }}>
            {!dashboardData.is_canceled && dashboardData.subscription_active && (
              <button
                onClick={handleCancelAutoRenew}
                disabled={loading}
                style={{
                  backgroundColor: '#ef4444',
                  color: 'white',
                  padding: '0.6rem 1.25rem',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
              >
                {loading ? 'Processing...' : 'Cancel Subscription'}
              </button>
            )}

            {dashboardData.is_canceled && dashboardData.reactivation_pending && (
              <p style={{ color: '#2563eb', marginTop: '1rem' }}>
                🔄 New plan scheduled to start: <strong>{formatDate(dashboardData.reactivation_start_date)}</strong>
              </p>
            )}

            {dashboardData.is_canceled && !dashboardData.reactivation_pending && (
              <button
                onClick={() => navigate('/admin_reactivate')}
                style={{
                  marginTop: '1rem',
                  backgroundColor: '#10b981',
                  color: 'white',
                  padding: '0.6rem 1.25rem',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
              >
                Reactivate Subscription
              </button>
            )}
          </div>

          {cancelMessage && (
            <p style={{ marginTop: '1rem', color: 'green' }}>{cancelMessage}</p>
          )}
        </div>
      ) : (
        <p style={{ marginTop: '2rem', color: '#9ca3af' }}>
          Unable to load your subscription details.
        </p>
      )}

      <button
        onClick={() => navigate('/admin_dashboard')}
        style={{
          marginTop: '2rem',
          backgroundColor: '#2563eb',
          color: 'white',
          padding: '0.75rem 1.5rem',
          border: 'none',
          borderRadius: '6px',
          cursor: 'pointer'
        }}
      >
        ← Back to Dashboard
      </button>
    </div>
  );
}

export default AdminSettings;
