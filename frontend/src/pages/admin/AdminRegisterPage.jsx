import React, { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';


function AdminRegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login } = useAuth();


  const sessionId = searchParams.get('session_id');

  const handleSubmit = async (e) => {
    e.preventDefault();
  
    try {
      // Step 1: Register the admin
      const registerRes = await fetch('http://localhost:8000/api/register-admin/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, session_id: sessionId }),
      });
  
      const registerData = await registerRes.json();
  
      if (!registerRes.ok) {
        alert(registerData.error || 'Registration failed');
        return;
      }
  
      // Step 2: Immediately log them in
      const loginRes = await fetch('http://localhost:8000/api/users/adminlogin/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
  
      const loginData = await loginRes.json();
  
      if (!loginRes.ok) {
        alert(loginData.error || 'Login failed after registration');
        return;
      }
  
      login(loginData.access); // calls context login
      localStorage.setItem('refresh_token', loginData.refresh);
      navigate('/admindashboard');

    } catch (err) {
      console.error('Something went wrong:', err);
      alert('Unexpected error occurred');
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
