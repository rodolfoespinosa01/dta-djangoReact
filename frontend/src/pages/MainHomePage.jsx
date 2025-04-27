import React from 'react';
import { useNavigate } from 'react-router-dom';

function MainHomePage() {
  const navigate = useNavigate();

  return (
    <div style={{ textAlign: 'center', padding: '3rem' }}>
      <h1>Welcome to the Best Diet Generator</h1>
      <p>This is your white label development platform for next-gen meal plans.</p>

      <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'center', gap: '1rem', flexWrap: 'wrap' }}>
        <button onClick={() => navigate('/admin_login')} style={buttonStyle}>
          Admin Login
        </button>
        <button onClick={() => navigate('/superadmin_login')} style={buttonStyle}>
          SuperAdmin Login
        </button>
        <button onClick={() => navigate('/admin_plans')} style={buttonStyle}>
          View Admin Plans
        </button>
      </div>
    </div>
  );
}

const buttonStyle = {
  padding: '1rem 2rem',
  fontSize: '1rem',
  borderRadius: '8px',
  cursor: 'pointer',
  backgroundColor: '#4CAF50',
  color: 'white',
  border: 'none',
  transition: 'background-color 0.3s ease',
};

export default MainHomePage;
