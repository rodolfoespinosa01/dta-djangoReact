import React from 'react';
import { useNavigate } from 'react-router-dom';
import './AdminHomePage.css';

function AdminHomePage() {
  const navigate = useNavigate();

  return (
    <div className="admin-home-wrapper">
      <div className="admin-home-card">
        <h1 className="admin-home-title">Welcome to DTA</h1>
        <p className="admin-home-subtitle">
          Your all-in-one platform for creating personalized diet plans for your clients.
        </p>

        <button
          onClick={() => navigate('/admin_login')}
          className="admin-home-button primary"
        >
          Admin Login
        </button>

        <button
          onClick={() => navigate('/superadmin_login')}
          className="admin-home-button secondary"
        >
          SuperAdmin Login
        </button>

        <button
          onClick={() => navigate('/admin_plans')}
          className="admin-home-button tertiary"
        >
          View Plans
        </button>
      </div>
    </div>
  );
}

export default AdminHomePage;
