import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../AdminTrialEnded/AdminTrialEnded.css';

function AdminTrialEnded() {
  const navigate = useNavigate();

  // clear session and redirect to login
  const handleLogout = () => {
    localStorage.removeItem('access');
    localStorage.removeItem('refresh');
    localStorage.removeItem('user_id');
    localStorage.removeItem('email');
    localStorage.removeItem('role');
    localStorage.removeItem('subscription_status');

    navigate('/admin_login');
  };

  return (
    <div className="trial-ended-wrapper">
      <h2 className="trial-ended-title">🚫 your admin access is inactive</h2>
      <p className="trial-ended-description">
        your free trial has ended or was cancelled. to continue using the dta dashboard and tools,
        you'll need to select a plan.
      </p>

      <div className="trial-ended-buttons">

        <button onClick={handleLogout} className="btn-logout">
          log out
        </button>
      </div>

      <p className="trial-ended-support">
        need help? contact support at <a href="mailto:support@dta.com">support@dta.com</a>
      </p>
    </div>
  );
}

export default AdminTrialEnded;

// summary:
// this page notifies the admin that their trial has ended
// logging out clears all local storage values and redirects the user to the login page.

