import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../../../api/client';
import './css.css';
import { useLanguage } from '../../../context/LanguageContext';
import dtaLogo from '../../../assets/dta_brand_content/DTA_Logo.png';
import foodMeasuringTape from '../../../assets/misc/foodmeasuringtape.png';
import foodScale from '../../../assets/misc/foodscale.png';
import calculationTools from '../../../assets/misc/calculationtools.png';
import girlMealPlan from '../../../assets/misc/girlmealplan.png';
import noAi from '../../../assets/misc/noai.png';
import mealplanImg from '../../../assets/misc/nutritionist_mealplan.png';
import messagingImg from '../../../assets/misc/messagingbubbles.png';
import trainerImg from '../../../assets/misc/personaltrainer.png';

const foodImagesContext = require.context('../../../assets/foods_png', false, /\.(png|jpe?g|webp)$/i);

const foodSlides = foodImagesContext.keys().map((key) => {
  const src = foodImagesContext(key);
  const rawName = key.replace('./', '').replace(/\.[^/.]+$/, '');
  const title = rawName.replace(/\s+/g, ' ').trim();
  return { src, title };
});

const CATEGORY_ORDER = ['protein', 'carbs', 'fats'];
const CATEGORY_SLIDE_DURATION_MS = 2300;

const CATEGORY_LABELS = {
  protein: 'user_home.protein',
  carbs: 'user_home.carbs',
  fats: 'user_home.fats',
};

const CATEGORY_DESCRIPTIONS = {
  protein: 'user_home.protein_desc',
  carbs: 'user_home.carbs_desc',
  fats: 'user_home.fats_desc',
};

const DTA_PLAN_OPTIONS = [
  {
    code: 'macro_calculator_free',
    name: 'Macro Calculator',
    price: 'Free',
    image: calculationTools,
    imageAlt: 'Macro calculator',
    description: 'Get your personalized macros and weekly breakdown without food assignments.',
    features: ['Macros only', 'Questionnaire-based results', 'No billing required'],
    cta: 'Send Registration Link',
  },
  {
    code: 'food_plan_monthly',
    name: 'Standard Meal Plan',
    price: '$15/month',
    image: mealplanImg,
    imageAlt: 'Meal plan',
    description: 'Food-based meal planning, weekly customization tools, and AI-generated recipes.',
    features: ['Food meal-plan generator', 'Food preferences after questionnaire', '5-day trial for first-time users'],
    cta: 'Go To Secure Checkout',
  },
  {
    code: 'food_plan_monthly_premium',
    name: 'Plan With Coaching',
    price: '$35/month',
    images: [
      { src: messagingImg, alt: 'Messaging' },
      { src: trainerImg, alt: 'Coach' },
    ],
    description: 'Everything in Standard plus coaching messaging and premium dashboard access.',
    features: ['Food plan plus coaching', 'Food preferences after questionnaire', 'Premium dashboard access'],
    cta: 'Choose Coaching Plan',
  },
];

const KEYWORDS_BY_CATEGORY = {
  protein: [
    'chicken', 'turkey', 'beef', 'bison', 'lamb', 'pork', 'ham',
    'shrimp', 'salmon', 'tuna', 'tilapia', 'cod', 'catfish', 'hake',
    'sirloin', 'steak', 'egg', 'protein powder', 'tofu', 'tempeh',
    'seitan', 'cottage cheese', 'edamame', 'mukimame', 'lentils',
    'chickpeas', 'beans',
  ],
  carbs: [
    'rice', 'oats', 'quinoa', 'bread', 'potato', 'yam', 'cereal',
    'rice cake', 'banana', 'apple', 'blueberries', 'strawberry',
    'pineapple', 'kiwi', 'grapefruit',
  ],
  fats: [
    'avocado', 'olive oil', 'cocunut oil', 'coconut oil', 'peanut butter',
    'almond butter', 'almonds', 'cashews', 'pistachios', 'walnuts', 'chia seed',
  ],
};

function shuffle(items) {
  const randomized = [...items];
  for (let i = randomized.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [randomized[i], randomized[j]] = [randomized[j], randomized[i]];
  }
  return randomized;
}

