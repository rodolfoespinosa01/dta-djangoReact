import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import logo from '../assets/DTA_Logo.png';
import './Navbar.css';

const Navbar = () => {
  const { isAuthenticated, user, logout } = useAuth();

  const handleLogout = () => {
    logout();
  };

  return (
    <nav className="site-navbar">
      <Link to="/admin_homepage" className="site-brand" aria-label="DTA home">
        <img src={logo} alt="DTA logo" className="site-brand-logo" />
      </Link>
      <div className="site-nav-links">
      <Link to="/welcome" className="site-nav-link">Welcome</Link>

      {isAuthenticated ? (
        <>
          {user?.role === 'admin' && (
            <>
              <Link to="/admin_dashboard" className="site-nav-link">Dashboard</Link>
              <Link to="/admin_settings" className="site-nav-link">Settings</Link>
            </>
          )}

          {user?.role === 'superadmin' && (
            <Link to="/superadmin_dashboard" className="site-nav-link">Super Dashboard</Link>
          )}

          <button
            onClick={handleLogout}
            className="site-logout-btn"
          >
            Logout
          </button>
        </>
      ) : (
        <>
          <Link to="/admin_login" className="site-nav-link">Login</Link>
          <Link to="/admin_plans" className="site-nav-link">Plans</Link>
        </>
      )}
      </div>
    </nav>
  );
};

export default Navbar;
