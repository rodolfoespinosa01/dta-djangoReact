import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function MainHomePage() {
  const { user, isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (loading) return; // ⏳ Wait for auth to finish loading

    if (isAuthenticated && user?.role) {
      switch (user.role) {
        case 'admin':
          navigate('/admin-dashboard');
          break;
        case 'superadmin':
          navigate('/superadmin-dashboard');
          break;
        case 'client':
          navigate('/client-dashboard'); // 🔁 Adjust this if needed
          break;
        default:
          break;
      }
    }
  }, [loading, isAuthenticated, user, navigate]);

  return (
    <div style={{ textAlign: 'center', padding: '3rem' }}>
      <h1>Welcome to the Best Diet Generator</h1>
      <p>This is your white label development platform for next-gen meal plans.</p>
    </div>
  );
}

export default MainHomePage;
