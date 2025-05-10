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
  
      let data = null;
      try {
        data = await res.json();
      } catch (jsonErr) {
        console.warn('⚠️ Response not JSON:', jsonErr);
      }
  
      if (res.ok) {
        setStatus('success');
      } else if (data && data.error) {
        setStatus(data.error);
      } else {
        setStatus('Email not found or not registered.');
      }
    } catch (err) {
      console.error('❌ Network error:', err);
      setStatus('A network error occurred.');
    }
  };
  
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#f9fafb',
        padding: '2rem',
      }}
    >
      <div
        style={{
          backgroundColor: 'white',
          border: '1px solid #e5e7eb',
          padding: '2rem',
          borderRadius: '10px',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
          maxWidth: '400px',
          width: '100%',
        }}
      >
        <h2 style={{ marginBottom: '1.5rem', textAlign: 'center' }}>🔐 Reset Admin Password</h2>
        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="Enter your admin email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{
              width: '100%',
              padding: '0.75rem',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              marginBottom: '1rem',
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
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '1rem',
            }}
          >
            Send Reset Link
          </button>
        </form>

        {status === 'success' && (
          <p style={{ color: '#16a34a', marginTop: '1rem', textAlign: 'center' }}>
            ✅ Check your email (or console) for the reset link.
          </p>
        )}

        {status && status !== 'success' && (
          <p style={{ color: '#dc2626', marginTop: '1rem', textAlign: 'center' }}>{status}</p>
        )}
      </div>
    </div>
  );
}

export default AdminForgotPasswordPage;
