import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { apiRequest } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import GoogleSignInButton from '../../components/auth/GoogleSignInButton';
import './ClientAuthPages.css';

function ClientLoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const isGmailEmail = /@gmail\.com$|@googlemail\.com$/i.test((email || '').trim());

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isGmailEmail) {
      setMessage('Gmail accounts must use Google sign-in.');
      return;
    }
    setSubmitting(true);
    setMessage('');
    try {
      const res = await apiRequest('/api/v1/users/client/login/', {
        method: 'POST',
        body: { username: email, password },
      });
      if (!res.ok) {
        const payload = res.data;
        setMessage(payload?.error?.message || payload?.detail?.error?.message || 'Login failed.');
        return;
      }
      login(res.data);
      const next = location.state?.from?.pathname || '/client_dashboard';
      navigate(next, { replace: true });
    } catch (err) {
      console.error(err);
      setMessage('Network error while logging in.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoogleCredential = async (credential) => {
    setSubmitting(true);
    setMessage('');
    try {
      const res = await apiRequest('/api/v1/users/client/google_login/', {
        method: 'POST',
        body: { credential },
      });
      if (!res.ok) {
        const payload = res.data;
        setMessage(payload?.error?.message || payload?.detail?.error?.message || 'Google login failed.');
        return;
      }
      login(res.data);
      const next = location.state?.from?.pathname || '/client_dashboard';
      navigate(next, { replace: true });
    } catch (err) {
      console.error(err);
      setMessage('Network error while logging in with Google.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="client-auth-page">
      <form className="client-auth-card" onSubmit={handleSubmit}>
        <h1>Client Login</h1>
        <p className="client-auth-subtitle">Log in to continue your plan and complete onboarding.</p>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required={!isGmailEmail}
            disabled={isGmailEmail}
            placeholder={isGmailEmail ? 'Use Google sign-in for Gmail accounts' : ''}
          />
        </label>
        {isGmailEmail ? <p className="client-auth-subtitle">Gmail account detected. Continue with Google below.</p> : null}
        <button type="submit" disabled={submitting}>
          {submitting ? 'Logging In…' : 'Log In'}
        </button>
        <div className="client-auth-divider"><span>or</span></div>
        <GoogleSignInButton onCredential={handleGoogleCredential} disabled={submitting} />
        {message && <p className="client-auth-error">{message}</p>}
      </form>
    </div>
  );
}

export default ClientLoginPage;
