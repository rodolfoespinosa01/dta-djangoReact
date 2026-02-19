import React from 'react';
import { useNavigate } from 'react-router-dom';
import welcomeImage from '../../assets/dta_brand_content/welcome_DTA.jpg';
import './MainWelcomeScreen.css';

function MainWelcomeScreen() {
  const navigate = useNavigate();

  return (
    <div className="main-welcome-page">
      <div className="main-welcome-content">
        <section className="main-welcome-hero">
          <div className="main-welcome-image-wrap">
            <img src={welcomeImage} alt="DTA welcome" className="main-welcome-image" />
          </div>
          <div className="main-welcome-overlay">
            <p className="main-welcome-prompt">Choose your entry point to continue.</p>
            <div className="main-welcome-actions">
              <button onClick={() => navigate('/admin_homepage')} className="main-welcome-btn">
                Go to Admin Flow
              </button>
              <button onClick={() => navigate('/user_homepage')} className="main-welcome-btn secondary">
                Go to EndUser Flow
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default MainWelcomeScreen;
