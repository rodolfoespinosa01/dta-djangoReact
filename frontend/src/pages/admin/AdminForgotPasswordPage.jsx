import React, { useState } from 'react';

function AdminForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
        const res = await fetch('http://localhost:8000/api/users/admin/forgot_password/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email }),
        });
      
        const data = await res.json();
      
        if (res.ok) {
          setStatus('success');
        } else {
          setStatus(data?.email || 'Error sending reset link.');
        }
      } catch (err) {
        console.error('❌ Network error:', err);
        setStatus('A network error occurred.');
      }
  };

  return (
    <div style={{ padding: '2rem' }}>
      <h2>Reset Admin Password</h2>
      <form onSubmit={handleSubmit} style={{ maxWidth: '400px' }}>
        <input
          type="email"
          placeholder="Enter your admin email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{ display: 'block', marginBottom: '1rem', width: '100%' }}
        />
        <button type="submit">Send Reset Link</button>
      </form>

      {status === 'success' && (
        <p style={{ color: 'green', marginTop: '1rem' }}>
          ✅ Check your email (or console) for the reset link.
        </p>
      )}

      {status && status !== 'success' && (
        <p style={{ color: 'red', marginTop: '1rem' }}>{status}</p>
      )}
    </div>
  );
}

export default AdminForgotPasswordPage;
