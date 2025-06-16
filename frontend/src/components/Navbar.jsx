import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Navbar = () => {
  const { isAuthenticated, user, logout } = useAuth();

  const handleLogout = () => {
    logout();
  };

  return (
    <nav style={{ padding: '1rem', borderBottom: '1px solid #ddd' }}>
      <Link to="/" style={{ marginRight: '1rem' }}>Home</Link>

      {isAuthenticated ? (
        <>
          {user?.role === 'admin' && (
            <>
              <Link to="/admin_dashboard" style={{ marginRight: '1rem' }}>Dashboard</Link>
              <Link to="/admin_settings" style={{ marginRight: '1rem' }}>Settings</Link>
            </>
          )}

          {user?.role === 'superadmin' && (
            <Link to="/superadmin_dashboard" style={{ marginRight: '1rem' }}>Super Dashboard</Link>
          )}

          <button onClick={handleLogout}>Logout</button>
        </>
      ) : (
        <>
          <Link to="/admin_login" style={{ marginRight: '1rem' }}>Login</Link>
          <Link to="/admin_plans">Plans</Link>
        </>
      )}
    </nav>
  );
};

export default Navbar;
