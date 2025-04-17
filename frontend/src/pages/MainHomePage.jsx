import React from 'react';
import { useNavigate } from 'react-router-dom';

function MainHomePage() {
  const navigate = useNavigate();

  const handleAdminCTA = () => {
    navigate('/admin-homepage'); 
  };

  const handleUserCTA = () => {
    navigate('/user-homepage'); 
  };

  return (
    <div style={{ padding: '2rem', textAlign: 'center' }}>
      <h1>Welcome to DTA</h1>
      <p>Your all-in-one platform for creating personalized diet plans.</p>
      <button onClick={handleAdminCTA} style={{ marginTop: '1rem', padding: '1rem 2rem', fontSize: '1rem' }}>
        Admin Home Page
      </button>
      <button onClick={handleUserCTA} style={{ marginTop: '1rem', padding: '1rem 2rem', fontSize: '1rem' }}>
        User Home Page
      </button>
    </div>
  );
}

export default MainHomePage;