function getCategoryForFood(title) {
  const normalized = title.toLowerCase();
  for (const category of CATEGORY_ORDER) {
    if (KEYWORDS_BY_CATEGORY[category].some((keyword) => normalized.includes(keyword))) {
      return category;
    }
  }
  return 'carbs';
}

function buildCategorySlides(foods, t) {
  const grouped = {
    protein: [],
    carbs: [],
    fats: [],
  };

  foods.forEach((food) => {
    grouped[getCategoryForFood(food.title)].push(food);
  });

  return CATEGORY_ORDER.map((category) => {
    const randomizedFoods = shuffle(grouped[category]);
    return {
      id: category,
      title: t(CATEGORY_LABELS[category]),
      description: t(CATEGORY_DESCRIPTIONS[category]),
      foods: randomizedFoods,
    };
  });
}

function UserHomePage() {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const categorySlides = useMemo(() => buildCategorySlides(foodSlides, t), [t]);
  const emailInputRef = useRef(null);
  const [categoryIndices, setCategoryIndices] = useState({
    protein: 0,
    carbs: 0,
    fats: 0,
  });
  const [signupEmail, setSignupEmail] = useState('');
  const [signupMessage, setSignupMessage] = useState('');
  const [startingOfferCode, setStartingOfferCode] = useState('');

  useEffect(() => {
    const timer = setInterval(() => {
      setCategoryIndices((previous) => {
        const next = { ...previous };
        categorySlides.forEach((category) => {
          const totalFoods = category.foods.length || 1;
          next[category.id] = (previous[category.id] + 1) % totalFoods;
        });
        return next;
      });
    }, CATEGORY_SLIDE_DURATION_MS);

    return () => clearInterval(timer);
  }, [categorySlides]);

  const handlePlanSignup = async (offerCode) => {
    setSignupMessage('');
    if (!signupEmail.trim()) {
      setSignupMessage('Enter your email first so we can create your signup link.');
      emailInputRef.current?.focus();
      emailInputRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
    setStartingOfferCode(offerCode);
    try {
      const res = await apiRequest('/api/v1/users/client/signup/start/', {
        method: 'POST',
        body: {
          email: signupEmail.trim(),
          offer_code: offerCode,
          admin_slug: null,
        },
      });
      if (!res.ok) {
        throw new Error(res.data?.error?.message || 'Unable to start signup.');
      }
      if (res.data?.checkout_url) {
        window.location.href = res.data.checkout_url;
        return;
      }
      setSignupMessage('Signup started. Check your email for the registration link.');
    } catch (err) {
      console.error(err);
      setSignupMessage(err.message || 'Unable to start signup.');
    } finally {
      setStartingOfferCode('');
    }
  };

  return (
    <div className="user-home-page">
      <section className="user-story-header">
        <div className="user-brand-row">
          <img src={dtaLogo} alt="DTA logo" className="user-brand-logo" />
          <img
            src={foodMeasuringTape}
            alt="Food measuring tape"
            className="user-brand-tape"
          />
        </div>
        <div className="user-story-copy">
          <h1>{t('user_home.hero_title')}</h1>
          <p>{t('user_home.hero_subtitle')}</p>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.75rem' }}>
            <button type="button" className="user-home-button" onClick={() => navigate('/welcome')}>
              Back to Main Page
            </button>
            <button type="button" className="user-home-button" onClick={() => navigate('/admin_homepage')}>
              Admin Access
            </button>
          </div>
        </div>
      </section>

      <div className="user-login-form">
        <p className="user-login-label" style={{ margin: 0 }}>
          DTA Client Access
        </p>
        <p className="user-section-subtitle" style={{ marginTop: 0 }}>
          Already have a DTA client account? Use the dedicated DTA client login page to sign in with password or Google.
        </p>
        <button type="button" className="user-home-button" onClick={() => navigate('/user_login')}>
          Go To DTA Client Login
        </button>
        <p className="user-section-subtitle" style={{ marginTop: '0.25rem' }}>
          DTA clients log in on the DTA client login page. If you are a coach&apos;s client, use your coach link and log in from that coach page.
        </p>
        <button type="button" className="user-home-button" onClick={() => navigate('/welcome')}>
          Back to Main Page
        </button>
      </div>

      <section className="user-home-plans" aria-label="DTA plan signup options">
        <div className="user-home-plans-header">
          <h2>Choose Your Plan</h2>
          <p className="user-section-subtitle">
            Start with the macro calculator, Standard Meal Plan, or Plan With Coaching directly from this page.
          </p>
          <label className="user-home-email-field">
            Email for signup
            <input
              ref={emailInputRef}
              type="email"
              value={signupEmail}
              onChange={(event) => setSignupEmail(event.target.value)}
              placeholder="you@example.com"
            />
          </label>
          {signupMessage ? <p className="user-home-inline-message">{signupMessage}</p> : null}
        </div>
        <div className="user-home-plan-grid">
          {DTA_PLAN_OPTIONS.map((plan) => (
            <article className={`user-home-plan-card ${plan.code === 'food_plan_monthly' ? 'is-featured' : ''}`} key={plan.code}>
              <div className="user-home-plan-card-top">
                <h3>{plan.name}</h3>
                <span>{plan.price}</span>
              </div>
              {plan.images ? (
                <div className="user-home-plan-image-row">
                  {plan.images.map((image) => (
                    <img key={image.alt} src={image.src} alt={image.alt} className="user-home-plan-image small" />
                  ))}
                </div>
              ) : (
                <img src={plan.image} alt={plan.imageAlt} className="user-home-plan-image" />
              )}
              <p>{plan.description}</p>
              <ul>
                {plan.features.map((feature) => <li key={feature}>{feature}</li>)}
              </ul>
              <button type="button" className="user-home-button" onClick={() => handlePlanSignup(plan.code)} disabled={startingOfferCode === plan.code}>
                {startingOfferCode === plan.code ? 'Starting...' : plan.cta}
              </button>
            </article>
          ))}
        </div>
      </section>

      <section className="user-macro-showcase" aria-label="Macro food categories">
        <h2>{t('user_home.macros_title')}</h2>
        <p className="user-section-subtitle">{t('user_home.macros_subtitle')}</p>
        <div className="user-macro-grid">
          {categorySlides.map((category) => (
            <article className="user-macro-card" key={category.id}>
              <h3>{category.title}</h3>
              <p>{category.description}</p>
              {category.foods.length > 0 && (
                <div
                  className="user-macro-featured"
                  key={category.foods[categoryIndices[category.id]].src}
                >
                  <img
                    src={category.foods[categoryIndices[category.id]].src}
                    alt={category.foods[categoryIndices[category.id]].title}
                    className="user-food-image"
                  />
                  <span>{category.foods[categoryIndices[category.id]].title}</span>
                </div>
              )}
            </article>
          ))}
        </div>
      </section>

      <section className="user-how-it-works" aria-label="How DTA calculates meal plans">
        <h2>{t('user_home.how_title')}</h2>
        <div className="user-process-grid">
          <article className="user-process-card">
            <img src={calculationTools} alt="Calculation tools" className="user-process-image" />
            <h3>{t('user_home.math_title')}</h3>
            <p>{t('user_home.math_text')}</p>
          </article>
          <article className="user-process-card">
            <img src={foodScale} alt="Food scale" className="user-process-image" />
            <h3>{t('user_home.measure_title')}</h3>
            <p>{t('user_home.measure_text')}</p>
          </article>
          <article className="user-process-card">
            <img src={girlMealPlan} alt="Woman with a meal plan" className="user-process-image" />
            <h3>{t('user_home.follow_title')}</h3>
            <p>{t('user_home.follow_text')}</p>
          </article>
        </div>
      </section>

      <section className="user-noai-section" aria-label="No AI-based calculations">
        <div className="user-noai-image-wrap">
          <img src={noAi} alt="No AI, real human-led calculation" className="user-noai-image" />
        </div>
        <div className="user-noai-copy">
          <h2>{t('user_home.no_ai_title')}</h2>
          <p>{t('user_home.no_ai_text_1')}</p>
          <p>{t('user_home.no_ai_text_2')}</p>
        </div>
      </section>
    </div>
  );
}

export default UserHomePage;
