import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import welcomeImage from '../../assets/dta_brand_content/welcome_DTA.jpg';
import './MainWelcomeScreen.css';

function MainWelcomeScreen() {
  const navigate = useNavigate();
  const { t } = useLanguage();

  return (
    <div className="main-welcome-page">
      <div className="main-welcome-content">
        <section className="main-welcome-hero">
          <div className="main-welcome-image-wrap">
            <img src={welcomeImage} alt={t('welcome.image_alt')} className="main-welcome-image" />
          </div>
          <div className="main-welcome-overlay">
            <p className="main-welcome-prompt">{t('welcome.prompt')}</p>
            <div className="main-welcome-actions">
              <button onClick={() => navigate('/admin_homepage')} className="main-welcome-btn">
                {t('welcome.admin_flow')}
              </button>
              <button onClick={() => navigate('/user_homepage')} className="main-welcome-btn secondary">
                {t('welcome.user_flow')}
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default MainWelcomeScreen;
