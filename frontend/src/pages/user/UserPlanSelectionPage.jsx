import React from 'react';
import { useNavigate } from 'react-router-dom';
import './UserPlanSelectionPage.css';

function UserPlanSelectionPage() {
  const navigate = useNavigate();

  const handleHomeCTA = () => {
    navigate('/');
  };

  return (
    <div className="user-plan-page">
      <h2>Select a User Plan</h2>
      <p>Later will set up plans for user</p>
      <button onClick={handleHomeCTA} className="user-plan-button">
        Back to Main Page
      </button>
    </div>
  );
}

export default UserPlanSelectionPage;
