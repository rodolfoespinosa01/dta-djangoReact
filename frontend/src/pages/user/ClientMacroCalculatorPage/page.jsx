import React, { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { apiRequest } from '../../../api/client';
import BodyVisualizationSelector, { normalizeHeightCmValue } from '../../../components/questionnaire/BodyVisualizationSelector';
import WeightSelector, { lbsToKg, normalizeWeightLbsValue } from '../../../components/questionnaire/WeightSelector';
import DOBSelector from '../../../components/questionnaire/DOBSelector';
import GoalSelector from '../../../components/questionnaire/GoalSelector';
import LifestyleSelector, { normalizeLifestyleCode } from '../../../components/questionnaire/LifestyleSelector';
import MealPlanTypeSelector, { normalizeMealPlanTypeCode } from '../../../components/questionnaire/MealPlanTypeSelector';
import maleSignImage from '../../../assets/questionnaire/1/malesign.png';
import femaleSignImage from '../../../assets/questionnaire/1/femalesign.png';
import '../../../styles/shared/client-app-shell.css';
import '../../../styles/shared/auth-flow.css';
import './css.css';

const QUESTION_STEPS = [
  'gender',
  'height',
  'weight',
  'date_of_birth',
  'goal',
  'lifestyle',
  'meal_plan_type',
  'workout_days',
  'meal_schedule',
  'training_schedule',
];

const WEEK_DAYS = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
function prettyDay(day) {
  return day.charAt(0).toUpperCase() + day.slice(1);
}
function formatTrainingLabel(value) {
  if (!value) return 'No training';
  return value.replace('before_meal_', 'Before Meal ');
}
function summarizeAnswers(answers = {}) {
  const mealDays = answers?.meal_schedule?.days || {};
  const training = answers?.training_schedule || {};
  const workoutDays = Array.isArray(answers?.workout_days) ? answers.workout_days : [];
  return WEEK_DAYS.map((day) => ({
    day,
    isWorkout: workoutDays.includes(day),
    meals: Number(mealDays[day] || 0),
    trainingBeforeMeal: training?.[day] || null,
  }));
}

function ClientMacroCalculatorPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const [status, setStatus] = useState('loading');
  const [message, setMessage] = useState('');
  const [context, setContext] = useState(null);
  const [wizardStep, setWizardStep] = useState(QUESTION_STEPS[0]);
  const [answers, setAnswers] = useState({});
  const [savingDraft, setSavingDraft] = useState(false);
  const [submitState, setSubmitState] = useState('idle');
  const [wizardMessage, setWizardMessage] = useState('');

  useEffect(() => {
    let ignore = false;
    const load = async () => {
      if (!token) {
        setStatus('error');
        setMessage('Missing macro calculator link token.');
        return;
      }
      const res = await apiRequest(`/api/v1/users/client/macro-access/${token}/`);
      if (ignore) return;
      if (!res.ok) {
        setStatus('error');
        setMessage(res.data?.error?.message || 'Invalid macro calculator link.');
        return;
      }
      const payload = res.data?.macro_access || {};
      setContext(payload);
      const q = payload.questionnaire || {};
      setAnswers(q.answers || {});
      setWizardStep(q.current_step || QUESTION_STEPS[0]);
      setStatus('ready');
    };
    load().catch((err) => {
      console.error(err);
      if (!ignore) {
        setStatus('error');
        setMessage('Unable to open macro calculator link.');
      }
    });
    return () => { ignore = true; };
  }, [token]);

  const questionnaire = context?.questionnaire || {};
  const isComplete = questionnaire?.status === 'completed';
  const activeAnswer = answers[wizardStep];
  const stepIndex = Math.max(0, QUESTION_STEPS.indexOf(wizardStep));
  const canGoBack = stepIndex > 0;
  const isLastStep = stepIndex === QUESTION_STEPS.length - 1;

  const updateAnswer = (value) => {
    setAnswers((prev) => {
      const nextAnswers = { ...prev, [wizardStep]: value };
      if (wizardStep === 'workout_days') {
        const selectedDays = new Set(Array.isArray(value) ? value : []);
        const existingTraining = nextAnswers.training_schedule && typeof nextAnswers.training_schedule === 'object'
          ? nextAnswers.training_schedule
          : {};
        nextAnswers.training_schedule = Object.fromEntries(
          Object.entries(existingTraining).filter(([day]) => selectedDays.has(day))
        );
      }
      if (wizardStep === 'meal_schedule') {
        const mealDays = value?.days || {};
        const existingTraining = nextAnswers.training_schedule && typeof nextAnswers.training_schedule === 'object'
          ? nextAnswers.training_schedule
          : {};
        nextAnswers.training_schedule = Object.fromEntries(
          Object.entries(existingTraining).filter(([day, timing]) => {
            const mealCount = Number(mealDays[day] || 0);
            const match = /^before_meal_(\d+)$/.exec(String(timing || ''));
            return Boolean(match) && Number(match[1]) <= mealCount;
          })
        );
      }
      return nextAnswers;
    });
    setWizardMessage('');
  };

  const activeStepValid = useMemo(() => {
    const value = activeAnswer;
    switch (wizardStep) {
      case 'gender':
      case 'goal':
      case 'meal_plan_type':
        return normalizeMealPlanTypeCode(value).length > 0;
      case 'lifestyle':
        return normalizeLifestyleCode(value).length > 0;
      case 'date_of_birth':
        return typeof value === 'string' && value.length > 0;
      case 'height':
        return Number.isFinite(normalizeHeightCmValue(value, Number.NaN));
      case 'weight':
        return Number.isFinite(normalizeWeightLbsValue(value, Number.NaN));
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
  }, [wizardStep, activeAnswer, answers.workout_days, answers.meal_schedule]);

  const saveDraft = async (stepToSave, answerValue, nextStep) => {
    setSavingDraft(true);
    setWizardMessage('');
    try {
      const res = await apiRequest(`/api/v1/users/client/macro-access/${token}/questionnaire/`, {
        method: 'PATCH',
        body: { step_key: stepToSave, answer: answerValue, next_step: nextStep },
      });
      if (!res.ok) {
        setWizardMessage(res.data?.error?.message || 'Unable to save your progress.');
        return false;
      }
      const q = res.data?.questionnaire || {};
      setContext((prev) => (prev ? { ...prev, questionnaire: q } : prev));
      setAnswers(q.answers || answers);
      if (nextStep) setWizardStep(nextStep);
      return true;
    } catch (err) {
      console.error(err);
      setWizardMessage('Network error while saving progress.');
      return false;
    } finally {
      setSavingDraft(false);
    }
  };

  const handleNext = async () => {
    if (!activeStepValid) return;
    const nextStep = isLastStep ? wizardStep : QUESTION_STEPS[stepIndex + 1];
    await saveDraft(wizardStep, answers[wizardStep], nextStep);
  };

  const handleBack = async () => {
    if (!canGoBack) return;
    const prevStep = QUESTION_STEPS[stepIndex - 1];
    if (activeStepValid) {
      await saveDraft(wizardStep, answers[wizardStep], prevStep);
      return;
    }
    setWizardStep(prevStep);
    setWizardMessage('');
  };

  const handleSubmitQuestionnaire = async () => {
    setSubmitState('submitting');
    setWizardMessage('');
    try {
      if (activeStepValid) {
        const okSave = await saveDraft(wizardStep, answers[wizardStep], wizardStep);
        if (!okSave) {
          setSubmitState('idle');
          return;
        }
      }
      const res = await apiRequest(`/api/v1/users/client/macro-access/${token}/questionnaire/submit/`, {
        method: 'POST',
      });
      if (!res.ok) {
        setWizardMessage(res.data?.error?.message || 'Unable to submit questionnaire.');
        const missing = res.data?.error?.details?.missing_steps;
        if (Array.isArray(missing) && missing.length) setWizardStep(missing[0]);
        setSubmitState('idle');
        return;
      }
      const q = res.data?.questionnaire || {};
      setContext((prev) => (prev ? { ...prev, questionnaire: q, results: res.data?.results || prev.results } : prev));
      setWizardMessage('Questionnaire submitted successfully.');
      setSubmitState('success');
    } catch (err) {
      console.error(err);
      setWizardMessage('Network error while submitting questionnaire.');
      setSubmitState('idle');
    }
  };

  const renderQuestionStep = () => {
    switch (wizardStep) {
      case 'gender':
        return (
          <div className="client-q-card-grid">
            {['male', 'female'].map((v) => (
              <button key={v} type="button" className={`client-q-option-card ${activeAnswer === v ? 'is-active' : ''}`} onClick={() => updateAnswer(v)}>
                <span className="client-q-option-icon" aria-hidden="true">
                  <img
                    className="client-q-option-icon-image"
                    src={v === 'male' ? maleSignImage : femaleSignImage}
                    alt=""
                  />
                </span>
                <span>{v === 'male' ? 'Male' : 'Female'}</span>
              </button>
            ))}
          </div>
        );
      case 'height': {
        const selectedGender = answers?.gender === 'female' ? 'female' : 'male';
        return (
          <BodyVisualizationSelector
            value={activeAnswer}
            gender={selectedGender}
            onChange={(heightCm) => updateAnswer(heightCm)}
          />
        );
      }
      case 'weight': {
        const weightUnit = activeAnswer?.unit === 'kg' ? 'kg' : 'lbs';
        const currentWeightLbs = normalizeWeightLbsValue(activeAnswer);
        return (
          <WeightSelector
            value={currentWeightLbs}
            unit={weightUnit}
            allowUnitToggle
            onUnitChange={(nextUnit) => {
              const normalizedLbs = normalizeWeightLbsValue(activeAnswer);
              updateAnswer({
                unit: nextUnit,
                value: nextUnit === 'kg' ? lbsToKg(normalizedLbs) : Math.round(normalizedLbs),
              });
            }}
            onChange={(nextLbs) => {
              updateAnswer({
                unit: weightUnit,
                value: weightUnit === 'kg' ? lbsToKg(nextLbs) : Math.round(nextLbs),
              });
            }}
          />
        );
      }
      case 'date_of_birth':
        return <DOBSelector value={activeAnswer ?? ''} gender={answers?.gender === 'female' ? 'female' : 'male'} onChange={(dobIso) => updateAnswer(dobIso)} />;
      case 'goal':
        return (
          <GoalSelector
            value={activeAnswer ?? ''}
            gender={answers?.gender === 'female' ? 'female' : 'male'}
            onChange={(goalKey) => updateAnswer(goalKey)}
          />
        );
      case 'lifestyle':
        return (
          <LifestyleSelector
            value={activeAnswer ?? ''}
            gender={answers?.gender === 'female' ? 'female' : 'male'}
            onChange={(lifestyleCode) => updateAnswer(lifestyleCode)}
          />
        );
      case 'meal_plan_type':
        return (
          <MealPlanTypeSelector
            value={activeAnswer ?? ''}
            onChange={(mealPlanTypeCode) => updateAnswer(mealPlanTypeCode)}
          />
        );
      case 'workout_days': {
        const selected = Array.isArray(activeAnswer) ? activeAnswer : [];
        return (
          <div className="client-q-stack">
            <p className="client-q-help">Select every day you plan to work out.</p>
            <div className="client-q-day-grid">
              {WEEK_DAYS.map((day) => {
                const on = selected.includes(day);
                return (
                  <button key={day} type="button" className={`client-q-day ${on ? 'is-active' : ''}`} onClick={() => updateAnswer(on ? selected.filter((d) => d !== day) : [...selected, day])}>
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

        const setSameMeals = (count) => updateAnswer({
          mode: 'same',
          default_meals: count,
          days: WEEK_DAYS.reduce((acc, day) => ({ ...acc, [day]: count }), {}),
        });
        const setCustomDayMeals = (day, count) => updateAnswer({
          ...value,
          mode: 'custom',
          days: { ...value.days, [day]: count },
        });

        return (
          <div className="client-q-stack">
            <p className="client-q-help">Choose one meal amount for all days, or customize each day of the week.</p>
            <div className="client-q-toggle">
              <button type="button" className={value.mode === 'same' ? 'is-active' : ''} onClick={() => updateAnswer({ ...value, mode: 'same' })}>
                Same for all days
              </button>
              <button type="button" className={value.mode === 'custom' ? 'is-active' : ''} onClick={() => updateAnswer({ ...value, mode: 'custom' })}>
                Customize by day
              </button>
            </div>
            <div className="client-q-card-grid">
              {[3, 4, 5, 6].map((count) => (
                <button
                  key={`same-${count}`}
                  type="button"
                  className={`client-q-option-card ${value.mode === 'same' && Number(value.default_meals) === count ? 'is-active' : ''}`}
                  onClick={() => setSameMeals(count)}
                >
                  <span>{count} Meals</span>
                </button>
              ))}
            </div>
            {value.mode === 'custom' && (
              <div className="client-q-stack">
                {WEEK_DAYS.map((day) => (
                  <div key={day} className="client-q-stack">
                    <strong>{day.charAt(0).toUpperCase() + day.slice(1)}</strong>
                    <div className="client-q-card-grid">
                      {[3, 4, 5, 6].map((count) => (
                        <button
                          key={`${day}-${count}`}
                          type="button"
                          className={`client-q-option-card ${Number(value.days[day]) === count ? 'is-active' : ''}`}
                          onClick={() => setCustomDayMeals(day, count)}
                        >
                          <span>{count}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      }
      case 'training_schedule': {
        const selectedDays = Array.isArray(answers.workout_days) ? answers.workout_days : [];
        const mealDays = answers.meal_schedule?.days || {};
        const value = activeAnswer && typeof activeAnswer === 'object' ? activeAnswer : {};
        if (selectedDays.length === 0) {
          return (
            <div className="client-q-stack">
              <p className="client-q-help">No workout days selected. We will treat all days as off days.</p>
              <button type="button" className="client-q-btn secondary" onClick={() => updateAnswer({})}>Confirm No Training Schedule</button>
            </div>
          );
        }
        const quickDefaultMeal = Number(value._default_before_meal || 1);
        const applicableDaysCount = selectedDays.filter((day) => quickDefaultMeal <= Number(mealDays[day] || 0)).length;
        const applyQuickDefault = (mealNum) => {
          const next = { ...value, _default_before_meal: mealNum };
          selectedDays.forEach((day) => {
            const count = Number(mealDays[day] || 0);
            if (mealNum <= count) {
              next[day] = `before_meal_${mealNum}`;
            }
          });
          updateAnswer(next);
        };
        return (
          <div className="client-q-stack">
            <p className="client-q-help">Choose which meal your workout happens before on each workout day.</p>
            <div className="client-q-stack">
              <strong>Quick set default for workout days</strong>
              <div className="client-q-card-grid">
                {[1, 2, 3, 4, 5, 6].map((mealNum) => (
                  <button
                    key={`quick-default-${mealNum}`}
                    type="button"
                    className={`client-q-option-card ${quickDefaultMeal === mealNum ? 'is-active' : ''}`}
                    onClick={() => applyQuickDefault(mealNum)}
                  >
                    <span>Before Meal {mealNum}</span>
                  </button>
                ))}
              </div>
              <p className="client-q-help">
                Applies to {applicableDaysCount} workout day{applicableDaysCount === 1 ? '' : 's'} automatically. You can still customize each day below.
              </p>
            </div>
            {selectedDays.map((day) => (
              <label key={day} className="client-q-single">
                {day.charAt(0).toUpperCase() + day.slice(1)}
                <div className="client-q-card-grid">
                  {Array.from({ length: Number(mealDays[day] || 3) }, (_, idx) => idx + 1).map((mealNum) => (
                    <button
                      key={`${day}-before-${mealNum}`}
                      type="button"
                      className={`client-q-option-card ${value[day] === `before_meal_${mealNum}` ? 'is-active' : ''}`}
                      onClick={() => updateAnswer({ ...value, [day]: `before_meal_${mealNum}` })}
                    >
                      <span>Before Meal {mealNum}</span>
                    </button>
                  ))}
                </div>
              </label>
            ))}
          </div>
        );
      }
      default:
        return <p>Question not configured.</p>;
    }
  };

  const stepMeta = {
    gender: ['Please state your gender', 'Choose male or female.'],
    height: ['What is your height?', 'You can enter feet/inches or centimeters.'],
    weight: ['What is your weight?', 'Choose pounds or kilograms.'],
    date_of_birth: ['What is your birthday?', 'We derive age from your date of birth.'],
    goal: ['What is your goal?', 'Lose, maintain, or gain weight.'],
    lifestyle: ['How active is your lifestyle?', 'This helps determine your TDEE category.'],
    meal_plan_type: ['Which meal plan type do you want?', 'Standard, carb cycling, or keto.'],
    workout_days: ['What days do you work out?', 'Select Sunday through Saturday.'],
    meal_schedule: ['How many meals do you want each day?', 'Set one meal amount for all days or customize each day of the week.'],
    training_schedule: ['Before which meal do you train?', 'Choose the meal your workout happens before on each workout day.'],
  };
  const weeklySchedule = useMemo(() => summarizeAnswers(questionnaire?.answers || {}), [questionnaire?.answers]);
  const results = context?.results;

  if (status === 'loading') {
    return <div className="client-auth-page"><div className="client-auth-card"><p>Opening macro calculator…</p></div></div>;
  }

  if (status === 'error') {
    return (
      <div className="client-auth-page">
        <div className="client-auth-card">
          <h1>Macro Calculator Link</h1>
          <p className="client-auth-error">{message}</p>
          <Link className="client-auth-link" to="/user_homepage">Back to DTA</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="client-dashboard-page">
      <header className="client-dashboard-header">
        <div>
          <h1>Macro Calculator</h1>
          <p className="client-dash-muted">Email: {context?.email}</p>
        </div>
        <div className="client-dash-chips">
          <span>free</span>
          <span>macro access</span>
        </div>
      </header>

      <section className="client-dashboard-card">
        <h2>Questionnaire Required</h2>
        <p className="client-dash-muted">
          Complete your questionnaire so we can calculate your macros and prepare the right meal-plan logic for later food customization.
        </p>
      </section>

      {isComplete && (
        <>
          <section className="client-dashboard-card">
            <h2>Macro Calculator Ready</h2>
            <div className="client-q-stack">
              <p className="client-dash-muted">
                Your questionnaire is complete. Below is your weekly schedule summary. Macro totals/per-meal macro calculations are now shown from your current settings.
              </p>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 560 }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Day</th>
                      <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Type</th>
                      <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Meals</th>
                      <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Training Timing</th>
                    </tr>
                  </thead>
                  <tbody>
                    {weeklySchedule.map((row) => (
                      <tr key={`macro-sched-${row.day}`}>
                        <td style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>{prettyDay(row.day)}</td>
                        <td style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>{row.isWorkout ? 'Workout Day' : 'Off Day'}</td>
                        <td style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>{row.meals || '-'}</td>
                        <td style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>
                          {row.trainingBeforeMeal ? row.trainingBeforeMeal.replaceAll('_', ' ') : 'No training'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          {results && (
            <>
              <section className="client-dashboard-card">
                <h2>Core Calculations</h2>
                <div className="client-dash-chips">
                  <span>BMR: {results?.core_calculations?.bmr ?? '-'} kcal</span>
                  <span>Goal Adj: {results?.core_calculations?.goal_calorie_adjustment_percent ?? '-'}%</span>
                  <span>TDEE Category: {results?.core_calculations?.tdee_category ?? '-'}</span>
                  <span>Avg Multiplier: {results?.core_calculations?.weekly_average_multiplier ?? '-'}</span>
                </div>
                <ul>
                  <li>Workout Day Avg TDEE: {results?.summary?.workout_day_avg_tdee ?? '-'} kcal</li>
                  <li>Off Day Avg TDEE: {results?.summary?.off_day_avg_tdee ?? '-'} kcal</li>
                  <li>Workout Day Avg Calories: {results?.summary?.workout_day_avg_calories ?? '-'} kcal</li>
                  <li>Off Day Avg Calories: {results?.summary?.off_day_avg_calories ?? '-'} kcal</li>
                </ul>
              </section>

              <section className="client-dashboard-card">
                <div className="client-dashboard-header" style={{ marginBottom: '0.5rem' }}>
                  <h2 style={{ margin: 0 }}>Daily Macro Results</h2>
                </div>
                <p className="client-dash-muted" style={{ marginTop: 0 }}>
                  PDF exports are available on paid monthly plans.
                </p>
                <div className="client-q-stack">
                  {(results.weekly_days || []).map((day) => (
                    <div key={`macro-results-${day.day}`} style={{ border: '1px solid rgba(20,40,74,0.1)', borderRadius: 12, padding: '0.8rem' }}>
                      <div className="client-dashboard-header" style={{ marginBottom: '0.5rem' }}>
                        <div>
                          <strong>{prettyDay(day.day)}</strong>
                          <p className="client-dash-muted" style={{ margin: '0.2rem 0 0' }}>
                            {day.is_workout_day ? 'Workout Day' : 'Off Day'} • {day.meals_per_day} meals • {formatTrainingLabel(day.training_before_meal)}
                          </p>
                        </div>
                        <div className="client-dash-chips">
                          <span>Mult: {day.tdee_multiplier}</span>
                          <span>TDEE: {day.tdee_calories} kcal</span>
                          <span>Target: {day.calories_target} kcal</span>
                        </div>
                      </div>

                      <div className="client-dash-chips" style={{ marginBottom: '0.5rem' }}>
                        <span>Protein: {day.daily_macros?.protein_g} g</span>
                        <span>Carbs: {day.daily_macros?.carbs_g} g</span>
                        <span>Fats: {day.daily_macros?.fats_g} g</span>
                        {day.carb_cycling_mode ? <span>{day.carb_cycling_mode === 'high_carbs' ? 'High Carb Day' : 'Low Carb Day'}</span> : null}
                      </div>

                      <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 520 }}>
                          <thead>
                            <tr>
                              <th style={{ textAlign: 'left', padding: '0.4rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Meal</th>
                              <th style={{ textAlign: 'left', padding: '0.4rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Protein</th>
                              <th style={{ textAlign: 'left', padding: '0.4rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Carbs</th>
                              <th style={{ textAlign: 'left', padding: '0.4rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Fats</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(day.meal_macro_splits || []).map((meal) => (
                              <tr key={`${day.day}-${meal.meal_number}`}>
                                <td style={{ padding: '0.4rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>Meal {meal.meal_number}</td>
                                <td style={{ padding: '0.4rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>{meal.grams?.protein_g} g ({meal.percentages?.protein}%)</td>
                                <td style={{ padding: '0.4rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>{meal.grams?.carbs_g} g ({meal.percentages?.carbs}%)</td>
                                <td style={{ padding: '0.4rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>{meal.grams?.fats_g} g ({meal.percentages?.fats}%)</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </>
          )}
        </>
      )}

      {!isComplete && (
        <div className="client-q-backdrop">
          <div className="client-q-modal" role="dialog" aria-modal="true" aria-labelledby="macro-q-title">
            <div className="client-q-progress">
              <span>Question {stepIndex + 1} of {QUESTION_STEPS.length}</span>
              <div className="client-q-progress-bar">
                <div className="client-q-progress-fill" style={{ width: `${((stepIndex + 1) / QUESTION_STEPS.length) * 100}%` }} />
              </div>
            </div>
            <h2 id="macro-q-title">{stepMeta[wizardStep]?.[0]}</h2>
            <p className="client-q-subtitle">{stepMeta[wizardStep]?.[1]}</p>
            <div className="client-q-body">{renderQuestionStep()}</div>
            {wizardMessage && <p className={wizardMessage.toLowerCase().includes('error') ? 'client-q-error' : 'client-q-message'}>{wizardMessage}</p>}
            <div className="client-q-actions">
              <button type="button" className="client-q-btn secondary" onClick={handleBack} disabled={!canGoBack || savingDraft || submitState === 'submitting'}>
                Back
              </button>
              {!isLastStep && (
                <button type="button" className="client-q-btn" onClick={handleNext} disabled={!activeStepValid || savingDraft || submitState === 'submitting'}>
                  {savingDraft ? 'Saving…' : 'Next'}
                </button>
              )}
              {isLastStep && (
                <button type="button" className="client-q-btn" onClick={handleSubmitQuestionnaire} disabled={!activeStepValid || savingDraft || submitState === 'submitting'}>
                  {submitState === 'submitting' ? 'Submitting…' : 'Submit Questionnaire'}
                </button>
              )}
              <Link className="client-q-btn danger" to="/welcome">Leave</Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ClientMacroCalculatorPage;
