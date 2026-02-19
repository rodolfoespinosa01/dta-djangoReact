import React from 'react';
import logo from '../assets/dta_brand_content/DTA_Logo.png';
import './Footer.css';

function Footer() {
  return (
    <footer className="site-footer">
      <img src={logo} alt="DTA logo" className="site-footer-logo" />
      <p className="site-footer-copy">DTA Platform</p>
      <p className="site-footer-note">Developed by Rodolfo E.N.</p>
    </footer>
  );
}

export default Footer;
