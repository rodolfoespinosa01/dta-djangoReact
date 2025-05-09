import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

function AdminRegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(true);

  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login } = useAuth();

  useEffect(() => {
    const tokenFromURL = searchParams.get('token');
    if (!tokenFromURL) {
      alert('Missing registration token.');
      navigate('/');
      return;
    }

    setToken(tokenFromURL);

    const fetchPendingEmail = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/users/admin/pending_signup/${tokenFromURL}`);
        
        if (!res.ok) {
          const text = await res.text();
          console.error('Server responded with:', text);
          alert('Invalid or expired registration link.');
          navigate('/');
          return;
        }

        const data = await res.json();
        setEmail(data.email);
      } catch (err) {
        console.error('Error fetching pending signup:', err);
        alert('Something went wrong.');
        navigate('/');
      } finally {
        setLoading(false);
      }
    };

    fetchPendingEmail();
  }, [searchParams, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const res = await fetch('http://localhost:8000/api/users/admin/register/', {
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
        console.error('❌ Response not JSON:', text);
        alert('Server error during registration. Check logs.');
        return;
      }

      if (!res.ok) {
        alert(data.error || 'Registration failed');
        return;
      }

      alert('✅ Account created successfully! Logging you in...');

      const loginRes = await fetch('http://localhost:8000/api/users/admin/login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username: email, password }),
      });

      const loginData = await loginRes.json();

      if (!loginRes.ok) {
        alert(loginData.error || 'Auto-login failed. Please login manually.');
        navigate('/admin_login');
        return;
      }

      login(loginData);
      navigate('/admin_dashboard');
    } catch (err) {
      console.error('Unexpected error:', err);
      alert('Unexpected error. Check console.');
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>🔄 Loading registration form...</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '3rem', display: 'flex', justifyContent: 'center' }}>
      <div
        style={{
          backgroundColor: '#fff',
          padding: '2rem',
          borderRadius: '10px',
          boxShadow: '0 0 12px rgba(0,0,0,0.05)',
          maxWidth: '400px',
          width: '100%',
        }}
      >
        <h2 style={{ marginBottom: '1rem', textAlign: 'center' }}>📝 Complete Your Admin Registration</h2>
        <form onSubmit={handleSubmit}>
          <label>Email</label>
          <input
            type="email"
            value={email}
            disabled
            style={{
              marginBottom: '1rem',
              width: '100%',
              padding: '0.75rem',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              backgroundColor: '#f9fafb',
            }}
          />
          <label>Create a Password</label>
          <input
            type="password"
            placeholder="Choose a password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{
              marginBottom: '1.5rem',
              width: '100%',
              padding: '0.75rem',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
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
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
            }}
          >
            Create Account
          </button>
        </form>
      </div>
    </div>
  );
}

export default AdminRegisterPage;
