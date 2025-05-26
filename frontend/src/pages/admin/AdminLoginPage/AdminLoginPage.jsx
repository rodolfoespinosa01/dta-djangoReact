import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import './AdminLoginPage.css';

function AdminLoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const response = await fetch('http://localhost:8000/api/users/admin/login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username: email, password }),
      });

      const data = await response.json();

      if (response.ok) {
        login(data);
        localStorage.setItem('refresh_token', data.refresh);
        navigate('/admin_dashboard');
      } else {
        alert(data.error || 'login failed');
      }
    } catch (err) {
      console.error('login error:', err);
      alert('something went wrong. please try again.');
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
          />
          <input
            type="password"
            placeholder="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="admin-login-input"
          />
          <button type="submit" className="admin-login-button">
            log in
          </button>
          <p className="admin-login-link-wrapper">
            <a href="/admin_forgot_password" className="admin-login-link">
              forgot your password?
            </a>
          </p>
        </form>
      </div>
    </div>
  );
}

export default AdminLoginPage;

// admin login page
// this component handles admin authentication using email and password.
// on form submission, it sends a POST request to /api/users/admin/login/ with the credentials and stores the jwt refresh token if successful.
// upon successful login, it redirects the admin to /admin_dashboard using react-router navigation.