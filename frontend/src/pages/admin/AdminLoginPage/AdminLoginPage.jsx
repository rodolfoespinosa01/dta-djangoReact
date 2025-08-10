// AdminLoginPage.jsx (minimal diff)
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import './AdminLoginPage.css';

function AdminLoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const { login } = useAuth();
  const navigate = useNavigate();

  const extractError = (data, status) => {
    const payload = data?.detail && typeof data.detail === 'object' ? data.detail : data;
    const code = payload?.error_code;
    if (status === 404 || code === 'USER_NOT_FOUND') return 'No account found with that email.';
    if (status === 401 || code === 'WRONG_PASSWORD') return 'Account found, but the password is incorrect.';
    return payload?.error || 'Unable to log in. Please try again.';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/api/users/admin/login/', {
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
      setError('Something went wrong. Please try again.');
    }
  };

  return (
    <div className="admin-login-wrapper">
      <div className="admin-login-card">
        <h2 className="admin-login-title">🔐 admin login</h2>
        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="admin-login-input"
            autoComplete="username"
          />
          <input
            type="password"
            placeholder="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="admin-login-input"
            autoComplete="current-password"
          />
          <button type="submit" className="admin-login-button">log in</button>

          {error && <div className="admin-login-error" role="alert">{error}</div>}

          <p className="admin-login-link-wrapper">
            <a href="/admin_forgot_password" className="admin-login-link">forgot your password?</a>
          </p>
        </form>
      </div>
    </div>
  );
}

export default AdminLoginPage;
