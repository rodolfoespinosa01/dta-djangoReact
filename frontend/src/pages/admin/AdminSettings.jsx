import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

function AdminSettings() {
  const { user, isAuthenticated, accessToken } = useAuth();
  const navigate = useNavigate();

  const [dashboardData, setDashboardData] = useState(null);
  const [cancelled, setCancelled] = useState(false);
  const [cancelMessage, setCancelMessage] = useState('');

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/admin-login');
      return;
    }

    const fetchDashboardData = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/users/admin-dashboard/', {
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        });

        const data = await res.json();
        console.log("DASHBOARD DATA:", data);
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
  }, [accessToken, isAuthenticated, navigate]);

  const handleCancelAutoRenew = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/users/admin/cancel-auto-renew/', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      const data = await res.json();

      if (res.ok) {
        setCancelled(true);
        setCancelMessage(data.message);

        // Refresh dashboard state
        const refreshRes = await fetch('http://localhost:8000/api/users/admin-dashboard/', {
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        });

        const refreshData = await refreshRes.json();
        setDashboardData(refreshData);
      } else {
        setCancelMessage(data.error || 'Failed to cancel auto-renew.');
      }
    } catch (err) {
      console.error('Cancel error:', err);
      setCancelMessage('Network error.');
    }
  };

  const formatDate = (dateStr) => {
    return dateStr ? new Date(dateStr).toLocaleDateString() : null;
  };

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

  return (
    <div style={{ padding: '2rem' }}>
      <h2>Admin Settings</h2>
  
      {/* Show Admin Email */}
      {user?.email && <p>Settings for: <strong>{user.email}</strong></p>}
  
      {/* Only render when we have data */}
      {dashboardData && (
        <>
          {/* Start Date */}
          {renderStartDate()}
  
          {/* Trial Days Remaining */}
          {dashboardData.subscription_status === 'admin_trial' && dashboardData.days_remaining !== null && (
            <p>⏳ Trial Days Left: <strong>{dashboardData.days_remaining}</strong></p>
          )}
  
          {/* Next Billing Date */}
          {dashboardData.subscription_active && dashboardData.next_billing_date && (
            <p><strong>Next Billing Date:</strong> {formatDate(dashboardData.next_billing_date)}</p>
          )}
  
          {/* Cancel Subscription */}
          {!cancelled ? (
            <button
              onClick={handleCancelAutoRenew}
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
          ) : (
            <p style={{ marginTop: '1rem', color: 'green' }}>{cancelMessage}</p>
          )}
        </>
      )}
  
      {!dashboardData && (
        <p style={{ marginTop: '1rem', color: 'gray' }}>
          Unable to load subscription details.
        </p>
      )}
  
      {/* Back to Dashboard Button */}
      <button
        onClick={() => navigate('/admin-dashboard')}
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
