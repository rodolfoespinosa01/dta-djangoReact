import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import './UserPlanSelectionPage.css';

function UserPlanSelectionPage() {
  const navigate = useNavigate();
  const { t } = useLanguage();

  const handleHomeCTA = () => {
    navigate('/');
  };

  return (
    <div className="user-plan-page">
      <h2>{t('user_plan.title')}</h2>
      <p>{t('user_plan.subtitle')}</p>
      <button onClick={handleHomeCTA} className="user-plan-button">
        {t('common.back_to_main_page')}
      </button>
    </div>
  );
}

export default UserPlanSelectionPage;
