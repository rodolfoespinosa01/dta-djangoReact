import React from 'react';
import { useNavigate } from 'react-router-dom';

function AdminHomePage() {
  const navigate = useNavigate();

  const handleCTA = () => {
    navigate('/adminPlans'); // We'll build this page next
  };

  return (
    <div style={{ padding: '2rem', textAlign: 'center' }}>
      <h1>Welcome to DTA</h1>
      <p>Your all-in-one platform for creating personalized diet plans for your clients.</p>
      <button onClick={handleCTA} style={{ marginTop: '1rem', padding: '1rem 2rem', fontSize: '1rem' }}>
        Start Free Trial
      </button>
    </div>
  );
}

export default AdminHomePage;
