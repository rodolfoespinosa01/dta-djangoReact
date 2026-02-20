import React from 'react';
import usaFlag from '../../assets/misc/usa.png';
import spainFlag from '../../assets/misc/spain.png';
import { useLanguage } from '../../context/LanguageContext';
import './LanguageToggle.css';

function LanguageToggle() {
  const { language, setLanguage, t } = useLanguage();

  return (
    <div className="language-toggle" role="group" aria-label="Language toggle">
      <button
        type="button"
        className={`language-btn ${language === 'en' ? 'active' : ''}`}
        onClick={() => setLanguage('en')}
        aria-label={t('language.switch_to_english')}
      >
        <img src={usaFlag} alt={t('language.english')} className="language-flag" />
      </button>
      <button
        type="button"
        className={`language-btn ${language === 'es' ? 'active' : ''}`}
        onClick={() => setLanguage('es')}
        aria-label={t('language.switch_to_spanish')}
      >
        <img src={spainFlag} alt={t('language.spanish')} className="language-flag" />
      </button>
    </div>
  );
}

export default LanguageToggle;
