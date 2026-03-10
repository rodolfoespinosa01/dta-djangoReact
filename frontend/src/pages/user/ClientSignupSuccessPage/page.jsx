import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiRequest } from '../../../api/client';
import '../../../styles/shared/auth-flow.css';
import './css.css';

function ClientSignupSuccessPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const sessionId = (searchParams.get('session_id') || '').trim();
  const signupEmail = (searchParams.get('signup_email') || '').trim();
  const adminSlug = (searchParams.get('admin_slug') || '').trim();

  const plansPath = adminSlug ? `/start/${adminSlug}/plans` : '/user_plans';
  const loginPath = adminSlug ? `/start/${adminSlug}/login` : '/user_login';

  useEffect(() => {
    if (process.env.NODE_ENV !== 'development') return undefined;
    if (!sessionId) return undefined;

    let isCancelled = false;
    let timeoutId = null;
    let attempts = 0;
    const maxAttempts = 6;

    const pollDebugLink = async () => {
      if (isCancelled) return;
      attempts += 1;
      console.log('Fetching stored registration link...');
      const response = await apiRequest(`/api/v1/users/client/signup/checkout-debug-link/?session_id=${encodeURIComponent(sessionId)}`);
      if (isCancelled) return;

      console.log('Success page response:', response);

      if (response?.data?.status === 'ready' && response?.data?.debug_registration_link) {
        console.log('Registration Link:', response.data.debug_registration_link);
        return;
      }

      if (response?.data?.status === 'pending' && attempts < maxAttempts) {
        timeoutId = window.setTimeout(() => {
          pollDebugLink().catch((err) => {
            if (!isCancelled) console.error('Unable to fetch stored registration link:', err);
          });
        }, 1000);
      }
    };

    pollDebugLink().catch((err) => {
      if (!isCancelled) console.error('Unable to fetch stored registration link:', err);
    });

    return () => {
      isCancelled = true;
      if (timeoutId) window.clearTimeout(timeoutId);
    };
  }, [sessionId]);

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
