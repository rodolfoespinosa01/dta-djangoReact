import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../../../context/LanguageContext';
import './AdminHomePage.css';
import strengthCoach from '../../../assets/misc/strengthcoach.png';
import nutritionistCartoon from '../../../assets/misc/nutritionistcartoon.png';
import animeTrainer from '../../../assets/misc/animetrainer.png';
import calculationTools from '../../../assets/misc/calculationtools.png';
import foodMeasuringTape from '../../../assets/misc/foodmeasuringtape.png';
import foodScale from '../../../assets/misc/foodscale.png';
import noAi from '../../../assets/misc/noai.png';
import chickenMeal from '../../../assets/misc/chickenmeal.png';
import salad from '../../../assets/misc/salad.png';
import girlMealPlan from '../../../assets/misc/girlmealplan.png';
import nutritionistMealPlan from '../../../assets/misc/nutritionist_mealplan.png';

function AdminHomePage() {
  const navigate = useNavigate();
  const { t } = useLanguage();

  return (
    <div className="admin-home-wrapper">
      <div className="admin-home-shell">
        <section className="admin-home-hero">
          <div className="admin-home-hero-copy">
            <h1 className="admin-home-title">{t('admin_home.title')}</h1>
            <p className="admin-home-subtitle">{t('admin_home.subtitle')}</p>
            <div className="admin-home-actions">
              <button
                onClick={() => navigate('/admin_login')}
                className="admin-home-button primary"
              >
                {t('admin_home.admin_login')}
              </button>
              <button
                onClick={() => navigate('/superadmin_login')}
                className="admin-home-button secondary"
              >
                {t('admin_home.superadmin_login')}
              </button>
              <button
                onClick={() => navigate('/admin_plans')}
                className="admin-home-button tertiary"
              >
                {t('admin_home.view_plans')}
              </button>
            </div>
          </div>
          <div className="admin-home-hero-images">
            <img src={strengthCoach} alt="Strength coach" className="admin-hero-main" />
            <img src={nutritionistCartoon} alt="Nutritionist coach" className="admin-hero-side" />
            <img src={animeTrainer} alt="Trainer avatar" className="admin-hero-side" />
          </div>
        </section>

        <section className="admin-home-grid">
          <article className="admin-info-card">
            <img src={calculationTools} alt="Calculation tools" className="admin-info-image" />
            <h2>{t('admin_home.control_calc_title')}</h2>
            <p>{t('admin_home.control_calc_text')}</p>
          </article>
          <article className="admin-info-card">
            <img src={foodMeasuringTape} alt="Food measuring tape" className="admin-info-image" />
            <h2>{t('admin_home.macro_split_title')}</h2>
            <p>{t('admin_home.macro_split_text')}</p>
          </article>
          <article className="admin-info-card">
            <img src={foodScale} alt="Food scale for meal portions" className="admin-info-image" />
            <h2>{t('admin_home.portions_title')}</h2>
            <p>{t('admin_home.portions_text')}</p>
          </article>
        </section>

        <section className="admin-home-ops">
          <div className="admin-ops-copy">
            <h2>{t('admin_home.workflow_title')}</h2>
            <ul>
              <li>{t('admin_home.li1')}</li>
              <li>{t('admin_home.li2')}</li>
              <li>{t('admin_home.li3')}</li>
              <li>{t('admin_home.li4')}</li>
              <li>{t('admin_home.li5')}</li>
            </ul>
          </div>
          <div className="admin-ops-gallery">
            <img src={girlMealPlan} alt="Client with meal plan" className="admin-ops-image" />
            <img src={nutritionistMealPlan} alt="Nutritionist meal plan process" className="admin-ops-image" />
            <img src={chickenMeal} alt="Chicken meal example" className="admin-ops-image" />
            <img src={salad} alt="Salad meal example" className="admin-ops-image" />
          </div>
        </section>

        <section className="admin-noai-banner">
          <img src={noAi} alt="No AI based calculations" className="admin-noai-image" />
          <p>{t('admin_home.no_ai')}</p>
        </section>
      </div>
    </div>
  );
}

export default AdminHomePage;
