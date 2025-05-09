import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

function AdminResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const uid = searchParams.get('uid');
  const token = searchParams.get('token');

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [status, setStatus] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!uid || !token) {
      setStatus('Missing or invalid reset link. Please try again.');
    }
  }, [uid, token]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (newPassword !== confirmPassword) {
      setStatus('Passwords do not match.');
      return;
    }

    setSubmitting(true);
    setStatus(null);

    try {
      const res = await fetch('http://localhost:8000/api/users/admin/reset_password/confirm/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uid, token, new_password: newPassword }),
      });

      if (res.ok) {
        setStatus('success');
        setTimeout(() => navigate('/admin_login'), 2000);
      } else {
        const data = await res.json();
        setStatus(data?.detail || 'Reset failed. Try a new link.');
      }
    } catch (err) {
      console.error('Reset error:', err);
      setStatus('Network error. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ padding: '3rem', display: 'flex', justifyContent: 'center' }}>
      <div
        style={{
          backgroundColor: '#fff',
          padding: '2rem',
          borderRadius: '10px',
          boxShadow: '0 0 10px rgba(0,0,0,0.05)',
          maxWidth: '400px',
          width: '100%',
        }}
      >
        <h2 style={{ textAlign: 'center', marginBottom: '1rem' }}>🔐 Reset Your Password</h2>
        <form onSubmit={handleSubmit}>
          <input
            type="password"
            placeholder="New password"
            required
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            style={{
              display: 'block',
              marginBottom: '1rem',
              width: '100%',
              padding: '0.75rem',
              borderRadius: '6px',
              border: '1px solid #d1d5db',
            }}
          />
          <input
            type="password"
            placeholder="Confirm new password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            style={{
              display: 'block',
              marginBottom: '1.5rem',
              width: '100%',
              padding: '0.75rem',
              borderRadius: '6px',
              border: '1px solid #d1d5db',
            }}
          />
          <button
            type="submit"
            disabled={submitting}
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
            {submitting ? 'Resetting...' : 'Reset Password'}
          </button>
        </form>

        {status === 'success' && (
          <p style={{ color: 'green', marginTop: '1rem' }}>
            ✅ Password updated! Redirecting to login...
          </p>
        )}
        {status && status !== 'success' && (
          <p style={{ color: 'red', marginTop: '1rem' }}>{status}</p>
        )}
      </div>
    </div>
  );
}

export default AdminResetPasswordPage;
