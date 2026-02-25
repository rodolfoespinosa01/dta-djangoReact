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
      code: 'food_plan_monthly',
      name: 'Meal Plan With Foods (Monthly)',
      price_label: '$15/month',
      trial_days: 5,
      description: 'Monthly access with food-based meal planning and full weekly customization tools.',
      includes_food_plan: true,
      billing: 'monthly',
      featured: false,
    },
    {
      code: 'food_plan_monthly_premium',
      name: 'Meal Plan + Coaching (Monthly Premium)',
      price_label: '$35/month',
      trial_days: 5,
      description: 'Best value premium tier with food planning plus coaching features and premium dashboard access.',
      includes_food_plan: true,
      includes_coaching: true,
      billing: 'monthly',
      featured: true,
    },
  ],
};

function getAdminSlugFromHostname() {
  if (typeof window === 'undefined') return '';
  const hostname = (window.location?.hostname || '').toLowerCase();
  if (!hostname) return '';
  if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === 'lvh.me') return '';
  if (hostname.endsWith('.lvh.me')) {
    const slug = hostname.slice(0, -'.lvh.me'.length);
    return slug && slug !== 'www' ? slug : '';
  }
  const parts = hostname.split('.').filter(Boolean);
  if (parts.length >= 3) {
    const sub = parts[0];
    if (sub && sub !== 'www') return sub;
  }
  return '';
}

function QuoteChip({ quote }) {
  if (!quote) return null;
  const amounts = quote.amounts || {};
  const entitlements = quote.entitlements_preview || {};
  const hasDiscount = Number(amounts.discount_cents || 0) > 0;
  const originalTotal = Number(amounts.subtotal_cents || 0) / 100;
  const discountedTotal = Number(amounts.total_cents || 0) / 100;
  return (
    <div style={{ marginTop: '0.6rem', border: '1px solid rgba(20,40,74,0.10)', borderRadius: 10, padding: '0.55rem' }}>
      <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', alignItems: 'center' }}>
        {hasDiscount ? (
          <>
            <span className="user-plan-trial is-free" style={{ textDecoration: 'line-through', opacity: 0.75 }}>
              ${originalTotal.toFixed(2)}
            </span>
            <span className="user-plan-trial">Now ${discountedTotal.toFixed(2)}</span>
          </>
        ) : (
          <span className="user-plan-trial is-free">Total ${discountedTotal.toFixed(2)}</span>
        )}
        {hasDiscount ? <span className="user-plan-trial">Discount -${(Number(amounts.discount_cents || 0) / 100).toFixed(2)}</span> : null}
        {quote.trial_days > 0 ? <span className="user-plan-trial">{quote.trial_days}-day trial</span> : null}
      </div>
      {quote.discount?.code ? (
        <p style={{ margin: '0.35rem 0 0', fontSize: '0.85rem' }}>
          Special applied: <strong>{quote.discount.code}</strong>
        </p>
      ) : null}
      {entitlements.has_premium_dashboard ? (
        <p style={{ margin: '0.35rem 0 0', fontSize: '0.85rem' }}>Includes premium coaching dashboard.</p>
      ) : null}
    </div>
  );
}

function UserPlanSelectionPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { adminSlug } = useParams();
  const hostAdminSlug = useMemo(() => getAdminSlugFromHostname(), []);
  const effectiveAdminSlug = adminSlug || hostAdminSlug || '';
  const [status, setStatus] = useState('loading');
  const [pageData, setPageData] = useState(null);
  const [error, setError] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [ctaMessage, setCtaMessage] = useState('');
  const [startingOfferCode, setStartingOfferCode] = useState('');
  const [discountCode, setDiscountCode] = useState('');
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [paidQuote, setPaidQuote] = useState(null);
  const [includeCoaching, setIncludeCoaching] = useState(false);

  useEffect(() => {
    let ignore = false;
    const load = async () => {
      if (!effectiveAdminSlug) {
        setPageData(DTA_DIRECT_PAGE);
        setStatus('ready');
        return;
      }
      try {
        setStatus('loading');
        setError('');
        const res = await apiRequest(`/api/v1/users/client/public/admin-page/${effectiveAdminSlug}/`);
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
  }, [effectiveAdminSlug]);

  useEffect(() => {
    const params = new URLSearchParams(location.search || '');
    const state = params.get('signup_checkout');
    if (state === 'success') {
      setCtaMessage('Checkout completed. Your registration link is being generated (check the email simulation / backend terminal).');
    } else if (state === 'cancel') {
      setCtaMessage('Checkout was canceled. You can preview pricing and try again when ready.');
    }
  }, [location.search]);

  const offers = useMemo(() => pageData?.offers || [], [pageData]);
  const freeOffer = useMemo(() => offers.find((o) => o.billing === 'free') || null, [offers]);
  const paidOffers = useMemo(() => offers.filter((o) => o.billing !== 'free'), [offers]);
  const selectedPaidOffer = useMemo(() => {
    const targetCoaching = includeCoaching;
    return paidOffers.find((o) => o.billing === 'monthly' && Boolean(o.includes_coaching) === targetCoaching) || null;
  }, [paidOffers, includeCoaching]);

  useEffect(() => {
    if (!selectedPaidOffer) {
      setPaidQuote(null);
      return;
    }
    let ignore = false;
    setQuoteLoading(true);
    apiRequest('/api/v1/users/client/signup/quote/', {
      method: 'POST',
      body: {
        email: signupEmail.trim(),
        offer_code: selectedPaidOffer.code,
        admin_slug: effectiveAdminSlug || null,
        discount_code: discountCode.trim(),
      },
    })
      .then((res) => {
        if (ignore) return;
        if (!res.ok) {
          setPaidQuote(null);
          if (discountCode.trim()) {
            setCtaMessage(res.data?.error?.message || 'Unable to apply discount code.');
          }
          return;
        }
        setPaidQuote(res.data?.quote || null);
        if (discountCode.trim()) {
          setCtaMessage('');
        }
      })
      .catch((err) => {
        if (ignore) return;
        console.error(err);
        setPaidQuote(null);
      })
      .finally(() => {
        if (!ignore) setQuoteLoading(false);
      });

    return () => { ignore = true; };
  // Intentionally re-run on plan toggles/admin page changes; discount code is applied on field blur.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPaidOffer, effectiveAdminSlug, includeCoaching]);

  const handleHomeCTA = () => {
    if (effectiveAdminSlug) navigate(`/start/${effectiveAdminSlug}`);
    else navigate('/user_homepage');
  };
  const handleLoginCTA = () => {
    if (effectiveAdminSlug) navigate(`/start/${effectiveAdminSlug}/login`);
    else navigate('/user_login');
  };

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
        admin_slug: effectiveAdminSlug || null,
        discount_code: discountCode.trim(),
      },
    })
      .then((res) => {
        if (!res.ok) {
          throw new Error(res.data?.error?.message || 'Unable to start signup.');
        }
        if (res.data?.checkout_url) {
          window.location.href = res.data.checkout_url;
          return;
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
  const signupCheckoutState = new URLSearchParams(location.search || '').get('signup_checkout');
  const paidOfferLabel = includeCoaching ? '1 Month + Coaching' : '1 Month (No Coaching)';

  return (
    <div className="user-plan-page">
      {signupCheckoutState === 'success' ? (
        <div className="user-plan-header-card" style={{ marginBottom: '1rem' }}>
          <p className="user-plan-brand">{brandName}</p>
          <h2>Checkout Completed</h2>
          <p>
            Payment/trial setup was completed successfully. Check your email (and backend terminal in dev) for the registration link to finish account setup.
          </p>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button type="button" className="user-plan-button user-plan-button-secondary" onClick={() => navigate(location.pathname, { replace: true })}>
              Start Another Signup
            </button>
            <button type="button" className="user-plan-button" onClick={handleLoginCTA}>
              Existing Client Login
            </button>
          </div>
        </div>
      ) : null}
      <div className="user-plan-header-card">
        <p className="user-plan-brand">{brandName}</p>
        <h2>Choose Your Access</h2>
        <p>
          Free macro calculator for everyone. Paid options are monthly only and include the food meal-plan generator.
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
        <label className="user-plan-email-field">
          Discount Code (optional)
          <input
            type="text"
            value={discountCode}
            onChange={(e) => setDiscountCode(e.target.value.toUpperCase())}
            onBlur={() => {
              // Re-run quote after editing the discount field
              if (!selectedPaidOffer) return;
              setQuoteLoading(true);
              apiRequest('/api/v1/users/client/signup/quote/', {
                method: 'POST',
                body: {
                  email: signupEmail.trim(),
                  offer_code: selectedPaidOffer.code,
                  admin_slug: effectiveAdminSlug || null,
                  discount_code: discountCode.trim(),
                },
              })
                .then((res) => {
                  if (!res.ok) {
                    setPaidQuote(null);
                    setCtaMessage(res.data?.error?.message || 'Unable to apply discount code.');
                    return;
                  }
                  setPaidQuote(res.data?.quote || null);
                  setCtaMessage('');
                })
                .catch((err) => {
                  console.error(err);
                  setCtaMessage('Unable to apply discount code.');
                })
                .finally(() => setQuoteLoading(false));
            }}
            placeholder="SUMMER20"
          />
        </label>
        {ctaMessage && <p className="user-plan-inline-message">{ctaMessage}</p>}
      </div>

      <div className="user-plan-grid">
        {freeOffer ? (
          <article key={freeOffer.code} className="user-plan-card">
            <div className="user-plan-card-top">
              <h3>{freeOffer.name}</h3>
              <span className="user-plan-price">{freeOffer.price_label}</span>
            </div>
            <p className="user-plan-trial is-free">Free account + login required</p>
            <p className="user-plan-description">{freeOffer.description}</p>
            <ul className="user-plan-features">
              <li>Macros only (no food assignments)</li>
              <li>Questionnaire required before dashboard access</li>
              <li>No billing required</li>
            </ul>
            <button type="button" className="user-plan-button" onClick={() => handleOfferSelect(freeOffer)}>
              {startingOfferCode === freeOffer.code ? 'Starting…' : 'Send Registration Link'}
            </button>
          </article>
        ) : null}

        <article className="user-plan-card is-featured">
          <div className="user-plan-card-top">
            <h3>1 Month Paid Plan</h3>
            <span className="user-plan-price">
              {quoteLoading ? 'Updating…' : (paidQuote ? `$${((paidQuote.amounts?.total_cents || 0) / 100).toFixed(2)}` : (selectedPaidOffer?.price_label || '-'))}
            </span>
          </div>
          <p className="user-plan-trial">
            {paidQuote?.trial_days ? `${paidQuote.trial_days}-day free trial for first-time users` : 'Card required to begin paid access'}
          </p>
          <p className="user-plan-description">
            Choose whether coaching is included. Both paid options include food-plan generation and go to secure Stripe checkout.
          </p>

          <div style={{ display: 'grid', gap: '0.55rem', marginTop: '0.4rem' }}>
            <div>
              <p style={{ margin: '0 0 0.3rem', fontWeight: 600 }}>Select One of the 2 Paid Options</p>
              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="user-plan-button user-plan-button-secondary"
                  onClick={() => setIncludeCoaching(false)}
                  style={{ opacity: includeCoaching ? 0.8 : 1 }}
                >
                  Standard
                </button>
                <button
                  type="button"
                  className="user-plan-button user-plan-button-secondary"
                  onClick={() => setIncludeCoaching(true)}
                  style={{ opacity: includeCoaching ? 1 : 0.8 }}
                >
                  Coaching Premium
                </button>
              </div>
            </div>
          </div>

          <ul className="user-plan-features">
            <li>{includeCoaching ? 'Food meal-plan generator + coaching features included' : 'Food meal-plan generator included (no coaching)'}</li>
            <li>Questionnaire required before dashboard access</li>
            <li>Billing cadence: monthly</li>
            <li>Selection: {paidOfferLabel}</li>
          </ul>

          <QuoteChip quote={paidQuote} />

          <button
            type="button"
            className="user-plan-button"
            onClick={() => selectedPaidOffer && handleOfferSelect(selectedPaidOffer)}
            disabled={!selectedPaidOffer}
          >
            {startingOfferCode === selectedPaidOffer?.code ? 'Starting…' : 'Go To Secure Checkout'}
          </button>
        </article>
      </div>

      <button onClick={handleHomeCTA} className="user-plan-button user-plan-button-secondary">
        {effectiveAdminSlug ? 'Back to Coach Page' : 'Back to DTA'}
      </button>
    </div>
  );
}

export default UserPlanSelectionPage;
