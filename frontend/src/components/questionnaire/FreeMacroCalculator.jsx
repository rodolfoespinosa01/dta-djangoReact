import React, { useEffect, useMemo, useState } from 'react';
import { apiRequest } from '../../api/client';
import BodyVisualizationSelector, { normalizeHeightCmValue } from './BodyVisualizationSelector';
import WeightSelector, { lbsToKg, normalizeWeightLbsValue } from './WeightSelector';
import DOBSelector from './DOBSelector';
import GoalSelector from './GoalSelector';
import LifestyleSelector, { normalizeLifestyleCode } from './LifestyleSelector';
import MealPlanTypeSelector, { normalizeMealPlanTypeCode } from './MealPlanTypeSelector';
import TrainingMealTimingSelector from './TrainingMealTimingSelector';
import maleSignImage from '../../assets/questionnaire/1/malesign.png';
import femaleSignImage from '../../assets/questionnaire/1/femalesign.png';
import '../../styles/shared/client-app-shell.css';
import './FreeMacroCalculator.css';

const STORAGE_KEY = 'dta_public_macro_calculator_answers';
const EMAIL_STORAGE_KEY = 'dta_public_macro_calculator_email';
const QUESTION_STEPS = [
  'height',
  'date_of_birth',
  'goal',
  'lifestyle',
  'meal_plan_type',
  'workout_days',
  'meal_schedule',
  'training_schedule',
  'email',
];
const WEEK_DAYS = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
const DAY_TO_CODE = {
  sunday: 'sun',
  monday: 'mon',
  tuesday: 'tue',
  wednesday: 'wed',
  thursday: 'thu',
  friday: 'fri',
  saturday: 'sat',
};
const CODE_TO_DAY = Object.fromEntries(Object.entries(DAY_TO_CODE).map(([day, code]) => [code, day]));

function readStoredAnswers() {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '{}');
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch (err) {
    return {};
  }
}

function writeStoredAnswers(answers) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(answers || {}));
  } catch (err) {
    // Session storage is a convenience only; the calculator still works in memory.
  }
}

function readStoredEmail() {
  try {
    return sessionStorage.getItem(EMAIL_STORAGE_KEY) || '';
  } catch (err) {
    return '';
  }
}

function writeStoredEmail(email) {
  try {
    sessionStorage.setItem(EMAIL_STORAGE_KEY, email || '');
  } catch (err) {
    // Session storage is a convenience only; the calculator still works in memory.
  }
}

function prettyDay(day) {
  return day.charAt(0).toUpperCase() + day.slice(1);
}

function normalizeTrainingComponentValue(trainingSchedule = {}, workoutDays = []) {
  const trainingDays = workoutDays.map((day) => DAY_TO_CODE[day]).filter(Boolean);
  const dayNumbers = {};
  trainingDays.forEach((code) => {
    const day = CODE_TO_DAY[code];
    const match = /^before_meal_(\d+)$/.exec(String(trainingSchedule?.[day] || ''));
    dayNumbers[code] = match ? Number(match[1]) : 1;
  });
  return {
    mode: trainingSchedule?._mode === 'custom' ? 'custom' : 'same',
    sameBeforeMeal: Number(trainingSchedule?._default_before_meal || dayNumbers[trainingDays[0]] || 1),
    days: dayNumbers,
  };
}

