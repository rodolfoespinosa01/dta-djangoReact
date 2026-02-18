import React from 'react';
import { useNavigate } from 'react-router-dom';
import './UserHomePage.css';

function UserHomePage() {
  const navigate = useNavigate();

  const handleCTA = () => {
    navigate('/user-plans');
  };

  const handleHomeCTA = () => {
    navigate('/');
  };

  return (
    <div className="user-home-page">
      <h1>Welcome to DTA - Users</h1>
      <p>Your all-in-one platform for creating personalized diet plans.</p>

      <button onClick={handleCTA} className="user-home-button">
        See Available plans for Users
      </button>

      <button onClick={handleHomeCTA} className="user-home-button">
        Back to Main Page
      </button>
    </div>
  );
}

export default UserHomePage;
