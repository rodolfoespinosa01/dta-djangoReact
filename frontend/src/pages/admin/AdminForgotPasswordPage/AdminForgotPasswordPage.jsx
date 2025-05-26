// import react hooks
import React, { useState } from 'react';

// import page-specific styles
import './AdminForgotPasswordPage.css';

function AdminForgotPasswordPage() {
  // form input state
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState(null);

  // handle form submission
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
        console.warn('⚠️ response not json:', jsonErr);
      }

      if (res.ok) {
        setStatus('success');
      } else if (data && data.error) {
        setStatus(data.error);
      } else {
        setStatus('email not found or not registered.');
      }
    } catch (err) {
      console.error('❌ network error:', err);
      setStatus('a network error occurred.');
    }
  };

  return (
    <div className="forgot-password-wrapper">
      <div className="forgot-password-card">
        <h2 className="forgot-password-title">🔐 reset admin password</h2>
        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="enter your admin email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="forgot-password-input"
          />
          <button type="submit" className="forgot-password-button">
            send reset link
          </button>
        </form>

        {status === 'success' && (
          <p className="forgot-password-success">
            ✅ check your email (or console) for the reset link.
          </p>
        )}

        {status && status !== 'success' && (
          <p className="forgot-password-error">{status}</p>
        )}
      </div>
    </div>
  );
}

export default AdminForgotPasswordPage;

// admin forgot password page
// this component allows an admin to submit their email address to receive a password reset link.
// when the form is submitted, it sends a POST request to /api/users/admin/forgot_password/ with the email in the json body.
// the backend checks if the email belongs to an active admin, then returns a success or error message which is shown to the user.