// AdminLoginPage.jsx (minimal diff)
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import { useLanguage } from '../../../context/LanguageContext';
import { buildApiUrl } from '../../../config/api';
import './AdminLoginPage.css';

function AdminLoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const { login } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();

  const extractError = (data, status) => {
    const payload = data?.detail && typeof data.detail === 'object' ? data.detail : data;
    const code = payload?.error_code;
    if (status === 404 || code === 'USER_NOT_FOUND') return t('admin_login.err_no_account');
    if (status === 401 || code === 'WRONG_PASSWORD') return t('admin_login.err_wrong_password');
    return payload?.error?.message || payload?.error || t('admin_login.err_try_again');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    try {
      const response = await fetch(buildApiUrl('/api/v1/users/admin/login/'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username: email, password }),
      });

      const data = await response.json().catch(() => ({}));

      if (response.ok) {
        login(data);
        localStorage.setItem('refresh_token', data.refresh);
        navigate('/admin_dashboard');
      } else {
        setError(extractError(data, response.status));
      }
    } catch (err) {
      console.error('login error:', err);
      setError(t('admin_login.err_generic'));
    }
  };

  return (
    <div className="admin-login-wrapper">
      <div className="admin-login-card">
        <h2 className="admin-login-title">🔐 {t('admin_login.title')}</h2>
        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder={t('admin_login.email_placeholder')}
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="admin-login-input"
            autoComplete="username"
          />
          <input
            type="password"
            placeholder={t('admin_login.password_placeholder')}
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="admin-login-input"
            autoComplete="current-password"
          />
          <button type="submit" className="admin-login-button">{t('admin_login.login_btn')}</button>

          {error && <div className="admin-login-error" role="alert">{error}</div>}

          <p className="admin-login-link-wrapper">
            <a href="/admin_forgot_password" className="admin-login-link">{t('admin_login.forgot')}</a>
          </p>
        </form>
      </div>
    </div>
  );
}

export default AdminLoginPage;
