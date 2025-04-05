import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

function AdminSettings() {
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated) navigate('/adminlogin');
  }, [isAuthenticated, navigate]);

  return (
    <div style={{ padding: '2rem' }}>
      <h2>Admin Settings</h2>
      {user && <p>Settings for: {user.email}</p>}
      <p>(Coming soon!)</p>
    </div>
  );
}

export default AdminSettings;
