import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiRequest } from '../../../api/client';
import './css.css';

function AdminClientLandingPage() {
  const { adminSlug } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('loading');
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let ignore = false;
    const load = async () => {
      setStatus('loading');
      setError('');
      try {
        const res = await apiRequest(`/api/v1/users/client/public/admin-page/${adminSlug}/`);
        if (ignore) return;
        if (!res.ok) {
          setStatus('error');
          setError(res.data?.error?.message || 'Unable to load this coach page.');
          return;
        }
        if (!res.data || !res.data.admin_page) {
          setStatus('error');
          setError('This coach page is unavailable right now.');
          return;
        }
        setData(res.data);
        setStatus('ready');
      } catch (err) {
        console.error('Public admin page load error:', err);
        if (!ignore) {
          setStatus('error');
          setError('Network error while loading this page.');
        }
      }
    };
    load();
    return () => { ignore = true; };
  }, [adminSlug]);

  const featuredOffer = useMemo(
    () => (data?.offers || []).find((offer) => offer.featured) || (data?.offers || [])[0],
    [data]
  );

  if (status === 'loading') {
    return <div className="admin-client-landing-page"><p className="admin-client-loading">Loading coach page…</p></div>;
  }

  if (status === 'error') {
    return (
      <div className="admin-client-landing-page">
        <div className="admin-client-error-card">
          <h2>Coach Page Not Available</h2>
          <p>{error}</p>
          <button type="button" onClick={() => navigate('/welcome')}>Back to Main Site</button>
        </div>
      </div>
    );
  }

  const adminPage = data?.admin_page || {};

  return (
    <div className="admin-client-landing-page">
      <section className="admin-client-hero">
        <div className="admin-client-badge">{adminPage.slug}.dtameals.com</div>
        <h1>{adminPage.brand_name}</h1>
        <p className="admin-client-headline">{adminPage.headline}</p>
        <p className="admin-client-subheadline">{adminPage.subheadline}</p>
        <div className="admin-client-cta-row">
          <button
            type="button"
            className="admin-client-primary-cta"
            onClick={() => navigate(`/start/${adminSlug}/plans`)}
          >
            Start Free Trial
          </button>
          <button
            type="button"
            className="admin-client-secondary-cta"
            onClick={() => navigate(`/start/${adminSlug}/plans`, { state: { focusOffer: 'macro_calculator_free' } })}
          >
            Free Macro Calculator
          </button>
          <button
            type="button"
            className="admin-client-secondary-cta"
            onClick={() => navigate(`/start/${adminSlug}/login`)}
          >
            Client Login
          </button>
        </div>
      </section>

      <section className="admin-client-offers-preview">
        <h2>Choose Your Starting Option</h2>
        <div className="admin-client-offer-grid">
          {(data?.offers || []).map((offer) => (
            <article key={offer.code} className={`admin-client-offer-card ${offer.featured ? 'is-featured' : ''}`}>
              <div className="offer-card-top">
                <h3>{offer.name}</h3>
                <span className="offer-price-pill">{offer.price_label}</span>
              </div>
              {offer.trial_days > 0 && <p className="offer-trial-pill">{offer.trial_days}-day free trial (first time users)</p>}
              <p>{offer.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="admin-client-how">
        <h2>How It Works</h2>
        <div className="admin-client-steps">
          <div><strong>1.</strong> Choose your plan option.</div>
          <div><strong>2.</strong> Complete signup and create your login.</div>
          <div><strong>3.</strong> Fill out your onboarding questionnaire.</div>
          <div><strong>4.</strong> Start with macros free or unlock food-based meal planning.</div>
        </div>
        {featuredOffer && (
          <div className="admin-client-highlight">
            <span>Most Popular:</span> {featuredOffer.name} ({featuredOffer.price_label})
          </div>
        )}
      </section>
    </div>
  );
}

export default AdminClientLandingPage;
