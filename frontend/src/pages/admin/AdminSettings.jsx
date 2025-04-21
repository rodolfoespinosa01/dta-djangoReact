import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

function AdminSettings() {
  const { user, isAuthenticated, accessToken } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [dashboardData, setDashboardData] = useState(null);
  const [cancelMessage, setCancelMessage] = useState('');

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/admin-login');
      return;
    }

    const fetchDashboardData = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/adminplans/admin_dashboard/', {
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
        if (res.ok) {
          setDashboardData(data);
        } else {
          setDashboardData(null);
        }
      } catch (err) {
        console.error('Error fetching dashboard info:', err);
        setDashboardData(null);
      }
    };

    fetchDashboardData();
  }, [accessToken, isAuthenticated, navigate, location]);

  const handleCancelSubscription = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/adminplans/admin_cancel_subscription/', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      const data = await res.json();

      if (res.ok) {
        setCancelMessage(data.message);
        const refreshRes = await fetch('http://localhost:8000/api/adminplans/admin_dashboard/', {
          headers: { Authorization: `Bearer ${accessToken}` }
        });
        const refreshData = await refreshRes.json();
        setDashboardData(refreshData);
      } else {
        setCancelMessage(data.error || 'Failed to cancel subscription.');
      }
    } catch (err) {
      console.error('Cancel error:', err);
      setCancelMessage('Network error.');
    }
  };

  const formatDate = (dateStr) => dateStr ? new Date(dateStr).toLocaleDateString() : null;

  const renderStartDate = () => {
    const plan = dashboardData?.subscription_status;
    const starts = {
      admin_trial: dashboardData?.trial_start,
      admin_monthly: dashboardData?.monthly_start,
      admin_quarterly: dashboardData?.quarterly_start,
      admin_annual: dashboardData?.annual_start,
    };

    const labelMap = {
      admin_trial: 'Trial Start Date',
      admin_monthly: 'Monthly Plan Start Date',
      admin_quarterly: 'Quarterly Plan Start Date',
      admin_annual: 'Annual Plan Start Date',
    };

    const startDate = formatDate(starts[plan]);
    const label = labelMap[plan];

    return startDate && label ? (
      <p><strong>{label}:</strong> {startDate}</p>
    ) : null;
  };

  const isWithinBillingCycle = () => {
    const endDate = dashboardData?.subscription_end_date;
    if (!endDate) return false;
    return new Date(endDate) > new Date();
  };

  return (
    <div style={{ padding: '2rem' }}>
      <h2>Admin Settings</h2>

      {user?.email && <p>Settings for: <strong>{user.email}</strong></p>}

      {dashboardData && (
        <>
          {renderStartDate()}

          {dashboardData.subscription_status === 'admin_trial' && dashboardData.days_remaining !== null && (
            <p>⏳ Trial Days Left: <strong>{dashboardData.days_remaining}</strong></p>
          )}

          {dashboardData.subscription_active && dashboardData.next_billing_date && (
            <p><strong>Next Billing Date:</strong> {formatDate(dashboardData.next_billing_date)}</p>
          )}

          {dashboardData.is_canceled && dashboardData.subscription_end_date && (
            <div style={{
              backgroundColor: '#fee2e2',
              padding: '1rem',
              borderRadius: '6px',
              marginTop: '1rem',
              border: '1px solid #dc2626'
            }}>
              <p style={{ margin: 0, color: '#991b1b', fontWeight: 'bold' }}>
                🛑 Your subscription will end on <strong>{formatDate(dashboardData.subscription_end_date)}</strong>.
              </p>
            </div>
          )}

          {/* Cancel and Reactivate Logic */}
          {dashboardData.subscription_active && !dashboardData.is_canceled && (
            <button
              onClick={handleCancelSubscription}
              style={{
                marginTop: '1rem',
                backgroundColor: '#ef4444',
                color: 'white',
                padding: '0.5rem 1rem',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Cancel Subscription
            </button>
          )}

          {/* Only show if canceled AND still in billing cycle */}
          {dashboardData.is_canceled && isWithinBillingCycle() && (
            <button
              onClick={() => navigate('/admin_reactivate')}
              style={{
                marginTop: '1rem',
                backgroundColor: '#10b981',
                color: 'white',
                padding: '0.5rem 1rem',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Reactivate Subscription
            </button>
          )}

          {cancelMessage && (
            <p style={{ marginTop: '1rem', color: 'green' }}>{cancelMessage}</p>
          )}
        </>
      )}

      {!dashboardData && (
        <p style={{ marginTop: '1rem', color: 'gray' }}>
          Unable to load subscription details.
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
        Back to Dashboard
      </button>
    </div>
  );
}

export default AdminSettings;