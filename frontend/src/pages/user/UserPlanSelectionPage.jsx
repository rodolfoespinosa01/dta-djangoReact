import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { apiRequest } from '../../api/client';
import { getAdminSlugFromHostname } from '../../utils/branding';
import './UserPlanSelectionPage.css';
import calcImg from '../../assets/misc/calculationtools.png';
import tapeImg from '../../assets/misc/foodmeasuringtape.png';
import mealplanImg from '../../assets/misc/nutritionist_mealplan.png';
import aiImg from '../../assets/misc/ailogo.png';
import messagingImg from '../../assets/misc/messagingbubbles.png';
import trainerImg from '../../assets/misc/personaltrainer.png';

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
  const [themeClass, setThemeClass] = useState('');
  const [customCssUrl, setCustomCssUrl] = useState(null);
  // Determine if this admin should use dark theme
  const isDarkTheme = (effectiveAdminSlug || '').toLowerCase() === 'rodolfo';
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
  const emailInputRef = useRef(null);

  useEffect(() => {
    // Dynamically load custom CSS if present in pageData
    if (pageData?.admin_page) {
      const theme = pageData.admin_page.marketing_theme;
      const cssUrl = pageData.admin_page.custom_css_url;
      setThemeClass(theme ? `user-plan-page-theme-${theme}` : '');
      setCustomCssUrl(cssUrl || null);
      if (cssUrl) {
        // Remove any previous custom CSS
        const prev = document.getElementById('admin-custom-css');
        if (prev) prev.remove();
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.id = 'admin-custom-css';
        link.href = cssUrl;
        document.head.appendChild(link);
      } else {
        const prev = document.getElementById('admin-custom-css');
        if (prev) prev.remove();
      }
    }
  }, [pageData]);

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
          // If branded page lookup fails, fallback to direct DTA page instead of crashing UX.
          setPageData(DTA_DIRECT_PAGE);
          setStatus('ready');
          setError('');
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
  const premiumOffer = useMemo(
    () => paidOffers.find((o) => o.billing === 'monthly' && Boolean(o.includes_coaching)) || null,
    [paidOffers],
  );

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
      if (emailInputRef.current) {
        emailInputRef.current.focus();
        emailInputRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
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
    <div className={['user-plan-page', themeClass].filter(Boolean).join(' ')}> 
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
        {pageData?.admin_page?.marketing_html ? (
          <div dangerouslySetInnerHTML={{ __html: pageData.admin_page.marketing_html }} />
        ) : (
          <>
            <h2>{pageData?.admin_page?.headline || 'Choose Your Meal Plan'}</h2>
            {pageData?.admin_page?.marketing_image_url && (
              <img src={pageData.admin_page.marketing_image_url} alt="Marketing" style={{ maxWidth: '100%', maxHeight: 180, margin: '0.7rem auto', borderRadius: 12 }} />
            )}
            <p className="user-plan-subheadline">
              <strong>{pageData?.admin_page?.subheadline || 'We do the exact calculation needed to get you closest to your macro goals. Guaranteed measurements. AI-generated recipes included.'}</strong>
            </p>
          </>
        )}
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
            ref={emailInputRef}
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
          <article key={freeOffer.code} className="user-plan-card user-plan-card-free">
            <div className="user-plan-card-top">
              <h3>{freeOffer.name}</h3>
              <span className="user-plan-price user-plan-blink">FREE!!!</span>
            </div>
            <img src={calcImg} alt="Macro Calculator" className="user-plan-img" style={{ maxHeight: 80, margin: '0.5rem auto' }} />
            <p className="user-plan-trial is-free">Absolutely free – no payment required!</p>
            <p className="user-plan-description"><b>Get your personalized macros calculated for FREE!</b> No signup required. Instantly see your weekly macro breakdown.</p>
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
            <h3>Standard Meal Plan</h3>
            <span className="user-plan-price">
              {quoteLoading ? 'Updating…' : (paidQuote ? `$${((paidQuote.amounts?.total_cents || 0) / 100).toFixed(2)}` : (selectedPaidOffer?.price_label || '-'))}
            </span>
          </div>
          <img src={mealplanImg} alt="Meal Plan" className="user-plan-img" style={{ maxHeight: 80, margin: '0.5rem auto' }} />
          <p className="user-plan-trial">
            {paidQuote?.trial_days ? `${paidQuote.trial_days}-day free trial for first-time users` : 'Card required to begin paid access'}
          </p>
          <p className="user-plan-description">
            <b>Let us do the work!</b> We’ll generate a meal plan that gets you as close as possible to your macro goals. <b>AI-generated recipes included.</b> Guaranteed measurements.
          </p>
          <ul className="user-plan-features">
            <li>Food meal-plan generator (no coaching)</li>
            <li>AI-generated recipes included</li>
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

        <article className="user-plan-card">
          <div className="user-plan-card-top">
            <h3>Premium + Coaching</h3>
            <span className="user-plan-price">$35/month</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 10, margin: '0.5rem 0' }}>
            <img src={messagingImg} alt="Messaging Bubbles" className="user-plan-img" style={{ maxHeight: 60, width: 'auto' }} />
            <img src={trainerImg} alt="Personal Trainer" className="user-plan-img" style={{ maxHeight: 60, width: 'auto' }} />
          </div>
          <p className="user-plan-trial">Everything in Standard, <b>plus your own coach!</b></p>
          <p className="user-plan-description">
            <b>Unlock the best results!</b> Get a personal trainer who checks in with you, makes adjustments to your plan, and ensures you stay on track. <b>AI-generated recipes included.</b> Premium dashboard access.
          </p>
          <ul className="user-plan-features">
            <li>Food meal-plan generator + 1:1 coaching</li>
            <li>Regular check-ins and plan adjustments by your trainer</li>
            <li>AI-generated recipes included</li>
            <li>Premium dashboard access</li>
            <li>Billing cadence: monthly</li>
            <li>Selection: Premium + Coaching</li>
          </ul>
          <button
            type="button"
            className="user-plan-button"
            onClick={() => {
              setIncludeCoaching(true);
              if (!premiumOffer) {
                setCtaMessage('Premium coaching option is not available right now.');
                return;
              }
              handleOfferSelect(premiumOffer);
            }}
            disabled={!premiumOffer}
          >
            {startingOfferCode === premiumOffer?.code ? 'Starting…' : 'Choose Premium + Coaching'}
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
