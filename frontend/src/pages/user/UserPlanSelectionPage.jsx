import React from 'react';
import { useNavigate } from 'react-router-dom';

function UserPlanSelectionPage() {
  const navigate = useNavigate();

  const handleHomeCTA = () => {
    navigate('/');
  };

  return (
    <div style={{ padding: '2rem', textAlign: 'center' }}>
      <h2>Select a User Plan</h2>
    <p>Later will set up plans for user</p>
    <button onClick={handleHomeCTA} style={{ marginTop: '1rem', padding: '1rem 2rem', fontSize: '1rem' }}>
        Back to Main Page
      </button>
    </div>
  );
}

export default UserPlanSelectionPage;
