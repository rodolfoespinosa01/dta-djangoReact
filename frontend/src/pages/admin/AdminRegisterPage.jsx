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
        
        // Try to parse JSON only if response is OK
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
          const text = await res.text(); // Try to read as plain text
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
        console.log('✅ loginData from /admin_login:', loginData);
        login(loginData);

        navigate('/admin_dashboard');
    
      } catch (err) {
        console.error('Unexpected error:', err);
        alert('Unexpected error. Check console.');
      }
    };
  

  if (loading) return <p>Loading...</p>;

  return (
    <div style={{ padding: '2rem' }}>
      <h2>Complete Your Admin Registration</h2>
      <form onSubmit={handleSubmit} style={{ maxWidth: '400px' }}>
        <input
          type="email"
          value={email}
          disabled
          style={{ display: 'block', marginBottom: '1rem', width: '100%' }}
        />
        <input
          type="password"
          placeholder="Choose a password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={{ display: 'block', marginBottom: '1rem', width: '100%' }}
        />
        <button type="submit" style={{ width: '100%' }}>
          Create Account
        </button>
      </form>
    </div>
  );
}

export default AdminRegisterPage;
