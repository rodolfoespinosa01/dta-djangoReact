import React, { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';

function AdminRegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const sessionId = searchParams.get('session_id');

  const handleSubmit = async (e) => {
    e.preventDefault();

    const response = await fetch('http://localhost:8000/api/register-admin/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, session_id: sessionId }),
    });

    const data = await response.json();

    if (response.ok) {
      navigate('/admindashboard');
    } else {
      alert(data.error || 'Registration failed');
    }
  };

  return (
    <div style={{ padding: '2rem' }}>
      <h2>Register Your Admin Account</h2>
      <form onSubmit={handleSubmit} style={{ maxWidth: '400px' }}>
        <input
          type="email"
          placeholder="Email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{ display: 'block', marginBottom: '1rem', width: '100%' }}
        />
        <input
          type="password"
          placeholder="Password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={{ display: 'block', marginBottom: '1rem', width: '100%' }}
        />
        <button type="submit">Create Account</button>
      </form>
    </div>
  );
}

export default AdminRegisterPage;
