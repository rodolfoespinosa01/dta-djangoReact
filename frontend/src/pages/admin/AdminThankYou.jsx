import React, { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';

function AdminThankYou() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const sessionId = searchParams.get('session_id');

    // Optional: basic confirmation the user came from Stripe
    if (!sessionId) {
      console.warn('No Stripe session ID found. Redirecting...');
      navigate('/');
    }
  }, [searchParams, navigate]);

  return (
    <div style={{ textAlign: 'center', padding: '3rem' }}>
      <h1>🎉 Thank you for signing up!</h1>
      <p>Your registration is almost complete.</p>
      <p>Please check your email for the link to finish setting up your admin account.</p>
    </div>
  );
}

export default AdminThankYou;
