import React, { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import './AdminThankYou.css';

function AdminThankYou() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

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
      <h1 className="admin-thankyou-title">🎉 thank you for signing up!</h1>
      <p className="admin-thankyou-text">your registration is almost complete.</p>
      <p className="admin-thankyou-text">please check your email for the link to finish setting up your admin account.</p>
    </div>
  );
}

export default AdminThankYou;

// summary:
// this page confirms successful stripe checkout and instructs the user to check their email to complete account setup.
// it verifies that a stripe session ID exists in the url before showing the thank you message.
// if the session ID is missing, the user is redirected to the homepage.
