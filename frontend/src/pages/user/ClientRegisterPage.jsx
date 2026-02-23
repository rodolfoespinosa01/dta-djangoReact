import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiRequest } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import GoogleSignInButton from '../../components/auth/GoogleSignInButton';
import './ClientAuthPages.css';

function ClientRegisterPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';

  const [prefill, setPrefill] = useState(null);
  const [status, setStatus] = useState('loading');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const isGmailEmail = /@gmail\.com$|@googlemail\.com$/i.test((email || '').trim());

  useEffect(() => {
    let ignore = false;
    const load = async () => {
      if (!token) {
        setStatus('error');
        setMessage('Missing registration token.');
        return;
      }
      const res = await apiRequest(`/api/v1/users/client/pending-signup/${token}/`);
      if (ignore) return;
      if (!res.ok) {
        setStatus('error');
        setMessage(res.data?.error?.message || 'Invalid registration link.');
        return;
      }
      const pending = res.data?.pending_signup;
      setPrefill(pending);
      setEmail(pending?.email || '');
      setStatus('ready');
    };
    load().catch((err) => {
      console.error(err);
      if (!ignore) {
        setStatus('error');
        setMessage('Unable to load registration link.');
      }
    });
    return () => { ignore = true; };
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isGmailEmail) {
      setMessage('Gmail accounts must continue with Google.');
      return;
    }
    setSubmitting(true);
    setMessage('');
    try {
      const res = await apiRequest('/api/v1/users/client/register/', {
        method: 'POST',
        body: { email, password, token },
      });
      if (!res.ok) {
        setMessage(res.data?.error?.message || 'Unable to create account.');
        return;
      }
      login(res.data);
      navigate('/client_dashboard', { replace: true });
    } catch (err) {
      console.error(err);
      setMessage('Network error while creating account.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoogleCredential = async (credential) => {
    setSubmitting(true);
    setMessage('');
    try {
      const res = await apiRequest('/api/v1/users/client/register/', {
        method: 'POST',
        body: { email, token, credential },
      });
      if (!res.ok) {
        setMessage(res.data?.error?.message || 'Unable to create account with Google.');
        return;
      }
      login(res.data);
      navigate('/client_dashboard', { replace: true });
    } catch (err) {
      console.error(err);
      setMessage('Network error while creating account with Google.');
    } finally {
      setSubmitting(false);
    }
  };

  if (status === 'loading') return <div className="client-auth-page"><p>Loading registration link…</p></div>;

  if (status === 'error') {
    return (
      <div className="client-auth-page">
        <div className="client-auth-card">
          <h1>Client Registration</h1>
          <p className="client-auth-error">{message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="client-auth-page">
      <form className="client-auth-card" onSubmit={handleSubmit}>
        <h1>Create Your Account</h1>
        <p className="client-auth-subtitle">
          Offer: {prefill?.offer_code} {prefill?.trial_days ? `• ${prefill.trial_days}-day free trial` : ''}
        </p>
        <p className="client-auth-subtitle">
          Use the same email shown below.
        </p>
        {isGmailEmail ? (
          <p className="client-auth-subtitle">Gmail account detected. Google signup is required to create this account.</p>
        ) : (
          <p className="client-auth-subtitle">Create a password to register. Google is also available if you want to use it now.</p>
        )}
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <div className="client-auth-divider"><span>{isGmailEmail ? 'Continue with Google' : 'Optional Google signup'}</span></div>
        <GoogleSignInButton onCredential={handleGoogleCredential} disabled={submitting} label="Continue with Google" />
        {!isGmailEmail && (
          <>
            <div className="client-auth-divider"><span>Create with password</span></div>
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={8}
                required
              />
            </label>
            <button type="submit" disabled={submitting}>
              {submitting ? 'Creating Account…' : 'Create Account'}
            </button>
          </>
        )}
        {message && <p className="client-auth-error">{message}</p>}
      </form>
    </div>
  );
}

export default ClientRegisterPage;
