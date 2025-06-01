import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import './AdminSettings.css';

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
          headers: { Authorization: `Bearer ${accessToken}` }
        });

        const data = await res.json();
        if (res.ok) {
          setDashboardData(data);
        }
      } catch (err) {
        console.error('error fetching dashboard info:', err);
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
      setCancelMessage(res.ok ? data.message : data.error || 'failed to cancel.');

      const refresh = await fetch('http://localhost:8000/api/users/admin/dashboard/', {
        headers: { Authorization: `Bearer ${accessToken}` }
      });

      const refreshData = await refresh.json();
      setDashboardData(refreshData);
    } catch (err) {
      console.error('cancel error:', err);
      setCancelMessage('network error.');
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
    <div className="admin-settings-wrapper">
      <h2>⚙️ admin settings</h2>
      {user?.email && (
        <p className="admin-settings-email">
          logged in as: <strong>{user.email}</strong>
        </p>
      )}

      {dashboardData ? (
        <div className="admin-settings-card">
          <h3>📄 subscription info</h3>
          <p><strong>plan:</strong> {subscriptionLabels[dashboardData.subscription_status]}</p>

          {dashboardData.trial_start && (
            <p><strong>trial start date:</strong> {formatDate(dashboardData.trial_start)}</p>
          )}
          {dashboardData.monthly_start && (
            <p><strong>monthly start date:</strong> {formatDate(dashboardData.monthly_start)}</p>
          )}
          {dashboardData.quarterly_start && (
            <p><strong>quarterly start date:</strong> {formatDate(dashboardData.quarterly_start)}</p>
          )}
          {dashboardData.annual_start && (
            <p><strong>annual start date:</strong> {formatDate(dashboardData.annual_start)}</p>
          )}

          {dashboardData.is_trial && dashboardData.days_remaining !== null && (
            <p className="trial-days-left">
              ⏳ trial days left: <strong>{dashboardData.days_remaining}</strong>
            </p>
          )}

          {dashboardData.next_billing && dashboardData.subscription_active && (
            <p><strong>next billing date:</strong> {formatDate(dashboardData.next_billing)}</p>
          )}

          {dashboardData.subscription_active && !dashboardData.is_canceled && (
            <p className="subscription-active">
              ✅ your subscription is active and set to auto-renew.
            </p>
          )}

          {dashboardData.is_canceled && dashboardData.subscription_end && (
            <p className="subscription-canceled">
              🔒 your plan is canceled. access ends on <strong>{formatDate(dashboardData.subscription_end)}</strong>
            </p>
          )}

          <div className="admin-settings-actions">
            {!dashboardData.is_canceled && dashboardData.subscription_active && (
              <button
                onClick={handleCancelAutoRenew}
                disabled={loading}
                className="btn-cancel"
              >
                {loading ? 'processing...' : 'cancel subscription'}
              </button>
            )}

          </div>

          {cancelMessage && (
            <p className="cancel-message">{cancelMessage}</p>
          )}
        </div>
      ) : (
        <p className="load-error">unable to load your subscription details.</p>
      )}

      <button onClick={() => navigate('/admin_dashboard')} className="btn-back">
        ← back to dashboard
      </button>
    </div>
  );
}

export default AdminSettings;

// summary:
// this page shows the admin's subscription details and provides options to cancel auto-renew 
// it fetches subscription data from the dashboard api, handles cancel requests, and reflects changes in real time.
