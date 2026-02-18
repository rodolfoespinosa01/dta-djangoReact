import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import './SuperAdminLoginPage.css';

function SuperAdminLoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    const response = await fetch('http://localhost:8000/api/users/superadmin_login/', {
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
      alert(data.error || 'Login failed');
    }
  };

  return (
    <div className="superadmin-login-page">
      <h2>SuperAdmin Login</h2>
      <form onSubmit={handleSubmit} className="superadmin-login-form">
        <input
          type="text"
          placeholder="Username"
          required
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="superadmin-login-input"
        />
        <input
          type="password"
          placeholder="Password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="superadmin-login-input"
        />
        <button type="submit" className="superadmin-login-button">Log In</button>
      </form>
    </div>
  );
}

export default SuperAdminLoginPage;
