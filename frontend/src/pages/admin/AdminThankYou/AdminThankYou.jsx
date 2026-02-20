import React, { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useLanguage } from '../../../context/LanguageContext';
import './AdminThankYou.css';

function AdminThankYou() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { t } = useLanguage();

  // redirect to home if no stripe session ID is found
  useEffect(() => {
    const sessionId = searchParams.get('session_id');
    if (!sessionId) {
      console.warn('no stripe session id found. redirecting...');
      navigate('/');
    }
  }, [searchParams, navigate]);

  return (
    <div className="admin-thankyou-wrapper">
      <h1 className="admin-thankyou-title">🎉 {t('admin_thank_you.title')}</h1>
      <p className="admin-thankyou-text">{t('admin_thank_you.text1')}</p>
      <p className="admin-thankyou-text">{t('admin_thank_you.text2')}</p>
    </div>
  );
}

export default AdminThankYou;

// summary:
// this page confirms successful stripe checkout and instructs the user to check their email to complete account setup.
// it verifies that a stripe session ID exists in the url before showing the thank you message.
// if the session ID is missing, the user is redirected to the homepage.
