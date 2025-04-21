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

  useEffect(() => {
    if (!uid || !token) {
      setStatus('Missing reset link information.');
    }
  }, [uid, token]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (newPassword !== confirmPassword) {
      setStatus('Passwords do not match.');
      return;
    }

    const res = await fetch('http://localhost:8000/api/users/admin/reset_password/confirm/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ uid, token, new_password: newPassword }),
    });

    if (res.ok) {
      setStatus('success');
      setTimeout(() => navigate('/admin-login'), 2000);
    } else {
      const data = await res.json();
      setStatus(data?.detail || 'Reset failed. Check your link or try again.');
    }
  };

  return (
    <div style={{ padding: '2rem' }}>
      <h2>Set New Admin Password</h2>
      <form onSubmit={handleSubmit} style={{ maxWidth: '400px' }}>
        <input
          type="password"
          placeholder="New password"
          required
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          style={{ display: 'block', marginBottom: '1rem', width: '100%' }}
        />
        <input
          type="password"
          placeholder="Confirm new password"
          required
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          style={{ display: 'block', marginBottom: '1rem', width: '100%' }}
        />
        <button type="submit">Reset Password</button>
      </form>

      {status === 'success' && (
        <p style={{ color: 'green', marginTop: '1rem' }}>
          ✅ Password reset! Redirecting to login...
        </p>
      )}
      {status && status !== 'success' && (
        <p style={{ color: 'red', marginTop: '1rem' }}>{status}</p>
      )}
    </div>
  );
}

export default AdminResetPasswordPage;
