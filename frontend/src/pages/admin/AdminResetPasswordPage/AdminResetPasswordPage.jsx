import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import './AdminResetPasswordPage.css';

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
      setStatus('missing or invalid reset link. please try again.');
    }
  }, [uid, token]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (newPassword !== confirmPassword) {
      setStatus('passwords do not match.');
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
        setStatus(data?.detail || 'reset failed. try a new link.');
      }
    } catch (err) {
      console.error('reset error:', err);
      setStatus('network error. please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="reset-password-wrapper">
      <div className="reset-password-card">
        <h2 className="reset-password-title">🔐 reset your password</h2>
        <form onSubmit={handleSubmit}>
          <input
            type="password"
            placeholder="new password"
            required
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="reset-password-input"
          />
          <input
            type="password"
            placeholder="confirm new password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="reset-password-input"
          />
          <button
            type="submit"
            disabled={submitting}
            className="reset-password-button"
          >
            {submitting ? 'resetting...' : 'reset password'}
          </button>
        </form>

        {status === 'success' && (
          <p className="reset-password-success">
            ✅ password updated! redirecting to login...
          </p>
        )}
        {status && status !== 'success' && (
          <p className="reset-password-error">{status}</p>
        )}
      </div>
    </div>
  );
}

export default AdminResetPasswordPage;

// summary:
// this page handles password resets for admins by submitting the uid, token, and new password to the backend.
// if the reset is successful, the user is redirected to the login page after 2 seconds.
// if the link is invalid or passwords don't match, appropriate error messages are shown.