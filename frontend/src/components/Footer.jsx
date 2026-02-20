import React from 'react';
import logo from '../assets/dta_brand_content/DTA_Logo.png';
import { useLanguage } from '../context/LanguageContext';
import './Footer.css';

function Footer() {
  const { t } = useLanguage();

  return (
    <footer className="site-footer">
      <img src={logo} alt="DTA logo" className="site-footer-logo" />
      <p className="site-footer-copy">{t('footer.platform')}</p>
      <p className="site-footer-note">{t('footer.developed_by')}</p>
    </footer>
  );
}

export default Footer;
