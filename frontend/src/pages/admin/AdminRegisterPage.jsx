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
        const res = await fetch(`http://localhost:8000/api/users/pending-signup/${tokenFromURL}/`);
        
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
      const res = await fetch('http://localhost:8000/api/users/register-admin/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          email,
          password,
          token,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        alert(data.error || 'Registration failed');
        return;
      }

      alert('✅ Account created successfully! Logging you in...');

      // 🔑 Auto-login via Admin endpoint
      const loginRes = await fetch('http://localhost:8000/api/users/adminlogin/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });

      const loginData = await loginRes.json();

      if (!loginRes.ok) {
        alert(loginData.error || 'Auto-login failed. Please login manually.');
        navigate('/adminlogin');
        return;
      }

      // Set user context if available
      login(loginData);

      // ✅ Go to dashboard
      navigate('/admindashboard');

    } catch (err) {
      console.error('Unexpected error:', err);
      alert('Something went wrong');
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
