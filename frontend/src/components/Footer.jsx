import React from 'react';
import logo from '../assets/dta_brand_content/DTA_Logo.png';
import { useLanguage } from '../context/LanguageContext';
import './Footer.css';
import logoWhite from '../assets/dta_brand_content/DTA_Logo_white.png';

function Footer({ adminTheme = null }) {
  const { t } = useLanguage();
  const logoSrc = adminTheme === 'dark' ? logoWhite : logo;

  return (
    <footer className="site-footer">
      <img src={logoSrc} alt="DTA logo" className="site-footer-logo" />
      <p className="site-footer-copy">{t('footer.platform')}</p>
      <p className="site-footer-note">{t('footer.developed_by')}</p>
    </footer>
  );
}

export default Footer;
