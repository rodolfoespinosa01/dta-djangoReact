import React from 'react';
import logo from '../assets/DTA_Logo.png';
import './Footer.css';

function Footer() {
  return (
    <footer className="site-footer">
      <img src={logo} alt="DTA logo" className="site-footer-logo" />
      <p className="site-footer-copy">DTA Platform</p>
    </footer>
  );
}

export default Footer;
