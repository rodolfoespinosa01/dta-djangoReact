import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

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
        alert(data.error || 'Login failed');
      }
    } catch (err) {
      console.error('Login error:', err);
      alert('Something went wrong. Please try again.');
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#f3f4f6',
        padding: '2rem',
      }}
    >
      <div
        style={{
          backgroundColor: 'white',
          padding: '2.5rem',
          borderRadius: '12px',
          width: '100%',
          maxWidth: '420px',
          boxShadow: '0 8px 20px rgba(0, 0, 0, 0.05)',
        }}
      >
        <h2 style={{ textAlign: 'center', marginBottom: '1.5rem' }}>🔐 Admin Login</h2>
        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="Email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{
              width: '100%',
              padding: '0.75rem',
              marginBottom: '1rem',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              fontSize: '1rem',
            }}
          />
          <input
            type="password"
            placeholder="Password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{
              width: '100%',
              padding: '0.75rem',
              marginBottom: '1rem',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              fontSize: '1rem',
            }}
          />
          <button
            type="submit"
            style={{
              width: '100%',
              padding: '0.75rem',
              backgroundColor: '#2563eb',
              color: 'white',
              fontWeight: 'bold',
              fontSize: '1rem',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
            }}
          >
            Log In
          </button>
          <p style={{ textAlign: 'center', marginTop: '1rem' }}>
            <a
              href="/admin_forgot_password"
              style={{
                color: '#2563eb',
                textDecoration: 'none',
                fontSize: '0.95rem',
              }}
            >
              Forgot your password?
            </a>
          </p>
        </form>
      </div>
    </div>
  );
}

export default AdminLoginPage;
