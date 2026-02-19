import React, { useEffect, useMemo, useState } from 'react';
import './UserHomePage.css';

const foodImagesContext = require.context('../../assets/foods_png', false, /\.(png|jpe?g|webp)$/i);
const SLIDE_DURATION_MS = 2600;

const foodSlides = foodImagesContext.keys().map((key) => {
  const src = foodImagesContext(key);
  const rawName = key.replace('./', '').replace(/\.[^/.]+$/, '');
  const title = rawName.replace(/\s+/g, ' ').trim();
  return { src, title };
});

function UserHomePage() {
  const slides = useMemo(() => foodSlides, []);
  const [slideIndex, setSlideIndex] = useState(0);

  useEffect(() => {
    if (!slides.length) {
      return;
    }

    const timer = setInterval(() => {
      setSlideIndex((prev) => (prev + 1) % slides.length);
    }, SLIDE_DURATION_MS);

    return () => clearInterval(timer);
  }, [slides]);

  const currentSlide = slides[slideIndex];

  return (
    <div className="user-home-page">
      <h1>User Login</h1>
      <p>Sign in with your email and password.</p>
      <form className="user-login-form">
        <label className="user-login-label" htmlFor="user-email">
          Email
        </label>
        <input
          id="user-email"
          type="email"
          className="user-login-input"
          placeholder="you@example.com"
          autoComplete="email"
        />
        <label className="user-login-label" htmlFor="user-password">
          Password
        </label>
        <input
          id="user-password"
          type="password"
          className="user-login-input"
          placeholder="Enter your password"
          autoComplete="current-password"
        />
        <button type="button" className="user-home-button" disabled>
          Log In (Coming Soon)
        </button>
      </form>
      <section className="user-food-showcase" aria-live="polite">
        <h2 className="user-food-title">Pick and Choose your foods, we'll do the calculation on our end!</h2>
        {currentSlide && (
          <div className="user-food-slide" key={currentSlide.src}>
            <img
              src={currentSlide.src}
              alt={currentSlide.title}
              className="user-food-image"
            />
            <p className="user-food-name">{currentSlide.title}</p>
          </div>
        )}
      </section>
    </div>
  );
}

export default UserHomePage;
