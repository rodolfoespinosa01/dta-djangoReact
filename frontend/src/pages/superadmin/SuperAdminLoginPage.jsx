import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useLanguage } from '../../context/LanguageContext';
import './SuperAdminLoginPage.css';

function SuperAdminLoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const { login } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    const response = await fetch('http://localhost:8000/api/users/superadmin/login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    const data = await response.json();

    if (response.ok) {
      login(data);
      localStorage.setItem('refresh_token', data.refresh);
      navigate('/superadmin_dashboard');
    } else {
      alert(data.error || t('superadmin_login.failed'));
    }
  };

  return (
    <div className="superadmin-login-page">
      <h2>{t('superadmin_login.title')}</h2>
      <form onSubmit={handleSubmit} className="superadmin-login-form">
        <input
          type="text"
          placeholder={t('superadmin_login.username_placeholder')}
          required
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="superadmin-login-input"
        />
        <input
          type="password"
          placeholder={t('superadmin_login.password_placeholder')}
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="superadmin-login-input"
        />
        <button type="submit" className="superadmin-login-button">{t('common.login')}</button>
      </form>
    </div>
  );
}

export default SuperAdminLoginPage;
