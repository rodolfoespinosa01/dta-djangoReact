import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import { useLanguage } from '../../../context/LanguageContext';
import { buildApiUrl } from '../../../config/api';
import GoogleSignInButton from '../../../components/auth/GoogleSignInButton';
import './AdminRegisterPage.css';

function AdminRegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [inlineError, setInlineError] = useState('');
  const isGmailEmail = /@gmail\.com$|@googlemail\.com$/i.test((email || '').trim());

  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login } = useAuth();
  const { t } = useLanguage();

  useEffect(() => {
    const tokenFromURL = searchParams.get('token');
    if (!tokenFromURL) {
      alert(t('admin_register.missing_token'));
      navigate('/');
      return;
    }

    setToken(tokenFromURL);

    const fetchPendingEmail = async () => {
      try {
        const res = await fetch(buildApiUrl(`/api/v1/users/admin/pending_signup/${tokenFromURL}/`));

        if (!res.ok) {
          const text = await res.text();
          console.error('server responded with:', text);
          alert(t('admin_register.invalid_link'));
          navigate('/');
          return;
        }

        const data = await res.json();
        const pending = data?.pending_signup || data;
        setEmail(pending?.email || '');
      } catch (err) {
        console.error('error fetching pending signup:', err);
        alert(t('admin_register.something_wrong'));
        navigate('/');
      } finally {
        setLoading(false);
      }
    };

    fetchPendingEmail();
  }, [searchParams, navigate, t]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isGmailEmail) {
      setInlineError('Gmail accounts must continue with Google.');
      return;
    }
    setSubmitting(true);
    setInlineError('');

    try {
      const res = await fetch(buildApiUrl('/api/v1/users/admin/register/'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password, token }),
      });

      let data;
      try {
        data = await res.json();
      } catch (jsonErr) {
        const text = await res.text();
        console.error('❌ response not json:', text);
        alert(t('admin_register.server_error'));
        return;
      }

      if (!res.ok) {
        setInlineError(data?.error?.message || data?.error || t('admin_register.registration_failed'));
        return;
      }
      login(data);
      navigate('/admin_dashboard');
    } catch (err) {
      console.error('unexpected error:', err);
      setInlineError(t('admin_register.unexpected'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoogleCredential = async (credential) => {
    setSubmitting(true);
    setInlineError('');
    try {
      const res = await fetch(buildApiUrl('/api/v1/users/admin/register/'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, token, credential }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setInlineError(data?.error?.message || data?.error || t('admin_register.registration_failed'));
        return;
      }
      login(data);
      navigate('/admin_dashboard');
    } catch (err) {
      console.error('google registration error:', err);
      setInlineError(t('admin_register.unexpected'));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="admin-register-loading">
        <p>🔄 {t('admin_register.loading')}</p>
      </div>
    );
  }

  return (
    <div className="admin-register-wrapper">
      <div className="admin-register-card">
        <h2 className="admin-register-title">📝 {t('admin_register.title')}</h2>
        <p className="admin-register-subtitle">Use the invited email below.</p>
        {isGmailEmail ? (
          <p className="admin-register-subtitle">Gmail account detected. Google signup is required to create this account.</p>
        ) : (
          <p className="admin-register-subtitle">Create a password to register. Google is also available if you want to use it now.</p>
        )}
        <form onSubmit={handleSubmit}>
          <label>{t('admin_register.email')}</label>
          <input
            type="email"
            value={email}
            disabled
            className="admin-register-input disabled"
          />
          <div className="admin-register-divider"><span>{isGmailEmail ? 'Continue with Google' : 'Optional Google signup'}</span></div>
          <GoogleSignInButton onCredential={handleGoogleCredential} disabled={submitting} />
          {!isGmailEmail && (
            <>
              <div className="admin-register-divider"><span>Create with password</span></div>
              <label>{t('admin_register.create_password')}</label>
              <input
                type="password"
                placeholder={t('admin_register.choose_password')}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="admin-register-input"
              />
              <button type="submit" className="admin-register-button" disabled={submitting}>
                {submitting ? 'Creating…' : t('admin_register.create_account')}
              </button>
            </>
          )}
          {inlineError && <p className="admin-register-error" role="alert">{inlineError}</p>}
        </form>
      </div>
    </div>
  );
}

export default AdminRegisterPage;

// summary:
// this page completes admin signup by capturing a password and verifying the token from the stripe registration flow.
// it fetches the pending email based on the token, then allows the user to submit a password and create the account.
// after registration, the user is auto-logged in and redirected to the dashboard.
