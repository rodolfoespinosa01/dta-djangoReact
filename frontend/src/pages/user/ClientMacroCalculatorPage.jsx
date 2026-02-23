import React, { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { apiRequest } from '../../api/client';
import MealComboBuilderStep from '../../components/MealComboBuilderStep';
import './ClientDashboardPage.css';
import './ClientAuthPages.css';

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
  'food_preferences',
];

const WEEK_DAYS = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
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
    setAnswers((prev) => ({ ...prev, [wizardStep]: value }));
    setWizardMessage('');
  };

  const activeStepValid = useMemo(() => {
    const value = activeAnswer;
    switch (wizardStep) {
      case 'gender':
      case 'goal':
      case 'lifestyle':
      case 'meal_plan_type':
        return typeof value === 'string' && value.length > 0;
      case 'date_of_birth':
        return typeof value === 'string' && value.length > 0;
      case 'height':
        return Boolean(
          value && (
            (value.unit === 'cm' && Number(value.cm) > 0) ||
            (value.unit === 'imperial' && (Number(value.feet) > 0 || Number(value.inches) >= 0))
          )
        );
      case 'weight':
        return Boolean(value && Number(value.value) > 0 && ['lbs', 'kg'].includes(value.unit));
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
      case 'food_preferences':
        return Boolean(
          value
          && value.weekly_days
          && WEEK_DAYS.every((day) =>
            Array.isArray(value.weekly_days[day])
            && value.weekly_days[day].every((meal) => Number(meal?.combo_id) > 0)
          )
        );
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
    await saveDraft(wizardStep, answers[wizardStep], prevStep);
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
      setContext((prev) => (prev ? { ...prev, questionnaire: q } : prev));
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
                <span className="client-q-option-icon" aria-hidden="true">{v === 'male' ? '♂' : '♀'}</span>
                <span>{v === 'male' ? 'Male' : 'Female'}</span>
              </button>
            ))}
          </div>
        );
      case 'height': {
        const value = activeAnswer || { unit: 'imperial', feet: 5, inches: 0, cm: '' };
        return (
          <div className="client-q-stack">
            <div className="client-q-toggle">
              {[{ key: 'imperial', label: 'Feet / Inches' }, { key: 'cm', label: 'CM' }].map((opt) => (
                <button key={opt.key} type="button" className={value.unit === opt.key ? 'is-active' : ''} onClick={() => updateAnswer({ ...value, unit: opt.key })}>
                  {opt.label}
                </button>
              ))}
            </div>
            {value.unit === 'imperial' ? (
              <div className="client-q-inline-grid">
                <label>Feet<input type="number" min="0" value={value.feet ?? ''} onChange={(e) => updateAnswer({ ...value, feet: e.target.value })} /></label>
                <label>Inches<input type="number" min="0" max="11" value={value.inches ?? ''} onChange={(e) => updateAnswer({ ...value, inches: e.target.value })} /></label>
              </div>
            ) : (
              <label>Height (cm)<input type="number" min="0" value={value.cm ?? ''} onChange={(e) => updateAnswer({ ...value, cm: e.target.value })} /></label>
            )}
          </div>
        );
      }
      case 'weight': {
        const value = activeAnswer || { unit: 'lbs', value: '' };
        return (
          <div className="client-q-stack">
            <div className="client-q-toggle">
              {['lbs', 'kg'].map((unit) => (
                <button key={unit} type="button" className={value.unit === unit ? 'is-active' : ''} onClick={() => updateAnswer({ ...value, unit })}>
                  {unit.toUpperCase()}
                </button>
              ))}
            </div>
            <label>Weight<input type="number" min="0" step="0.1" value={value.value ?? ''} onChange={(e) => updateAnswer({ ...value, value: e.target.value })} /></label>
          </div>
        );
      }
      case 'date_of_birth':
        return <label className="client-q-single">Birthday<input type="date" value={activeAnswer ?? ''} onChange={(e) => updateAnswer(e.target.value)} /></label>;
      case 'goal':
        return (
          <div className="client-q-card-grid">
            {[['lose', 'Lose Weight'], ['maintain', 'Maintain'], ['gain', 'Gain Weight']].map(([value, label]) => (
              <button key={value} type="button" className={`client-q-option-card ${activeAnswer === value ? 'is-active' : ''}`} onClick={() => updateAnswer(value)}><span>{label}</span></button>
            ))}
          </div>
        );
      case 'lifestyle':
        return (
          <div className="client-q-card-grid">
            {[['low_active', 'Low Active'], ['middle_active', 'Middle Active'], ['high_active', 'Very Active']].map(([value, label]) => (
              <button key={value} type="button" className={`client-q-option-card ${activeAnswer === value ? 'is-active' : ''}`} onClick={() => updateAnswer(value)}><span>{label}</span></button>
            ))}
          </div>
        );
      case 'meal_plan_type':
        return (
          <div className="client-q-card-grid">
            {[['standard', 'Standard'], ['carb_cycling', 'Carb Cycling'], ['keto', 'Keto']].map(([value, label]) => (
              <button key={value} type="button" className={`client-q-option-card ${activeAnswer === value ? 'is-active' : ''}`} onClick={() => updateAnswer(value)}><span>{label}</span></button>
            ))}
          </div>
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
      case 'food_preferences': {
        return (
          <MealComboBuilderStep
            value={activeAnswer}
            onChange={updateAnswer}
            mealScheduleDays={answers.meal_schedule?.days || {}}
          />
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
    food_preferences: ['Build your meals for the week', 'Set a default day of meals, apply it to the week, and customize specific days if needed.'],
  };

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
        <section className="client-dashboard-card">
          <h2>Macro Calculator Ready</h2>
          <p className="client-dash-muted">
            Your questionnaire is complete. Next we will calculate and display your macros from this page.
          </p>
        </section>
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
