import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { apiRequest } from '../../../api/client';
import { useAuth } from '../../../context/AuthContext';
import GoogleSignInButton from '../../../components/auth/GoogleSignInButton';
import '../../../styles/shared/auth-flow.css';
import './css.css';

function ClientLoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { adminSlug } = useParams();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [brandState, setBrandState] = useState({
    loading: Boolean(adminSlug),
    brandName: adminSlug ? adminSlug : 'DTA',
  });
  const isGmailEmail = /@gmail\.com$|@googlemail\.com$/i.test((email || '').trim());
  const isAdminBranded = Boolean(adminSlug);

  useEffect(() => {
    let ignore = false;
    if (!adminSlug) {
      setBrandState({ loading: false, brandName: 'DTA' });
      return () => { ignore = true; };
    }
    setBrandState((prev) => ({ ...prev, loading: true }));
    apiRequest(`/api/v1/users/client/public/admin-page/${adminSlug}/`)
      .then((res) => {
        if (ignore) return;
        if (res.ok) {
          setBrandState({
            loading: false,
            brandName: res.data?.admin_page?.brand_name || adminSlug,
          });
          return;
        }
        setBrandState({
          loading: false,
          brandName: adminSlug,
        });
      })
      .catch(() => {
        if (ignore) return;
        setBrandState({
          loading: false,
          brandName: adminSlug,
        });
      });
    return () => { ignore = true; };
  }, [adminSlug]);

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
        <p className="client-auth-badge">
          {isAdminBranded ? `Coach Client Login • ${brandState.brandName}` : 'DTA Client Login'}
        </p>
        <h1>{isAdminBranded ? 'Coach Client Login' : 'Client Login'}</h1>
        <p className="client-auth-subtitle">
          {isAdminBranded
            ? 'Log in to access your coach-linked dashboard, meal plan, and progress tools.'
            : 'Log in to continue your DTA plan and access your dashboard.'}
        </p>
        {brandState.loading && isAdminBranded ? (
          <p className="client-auth-subtitle">Loading coach branding…</p>
        ) : null}
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
        <div className="client-auth-links">
          {isAdminBranded ? (
            <>
              <Link className="client-auth-link" to={`/start/${adminSlug}`}>Back to Coach Page</Link>
              <Link className="client-auth-link" to={`/start/${adminSlug}/plans`}>View Coach Plans</Link>
            </>
          ) : (
            <>
              <Link className="client-auth-link" to="/user_homepage">Back to DTA</Link>
              <Link className="client-auth-link" to="/user_plans">View DTA Plans</Link>
            </>
          )}
        </div>
      </form>
    </div>
  );
}

export default ClientLoginPage;
