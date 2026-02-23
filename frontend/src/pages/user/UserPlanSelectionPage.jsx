import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { apiRequest } from '../../api/client';
import './UserPlanSelectionPage.css';

const DTA_DIRECT_PAGE = {
  admin_page: {
    brand_name: 'DTA',
    admin_slug: null,
    sale_channel: 'dta_direct',
  },
  offers: [
    {
      code: 'macro_calculator_free',
      name: 'Macro Calculator',
      price_label: 'Free',
      trial_days: 0,
      description: 'Get your macro calculations and weekly macro breakdown with a DTA account.',
      includes_food_plan: false,
      billing: 'free',
      featured: false,
    },
    {
      code: 'food_plan_weekly',
      name: 'Meal Plan With Foods (Weekly)',
      price_label: '$5/week',
      trial_days: 5,
      description: 'Includes food-based meal planning, food preferences, and weekly meal customization.',
      includes_food_plan: true,
      billing: 'weekly',
      featured: true,
    },
    {
      code: 'food_plan_monthly',
      name: 'Meal Plan With Foods (Monthly)',
      price_label: '$15/month',
      trial_days: 5,
      description: 'Monthly access with food-based meal planning and full weekly customization tools.',
      includes_food_plan: true,
      billing: 'monthly',
      featured: false,
    },
  ],
};

function UserPlanSelectionPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { adminSlug } = useParams();
  const [status, setStatus] = useState('loading');
  const [pageData, setPageData] = useState(null);
  const [error, setError] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [ctaMessage, setCtaMessage] = useState('');
  const [startingOfferCode, setStartingOfferCode] = useState('');

  const focusOffer = location.state?.focusOffer;

  useEffect(() => {
    let ignore = false;
    const load = async () => {
      if (!adminSlug) {
        setPageData(DTA_DIRECT_PAGE);
        setStatus('ready');
        return;
      }
      try {
        setStatus('loading');
        setError('');
        const res = await apiRequest(`/api/v1/users/client/public/admin-page/${adminSlug}/`);
        if (ignore) return;
        if (!res.ok) {
          setStatus('error');
          setError(res.data?.error?.message || 'Unable to load plan options.');
          return;
        }
        setPageData(res.data);
        setStatus('ready');
      } catch (err) {
        console.error('Failed to load user plans:', err);
        if (!ignore) {
          setStatus('error');
          setError('Network error while loading plan options.');
        }
      }
    };
    load();
    return () => { ignore = true; };
  }, [adminSlug]);

  const handleHomeCTA = () => {
    if (adminSlug) navigate(`/start/${adminSlug}`);
    else navigate('/user_homepage');
  };
  const handleLoginCTA = () => {
    if (adminSlug) navigate(`/start/${adminSlug}/login`);
    else navigate('/user_login');
  };

  const offers = pageData?.offers || [];
  const sortedOffers = useMemo(() => {
    if (!focusOffer) return offers;
    return [...offers].sort((a, b) => (a.code === focusOffer ? -1 : b.code === focusOffer ? 1 : 0));
  }, [offers, focusOffer]);

  const handleOfferSelect = (offer) => {
    setCtaMessage('');
    if (!signupEmail.trim()) {
      setCtaMessage('Enter your email first so we can create your registration link.');
      return;
    }
    setStartingOfferCode(offer.code);
    apiRequest('/api/v1/users/client/signup/start/', {
      method: 'POST',
      body: {
        email: signupEmail.trim(),
        offer_code: offer.code,
        admin_slug: adminSlug,
      },
    })
      .then((res) => {
        if (!res.ok) {
          throw new Error(res.data?.error?.message || 'Unable to start signup.');
        }
        setCtaMessage('Signup started. Check the backend terminal for the registration link (email simulation).');
      })
      .catch((err) => {
        console.error(err);
        setCtaMessage(err.message || 'Unable to start signup.');
      })
      .finally(() => setStartingOfferCode(''));
  };

  if (status === 'loading') {
    return <div className="user-plan-page"><p>Loading plan options…</p></div>;
  }

  if (status === 'error') {
    return (
      <div className="user-plan-page">
        <h2>Plan Options Unavailable</h2>
        <p>{error}</p>
        <button onClick={() => navigate('/welcome')} className="user-plan-button">Back to Main Site</button>
      </div>
    );
  }

  const brandName = pageData?.admin_page?.brand_name || 'DTA';

  return (
    <div className="user-plan-page">
      <div className="user-plan-header-card">
        <p className="user-plan-brand">{brandName}</p>
        <h2>Choose Your Access</h2>
        <p>
          Free macro calculator for everyone. Paid meal-plan options include a free 5-day trial for first-time users, then continue weekly or monthly.
        </p>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button type="button" className="user-plan-button user-plan-button-secondary" onClick={handleLoginCTA}>
            Existing Client Login
          </button>
        </div>
        <label className="user-plan-email-field">
          Email (we will send your registration link)
          <input
            type="email"
            value={signupEmail}
            onChange={(e) => setSignupEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </label>
        {ctaMessage && <p className="user-plan-inline-message">{ctaMessage}</p>}
      </div>

      <div className="user-plan-grid">
        {sortedOffers.map((offer) => (
          <article key={offer.code} className={`user-plan-card ${offer.featured ? 'is-featured' : ''}`}>
            <div className="user-plan-card-top">
              <h3>{offer.name}</h3>
              <span className="user-plan-price">{offer.price_label}</span>
            </div>
            {offer.trial_days > 0 ? (
              <p className="user-plan-trial">{offer.trial_days}-day free trial for first-time users</p>
            ) : (
              <p className="user-plan-trial is-free">Free account + login required</p>
            )}
            <p className="user-plan-description">{offer.description}</p>
            <ul className="user-plan-features">
              <li>{offer.includes_food_plan ? 'Includes foods + meal structure' : 'Macros only (no food assignments)'}</li>
              <li>Questionnaire required before dashboard access</li>
              <li>{offer.billing === 'free' ? 'No billing required' : `Billing cadence: ${offer.billing}`}</li>
            </ul>
            <button type="button" className="user-plan-button" onClick={() => handleOfferSelect(offer)}>
              {startingOfferCode === offer.code
                ? 'Starting…'
                : (offer.billing === 'free' ? 'Send Registration Link' : 'Start Free Trial')}
            </button>
          </article>
        ))}
      </div>

      <button onClick={handleHomeCTA} className="user-plan-button user-plan-button-secondary">
        {adminSlug ? 'Back to Coach Page' : 'Back to DTA'}
      </button>
    </div>
  );
}

export default UserPlanSelectionPage;
