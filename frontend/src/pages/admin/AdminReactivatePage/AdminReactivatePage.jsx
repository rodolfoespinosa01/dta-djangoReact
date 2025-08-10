import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import './AdminReactivatePage.css';

function AdminReactivatePage() {
  const { accessToken, logout } = useAuth();
  const navigate = useNavigate();
  const [selectedPlan, setSelectedPlan] = useState('adminMonthly');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);



  // handle reactivation button click
  const handleReactivate = async () => {
    setLoading(true);
    setError(null);

    try {
      const res = await fetch('http://localhost:8000/api/users/admin/reactivate_checkout/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ plan_name: selectedPlan }),
      });

      const data = await res.json();

      if (res.ok && data.url) {
        window.location.href = data.url;
      } else {
        setError(data.error || 'something went wrong.');
        setLoading(false);
      }
    } catch (err) {
      console.error('error:', err);
      setError('network error.');
      setLoading(false);
    }
  };

  return (
    <div className="admin-reactivate-wrapper">
      <div className="admin-reactivate-card">
        <h2 className="admin-reactivate-title">🔄 reactivate your admin subscription</h2>
        <p className="admin-reactivate-description">
          select a plan to resume your access. your new billing cycle will start based on your current subscription status.
        </p>

        <label className="admin-reactivate-label">
          choose a plan:
        </label>
        <select
          value={selectedPlan}
          onChange={(e) => setSelectedPlan(e.target.value)}
          className="admin-reactivate-select"
        >
          <option value="adminMonthly">📆 monthly – $29/month</option>
          <option value="adminQuarterly">📅 quarterly – $75/quarter</option>
          <option value="adminAnnual">📈 annual – $250/year</option>
        </select>

        <button
          onClick={handleReactivate}
          disabled={loading}
          className="admin-reactivate-button"
        >
          {loading ? 'redirecting to stripe...' : 'reactivate plan'}
        </button>

        {error && (
          <p className="admin-reactivate-error">{error}</p>
        )}

        <div className="admin-reactivate-footer">
          <button onClick={() => navigate('/admin_settings')} className="admin-reactivate-settings-btn">
            back to settings
          </button>
          <button onClick={() => logout()} className="admin-reactivate-logout-btn">
            log out
          </button>
        </div>
      </div>
    </div>
  );
}

export default AdminReactivatePage;


// summary:
// this page allows canceled or inactive admins to reactivate their subscription by selecting a new paid plan.
// it sends a POST request to /api/users/admin/reactivate_checkout/ with the selected plan and jwt token, then redirects to stripe checkout if successful.
// if the request fails or there's a network issue, an error message is shown to the user.
