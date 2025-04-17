import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

function AdminSettings() {
  const { user, isAuthenticated, accessToken } = useAuth();
  const navigate = useNavigate();

  const [daysLeft, setDaysLeft] = useState(null);
  const [cancelled, setCancelled] = useState(false);
  const [cancelMessage, setCancelMessage] = useState('');

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/admin-login');
      return;
    }

    const fetchTrialStatus = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/users/admin-dashboard/', {
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        });

        const data = await res.json();
        if (res.ok && data.trial_active) {
          setDaysLeft(data.days_remaining);
        } else if (res.status === 403) {
          setDaysLeft(null);
        }
      } catch (err) {
        console.error('Error fetching trial info:', err);
      }
    };

    fetchTrialStatus();
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

        // Re-fetch dashboard to reflect new trial state
        const refreshRes = await fetch('http://localhost:8000/api/users/admin-dashboard/', {
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        });

        const refreshData = await refreshRes.json();
        if (!refreshData.trial_active) {
          setDaysLeft(null);
        }
      } else {
        setCancelMessage(data.error || 'Failed to cancel auto-renew.');
      }
    } catch (err) {
      console.error('Cancel error:', err);
      setCancelMessage('Network error.');
    }
  };

  return (
    <div style={{ padding: '2rem' }}>
      <h2>Admin Settings</h2>
      {user && <p>Settings for: {user.email}</p>}

      {/* Show Trial Details + Cancel Option */}
      {user?.subscription_status === 'admin_trial' && (
        <>
          {daysLeft !== null && (
            <p style={{ marginTop: '1rem' }}>⏳ Trial Days Left: <strong>{daysLeft}</strong></p>
          )}

          {!cancelled ? (
            <button
              onClick={handleCancelAutoRenew}
              style={{ marginTop: '1rem', backgroundColor: '#fbbf24', padding: '0.5rem 1rem', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
            >
              Cancel Trial Auto-Renewal
            </button>
          ) : (
            <p style={{ marginTop: '1rem', color: 'green' }}>{cancelMessage}</p>
          )}
        </>
      )}

      {/* Fallback message for non-trial users */}
      {user?.subscription_status !== 'admin_trial' && (
        <p style={{ marginTop: '1rem', color: 'gray' }}>
          You are not currently on a free trial. To reactivate your account, please purchase a monthly or annual plan.
        </p>
      )}
    </div>
  );
}

export default AdminSettings;
