import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../../../context/LanguageContext';
import '../AdminTrialEnded/AdminTrialEnded.css';

function AdminTrialEnded() {
  const navigate = useNavigate();
  const { t } = useLanguage();

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
      <h2 className="trial-ended-title">🚫 {t('admin_trial_ended.title')}</h2>
      <p className="trial-ended-description">{t('admin_trial_ended.description')}</p>

      <div className="trial-ended-buttons">

        <button onClick={handleLogout} className="btn-logout">
          {t('admin_trial_ended.logout')}
        </button>
      </div>

      <p className="trial-ended-support">
        {t('admin_trial_ended.support')} <a href="mailto:support@dta.com">support@dta.com</a>
      </p>
    </div>
  );
}

export default AdminTrialEnded;

// summary:
// this page notifies the admin that their trial has ended
// logging out clears all local storage values and redirects the user to the login page.
