import React from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import './ClientAuthPages.css';

function ClientSignupSuccessPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const signupEmail = (searchParams.get('signup_email') || '').trim();
  const adminSlug = (searchParams.get('admin_slug') || '').trim();

  const plansPath = adminSlug ? `/start/${adminSlug}/plans` : '/user_plans';
  const loginPath = adminSlug ? `/start/${adminSlug}/login` : '/user_login';

  return (
    <div className="client-auth-page">
      <div className="client-auth-card">
        <h1>Signup Payment Successful</h1>
        <p className="client-auth-subtitle">
          Your Stripe checkout completed successfully.
        </p>
        <p className="client-auth-subtitle">
          Check your email {signupEmail ? <strong>{signupEmail}</strong> : ''} for your registration link to finish creating your account.
        </p>
        <p className="client-auth-subtitle">
          If you do not see it, check spam/junk and Promotions.
        </p>

        <div className="client-auth-links">
          <button type="button" onClick={() => navigate(plansPath)}>
            Back to Plans
          </button>
          <button type="button" onClick={() => navigate(loginPath)}>
            Existing Client Login
          </button>
        </div>
      </div>
    </div>
  );
}

export default ClientSignupSuccessPage;