function FreeMacroCalculator({ adminSlug = null, focused = false, onStart }) {
  const [phase, setPhase] = useState(() => (focused ? 'questionnaire' : 'initial'));
  const [stepIndex, setStepIndex] = useState(0);
  const [answers, setAnswers] = useState(() => readStoredAnswers());
  const [email, setEmail] = useState(() => readStoredEmail());
  const [message, setMessage] = useState('');
  const [submitState, setSubmitState] = useState('idle');
  const activeStep = QUESTION_STEPS[stepIndex];
  const activeAnswer = answers[activeStep];

  useEffect(() => {
    writeStoredAnswers(answers);
  }, [answers]);

  useEffect(() => {
    writeStoredEmail(email);
  }, [email]);

  const updateAnswer = (step, value) => {
    setAnswers((prev) => {
      const nextAnswers = { ...prev, [step]: value };
      if (step === 'workout_days') {
        const selectedDays = new Set(Array.isArray(value) ? value : []);
        const existingTraining = nextAnswers.training_schedule && typeof nextAnswers.training_schedule === 'object'
          ? nextAnswers.training_schedule
          : {};
        nextAnswers.training_schedule = Object.fromEntries(
          Object.entries(existingTraining).filter(([day]) => day.startsWith('_') || selectedDays.has(day))
        );
      }
      if (step === 'meal_schedule') {
        const mealDays = value?.days || {};
        const existingTraining = nextAnswers.training_schedule && typeof nextAnswers.training_schedule === 'object'
          ? nextAnswers.training_schedule
          : {};
        nextAnswers.training_schedule = Object.fromEntries(
          Object.entries(existingTraining).filter(([day, timing]) => {
            if (day.startsWith('_')) return true;
            const mealCount = Number(mealDays[day] || 0);
            const match = /^before_meal_(\d+)$/.exec(String(timing || ''));
            return Boolean(match) && Number(match[1]) <= mealCount;
          })
        );
      }
      return nextAnswers;
    });
    setMessage('');
  };

  const initialStepValid = useMemo(() => (
    ['male', 'female'].includes(answers.gender)
    && answers.weight !== undefined
    && Number.isFinite(normalizeWeightLbsValue(answers.weight, Number.NaN))
  ), [answers]);

  const activeStepValid = useMemo(() => {
    if (activeStep === 'email') return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
    const value = activeAnswer;
    switch (activeStep) {
      case 'height':
        return Number.isFinite(normalizeHeightCmValue(value, Number.NaN));
      case 'date_of_birth':
        return typeof value === 'string' && value.length > 0;
      case 'goal':
        return ['lose', 'maintain', 'gain'].includes(value);
      case 'meal_plan_type':
        return normalizeMealPlanTypeCode(value).length > 0;
      case 'lifestyle':
        return normalizeLifestyleCode(value).length > 0;
      case 'workout_days':
        return Array.isArray(value);
      case 'meal_schedule': {
        const days = value?.days || {};
        return WEEK_DAYS.every((day) => [3, 4, 5, 6].includes(Number(days[day])));
      }
      case 'training_schedule': {
        const selectedDays = Array.isArray(answers.workout_days) ? answers.workout_days : [];
        const mealDays = answers.meal_schedule?.days || {};
        if (!value || typeof value !== 'object') return selectedDays.length === 0;
        return selectedDays.every((day) => {
          const mealCount = Number(mealDays[day]);
          const selected = value[day];
          return [3, 4, 5, 6].includes(mealCount)
            && typeof selected === 'string'
            && /^before_meal_[1-6]$/.test(selected)
            && Number(selected.split('_').pop()) <= mealCount;
        });
      }
      default:
        return value !== undefined && value !== null && value !== '';
    }
  }, [activeStep, activeAnswer, email, answers.workout_days, answers.meal_schedule]);

  const startQuestionnaire = () => {
    if (!initialStepValid) return;
    setPhase('questionnaire');
    setStepIndex(0);
    setMessage('');
    onStart?.();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const submitCalculator = async () => {
    setSubmitState('submitting');
    setMessage('');
    try {
      const res = await apiRequest('/api/v1/users/client/public/macro-calculator/', {
        method: 'POST',
        body: {
          email: email.trim(),
          answers,
          admin_slug: adminSlug || null,
        },
      });
      if (!res.ok) {
        const missing = res.data?.error?.details?.missing_steps;
        if (Array.isArray(missing) && missing.length) {
          const firstStep = QUESTION_STEPS.indexOf(missing[0]);
          setStepIndex(firstStep >= 0 ? firstStep : 0);
          setPhase('questionnaire');
        }
        const backendMessage = res.data?.error?.message || res.data?.detail;
        setMessage(backendMessage || `Unable to send your macro link. Server returned ${res.status}.`);
        setSubmitState('idle');
        return;
      }
      if (res.data?.debug_registration_link) {
        console.log('Public macro registration link:', res.data.debug_registration_link);
      }
      setPhase('confirmation');
      setSubmitState('success');
    } catch (err) {
      console.error(err);
      setMessage('Network error while sending your macro link.');
      setSubmitState('idle');
    }
  };

  const renderInitialStep = () => {
    const weightUnit = answers.weight?.unit === 'kg' ? 'kg' : 'lbs';
    const currentWeightLbs = normalizeWeightLbsValue(answers.weight);

    return (
      <div className="free-macro-initial-grid compact">
        <div className="free-macro-field-group">
          <h3>Gender</h3>
          <div className="client-q-card-grid">
            {['male', 'female'].map((v) => (
              <button key={v} type="button" className={`client-q-option-card ${answers.gender === v ? 'is-active' : ''}`} onClick={() => updateAnswer('gender', v)}>
                <span className="client-q-option-icon" aria-hidden="true">
                  <img className="client-q-option-icon-image" src={v === 'male' ? maleSignImage : femaleSignImage} alt="" />
                </span>
                <span>{v === 'male' ? 'Male' : 'Female'}</span>
              </button>
            ))}
          </div>
        </div>
        <WeightSelector
          value={currentWeightLbs}
          unit={weightUnit}
          allowUnitToggle
          onUnitChange={(nextUnit) => {
            const normalizedLbs = normalizeWeightLbsValue(answers.weight);
            updateAnswer('weight', {
              unit: nextUnit,
              value: nextUnit === 'kg' ? lbsToKg(normalizedLbs) : Math.round(normalizedLbs),
            });
          }}
          onChange={(nextLbs) => {
            updateAnswer('weight', {
              unit: weightUnit,
              value: weightUnit === 'kg' ? lbsToKg(nextLbs) : Math.round(nextLbs),
            });
          }}
        />
      </div>
    );
  };

  const renderQuestionStep = () => {
    switch (activeStep) {
      case 'height':
        return (
          <BodyVisualizationSelector
            value={activeAnswer}
            gender={answers?.gender === 'female' ? 'female' : 'male'}
            onChange={(heightCm) => updateAnswer(activeStep, heightCm)}
          />
        );
      case 'date_of_birth':
        return (
          <div className="free-macro-dob-wrap">
            <DOBSelector value={activeAnswer ?? ''} gender={answers?.gender === 'female' ? 'female' : 'male'} onChange={(dobIso) => updateAnswer(activeStep, dobIso)} />
          </div>
        );
      case 'goal':
        return <GoalSelector value={activeAnswer ?? ''} gender={answers?.gender === 'female' ? 'female' : 'male'} onChange={(goalKey) => updateAnswer(activeStep, goalKey)} />;
      case 'lifestyle':
        return <LifestyleSelector value={activeAnswer ?? ''} gender={answers?.gender === 'female' ? 'female' : 'male'} onChange={(lifestyleCode) => updateAnswer(activeStep, lifestyleCode)} />;
      case 'meal_plan_type':
        return <MealPlanTypeSelector value={activeAnswer ?? ''} onChange={(mealPlanTypeCode) => updateAnswer(activeStep, mealPlanTypeCode)} />;
      case 'workout_days': {
        const selected = Array.isArray(activeAnswer) ? activeAnswer : [];
        return (
          <div className="client-q-stack">
            <p className="client-q-help">Select every day you plan to work out.</p>
            <div className="client-q-day-grid">
              {WEEK_DAYS.map((day) => {
                const on = selected.includes(day);
                return (
                  <button key={day} type="button" className={`client-q-day ${on ? 'is-active' : ''}`} onClick={() => updateAnswer(activeStep, on ? selected.filter((d) => d !== day) : [...selected, day])}>
                    {day.slice(0, 3).toUpperCase()}
                  </button>
                );
              })}
            </div>
          </div>
        );
      }
      case 'meal_schedule': {
        const existingDays = activeAnswer?.days || {};
        const firstDayValue = Number(existingDays[WEEK_DAYS[0]] || 3);
        const inferredSame = WEEK_DAYS.every((day) => Number(existingDays[day] || firstDayValue) === firstDayValue);
        const value = {
          mode: activeAnswer?.mode || (inferredSame ? 'same' : 'custom'),
          default_meals: Number(activeAnswer?.default_meals || firstDayValue || 3),
          days: WEEK_DAYS.reduce((acc, day) => {
            acc[day] = [3, 4, 5, 6].includes(Number(existingDays[day])) ? Number(existingDays[day]) : 3;
            return acc;
          }, {}),
        };
        const setSameMeals = (count) => updateAnswer(activeStep, {
          mode: 'same',
          default_meals: count,
          days: WEEK_DAYS.reduce((acc, day) => ({ ...acc, [day]: count }), {}),
        });
        return (
          <div className="client-q-stack">
            <p className="client-q-help">Choose one meal amount for all days, or customize each day of the week.</p>
            <div className="client-q-toggle">
              <button type="button" className={value.mode === 'same' ? 'is-active' : ''} onClick={() => updateAnswer(activeStep, { ...value, mode: 'same' })}>Same for all days</button>
              <button type="button" className={value.mode === 'custom' ? 'is-active' : ''} onClick={() => updateAnswer(activeStep, { ...value, mode: 'custom' })}>Customize by day</button>
            </div>
            <div className="client-q-card-grid">
              {[3, 4, 5, 6].map((count) => (
                <button key={`same-${count}`} type="button" className={`client-q-option-card ${value.mode === 'same' && Number(value.default_meals) === count ? 'is-active' : ''}`} onClick={() => setSameMeals(count)}>
                  <span>{count} Meals</span>
                </button>
              ))}
            </div>
            {value.mode === 'custom' ? WEEK_DAYS.map((day) => (
              <div key={day} className="client-q-stack">
                <strong>{prettyDay(day)}</strong>
                <div className="client-q-card-grid">
                  {[3, 4, 5, 6].map((count) => (
                    <button key={`${day}-${count}`} type="button" className={`client-q-option-card ${Number(value.days[day]) === count ? 'is-active' : ''}`} onClick={() => updateAnswer(activeStep, { ...value, mode: 'custom', days: { ...value.days, [day]: count } })}>
                      <span>{count}</span>
                    </button>
                  ))}
                </div>
              </div>
            )) : null}
          </div>
        );
      }
      case 'training_schedule': {
        const selectedDays = Array.isArray(answers.workout_days) ? answers.workout_days : [];
        const trainingDays = selectedDays.map((day) => DAY_TO_CODE[day]).filter(Boolean);
        const mealScheduleByDay = Object.fromEntries(
          trainingDays.map((code) => [code, Number(answers.meal_schedule?.days?.[CODE_TO_DAY[code]] || 3)])
        );
        const componentValue = normalizeTrainingComponentValue(activeAnswer, selectedDays);
        return (
          <TrainingMealTimingSelector
            gender={answers?.gender === 'female' ? 'female' : 'male'}
            trainingDays={trainingDays}
            mealScheduleByDay={mealScheduleByDay}
            value={componentValue}
            onChange={(nextValue) => {
              const nextSchedule = {
                _mode: nextValue?.mode === 'custom' ? 'custom' : 'same',
                _default_before_meal: Number(nextValue?.sameBeforeMeal || 1),
              };
              trainingDays.forEach((code) => {
                const day = CODE_TO_DAY[code];
                const beforeMeal = Number(nextValue?.days?.[code] || nextValue?.sameBeforeMeal || 1);
                nextSchedule[day] = `before_meal_${beforeMeal}`;
              });
              updateAnswer(activeStep, nextSchedule);
            }}
          />
        );
      }
      case 'email':
        return (
          <div className="free-macro-email-step">
            <label>
              Email
              <input
                type="email"
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value);
                  setMessage('');
                }}
                placeholder="you@example.com"
                required
              />
            </label>
            <p>We will send a secure link so you can create your account and view your macro results in your dashboard.</p>
          </div>
        );
      default:
        return null;
    }
  };

  const stepMeta = {
    height: ['What is your height?', 'Use the slider to set your height.'],
    date_of_birth: ['What is your birthday?', 'We derive age from your date of birth.'],
    goal: ['What is your goal?', 'Lose, maintain, or gain weight.'],
    lifestyle: ['How active is your lifestyle?', 'This helps determine your TDEE category.'],
    meal_plan_type: ['Which macro plan type do you want?', 'Standard, carb cycling, or keto.'],
    workout_days: ['What days do you work out?', 'Select Sunday through Saturday.'],
    meal_schedule: ['How many meals do you want each day?', 'Set one meal amount for all days or customize each day.'],
    training_schedule: ['Before which meal do you train?', 'Choose the meal your workout happens before on each workout day.'],
    email: ['Where should we send your results link?', 'Create your account from the secure link to view your macro results.'],
  };

  return (
    <section className={`free-macro-calculator ${focused ? 'is-focused' : ''}`} aria-label="Free macro calculator">
      <div className="free-macro-header">
        <p>Free Macro Calculator</p>
        <h2>Get your free macros now.</h2>
        <span>{phase === 'initial' ? 'Start with gender and weight.' : 'Complete the questionnaire to receive your secure results link.'}</span>
      </div>

      {phase === 'initial' ? (
        <div className="free-macro-panel">
          <div className="client-q-progress">
            <span>Start with your basics</span>
            <div className="client-q-progress-bar"><div className="client-q-progress-fill" style={{ width: '20%' }} /></div>
          </div>
          {renderInitialStep()}
          {message ? <p className="client-q-error">{message}</p> : null}
          <div className="client-q-actions">
            <button type="button" className="client-q-btn" onClick={startQuestionnaire} disabled={!initialStepValid}>
              Next
            </button>
          </div>
        </div>
      ) : null}

      {phase === 'questionnaire' ? (
        <div className="free-macro-panel full">
          <div className="client-q-progress">
            <span>Question {stepIndex + 4} of {QUESTION_STEPS.length + 3}</span>
            <div className="client-q-progress-bar">
              <div className="client-q-progress-fill" style={{ width: `${((stepIndex + 4) / (QUESTION_STEPS.length + 3)) * 100}%` }} />
            </div>
          </div>
          <h3 className="free-macro-step-title">{stepMeta[activeStep]?.[0]}</h3>
          <p className="client-q-subtitle">{stepMeta[activeStep]?.[1]}</p>
          <div className="client-q-body">{renderQuestionStep()}</div>
          {message ? <p className="client-q-error">{message}</p> : null}
          <div className="client-q-actions">
            <button type="button" className="client-q-btn secondary" onClick={() => (stepIndex === 0 ? setPhase('initial') : setStepIndex((idx) => idx - 1))} disabled={submitState === 'submitting'}>
              Back
            </button>
            {stepIndex < QUESTION_STEPS.length - 1 ? (
              <button type="button" className="client-q-btn" onClick={() => setStepIndex((idx) => idx + 1)} disabled={!activeStepValid || submitState === 'submitting'}>
                Next
              </button>
            ) : (
              <button type="button" className="client-q-btn" onClick={submitCalculator} disabled={!activeStepValid || submitState === 'submitting'}>
                {submitState === 'submitting' ? 'Sending...' : 'Send My Results Link'}
              </button>
            )}
          </div>
        </div>
      ) : null}

      {phase === 'confirmation' ? (
        <div className="free-macro-confirmation">
          <h3>Check your email to create your account and view your macro results.</h3>
          <p>Your answers were saved to a secure registration link. The link expires in 7 days and can be used once.</p>
        </div>
      ) : null}
    </section>
  );
}

export default FreeMacroCalculator;
