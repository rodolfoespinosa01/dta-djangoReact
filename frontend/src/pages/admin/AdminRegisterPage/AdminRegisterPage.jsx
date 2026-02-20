import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import { useLanguage } from '../../../context/LanguageContext';
import { buildApiUrl } from '../../../config/api';
import './AdminRegisterPage.css';

function AdminRegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(true);

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
        const res = await fetch(buildApiUrl(`/api/v1/users/admin/pending_signup/${tokenFromURL}`));

        if (!res.ok) {
          const text = await res.text();
          console.error('server responded with:', text);
          alert(t('admin_register.invalid_link'));
          navigate('/');
          return;
        }

        const data = await res.json();
        setEmail(data.email);
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
        alert(data?.error?.message || data?.error || t('admin_register.registration_failed'));
        return;
      }

      alert(`✅ ${t('admin_register.created')}`);

      const loginRes = await fetch(buildApiUrl('/api/v1/users/admin/login/'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username: email, password }),
      });

      const loginData = await loginRes.json();

      if (!loginRes.ok) {
        alert(loginData?.error?.message || loginData?.error || t('admin_register.auto_login_failed'));
        navigate('/admin_login');
        return;
      }

      login(loginData);
      navigate('/admin_dashboard');
    } catch (err) {
      console.error('unexpected error:', err);
      alert(t('admin_register.unexpected'));
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
        <form onSubmit={handleSubmit}>
          <label>{t('admin_register.email')}</label>
          <input
            type="email"
            value={email}
            disabled
            className="admin-register-input disabled"
          />
          <label>{t('admin_register.create_password')}</label>
          <input
            type="password"
            placeholder={t('admin_register.choose_password')}
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="admin-register-input"
          />
          <button type="submit" className="admin-register-button">
            {t('admin_register.create_account')}
          </button>
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
