import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import logo from '../assets/dta_brand_content/DTA_Logo.png';
import './Navbar.css';

const Navbar = () => {
  const { isAuthenticated, user, logout } = useAuth();
  const { t } = useLanguage();

  const handleLogout = () => {
    logout();
  };

  return (
    <nav className="site-navbar">
      <Link to="/admin_homepage" className="site-brand" aria-label={t('navbar.home_aria')}>
        <img src={logo} alt="DTA logo" className="site-brand-logo" />
      </Link>
      <div className="site-nav-links">
      <Link to="/welcome" className="site-nav-link">{t('navbar.welcome')}</Link>

      {isAuthenticated ? (
        <>
          {user?.role === 'admin' && (
            <>
              <Link to="/admin_dashboard" className="site-nav-link">{t('navbar.dashboard')}</Link>
              <Link to="/admin_settings" className="site-nav-link">{t('navbar.settings')}</Link>
            </>
          )}

          {user?.role === 'superadmin' && (
            <Link to="/superadmin_dashboard" className="site-nav-link">{t('navbar.super_dashboard')}</Link>
          )}

          <button
            onClick={handleLogout}
            className="site-logout-btn"
          >
            {t('navbar.logout')}
          </button>
        </>
      ) : (
        <>
          <Link to="/admin_login" className="site-nav-link">{t('navbar.login')}</Link>
          <Link to="/admin_plans" className="site-nav-link">{t('navbar.plans')}</Link>
        </>
      )}
      </div>
    </nav>
  );
};

export default Navbar;
