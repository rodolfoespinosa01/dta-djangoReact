import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import logo from '../assets/dta_brand_content/DTA_Logo.png';
import logoWhite from '../assets/dta_brand_content/DTA_Logo_white.png';
import './Navbar.css';

const Navbar = ({ adminTheme = null }) => {
  const { isAuthenticated, user, logout } = useAuth();
  const { t } = useLanguage();
  const location = useLocation();
  const logoSrc = adminTheme === 'dark' ? logoWhite : logo;
  const isAdminSignedIn = isAuthenticated && user?.role === 'admin';
  const onAdminDashboard = location.pathname === '/admin_dashboard';
  const onAdminSettings = location.pathname === '/admin_settings';
  const onAdminParameters = location.pathname === '/admin_parameter_settings';

  const handleLogout = () => {
    logout();
  };

  return (
    <nav className="site-navbar">
      <Link to="/admin_homepage" className="site-brand" aria-label={t('navbar.home_aria')}>
        <img src={logoSrc} alt="DTA logo" className="site-brand-logo" />
      </Link>
      <div className="site-nav-links">
      {!isAdminSignedIn && <Link to="/welcome" className="site-nav-link">{t('navbar.welcome')}</Link>}

      {isAuthenticated ? (
        <>
          {user?.role === 'admin' && (
            <>
              {!onAdminDashboard && <Link to="/admin_dashboard" className="site-nav-link">{t('navbar.dashboard')}</Link>}
              {!onAdminSettings && <Link to="/admin_settings" className="site-nav-link">{t('navbar.settings')}</Link>}
              {!onAdminParameters && <Link to="/admin_parameter_settings" className="site-nav-link">Parameters</Link>}
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
