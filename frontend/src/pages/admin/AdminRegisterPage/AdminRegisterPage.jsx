import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import './AdminRegisterPage.css';

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
      alert('missing registration token.');
      navigate('/');
      return;
    }

    setToken(tokenFromURL);

    const fetchPendingEmail = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/users/admin/pending_signup/${tokenFromURL}`);

        if (!res.ok) {
          const text = await res.text();
          console.error('server responded with:', text);
          alert('invalid or expired registration link.');
          navigate('/');
          return;
        }

        const data = await res.json();
        setEmail(data.email);
      } catch (err) {
        console.error('error fetching pending signup:', err);
        alert('something went wrong.');
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
        console.error('❌ response not json:', text);
        alert('server error during registration. check logs.');
        return;
      }

      if (!res.ok) {
        alert(data.error || 'registration failed');
        return;
      }

      alert('✅ account created successfully! logging you in...');

      const loginRes = await fetch('http://localhost:8000/api/users/admin/login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username: email, password }),
      });

      const loginData = await loginRes.json();

      if (!loginRes.ok) {
        alert(loginData.error || 'auto-login failed. please login manually.');
        navigate('/admin_login');
        return;
      }

      login(loginData);
      navigate('/admin_dashboard');
    } catch (err) {
      console.error('unexpected error:', err);
      alert('unexpected error. check console.');
    }
  };

  if (loading) {
    return (
      <div className="admin-register-loading">
        <p>🔄 loading registration form...</p>
      </div>
    );
  }

  return (
    <div className="admin-register-wrapper">
      <div className="admin-register-card">
        <h2 className="admin-register-title">📝 complete your admin registration</h2>
        <form onSubmit={handleSubmit}>
          <label>email</label>
          <input
            type="email"
            value={email}
            disabled
            className="admin-register-input disabled"
          />
          <label>create a password</label>
          <input
            type="password"
            placeholder="choose a password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="admin-register-input"
          />
          <button type="submit" className="admin-register-button">
            create account
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