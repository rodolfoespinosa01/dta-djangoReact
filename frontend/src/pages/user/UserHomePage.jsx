import React from 'react';
import { useNavigate } from 'react-router-dom';

function UserHomePage() {
  const navigate = useNavigate();

  const handleCTA = () => {
    navigate('/userPlans');
  };

  const handleHomeCTA = () => {
    navigate('/');
  };

  return (
    <div style={{ padding: '2rem', textAlign: 'center' }}>
      <h1>Welcome to DTA - Users</h1>
      <p>Your all-in-one platform for creating personalized diet plans.</p>

      <button onClick={handleCTA} style={{ marginTop: '1rem', padding: '1rem 2rem', fontSize: '1rem' }}>
        See Available plans for Users
      </button>

      <button onClick={handleHomeCTA} style={{ marginTop: '1rem', padding: '1rem 2rem', fontSize: '1rem' }}>
        Back to Main Page
      </button>
    </div>
  );
}

export default UserHomePage;
