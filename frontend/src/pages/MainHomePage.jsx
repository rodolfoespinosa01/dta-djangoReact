import React from 'react';
import { useNavigate } from 'react-router-dom';
import './MainHomePage.css';

function MainHomePage() {
  const navigate = useNavigate();

  return (
    <div className="main-home-page">
      <h1 className="main-home-title">Welcome to the Best Diet Generator</h1>
      <p className="main-home-subtitle">This is your white label development platform for next-gen meal plans.</p>

      <div className="main-home-actions">
        <button onClick={() => navigate('/admin_login')} className="main-home-button">
          Admin Login
        </button>
        <button onClick={() => navigate('/superadmin_login')} className="main-home-button">
          SuperAdmin Login
        </button>
        <button onClick={() => navigate('/admin_plans')} className="main-home-button">
          View Admin Plans
        </button>
      </div>
    </div>
  );
}

export default MainHomePage;
