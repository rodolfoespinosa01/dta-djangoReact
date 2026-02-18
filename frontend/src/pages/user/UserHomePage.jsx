import React from 'react';
import './UserHomePage.css';

function UserHomePage() {
  return (
    <div className="user-home-page">
      <h1>User Login</h1>
      <p>Sign in with your email and password.</p>
      <form className="user-login-form">
        <label className="user-login-label" htmlFor="user-email">
          Email
        </label>
        <input
          id="user-email"
          type="email"
          className="user-login-input"
          placeholder="you@example.com"
          autoComplete="email"
        />
        <label className="user-login-label" htmlFor="user-password">
          Password
        </label>
        <input
          id="user-password"
          type="password"
          className="user-login-input"
          placeholder="Enter your password"
          autoComplete="current-password"
        />
        <button type="button" className="user-home-button" disabled>
          Log In (Coming Soon)
        </button>
      </form>
    </div>
  );
}

export default UserHomePage;
