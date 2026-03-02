import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { openPrintPdfWindow, renderPrintTable, escapeHtml } from '../../utils/printPdf';
import './ClientDashboardPage.css';

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
const EDITABLE_QUESTION_STEPS = [
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
function normalizeSubdomainLabel(slug) {
  return slug ? `${slug}.dtameals.com` : 'DTA Direct';
}
function portalLabel(client) {
  if (!client) return 'Client Portal';
  return client.sale_channel === 'admin_white_label' ? 'Coach Portal' : 'DTA Direct Portal';
}
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

function getTodayWeekdayKey() {
  const dayIndex = new Date().getDay();
  return WEEK_DAYS[dayIndex] || 'sunday';
}

function renderPrintSection(title, innerHtml) {
  return `<section class="section"><h2>${escapeHtml(title)}</h2>${innerHtml}</section>`;
}

function renderChipList(items = []) {
  const list = items.filter(Boolean);
  if (!list.length) return '';
  return `<div class="chips">${list.map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join('')}</div>`;
}

function ClientDashboardPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState('');
  const [wizardStep, setWizardStep] = useState('gender');
  const [answers, setAnswers] = useState({});
  const [savingDraft, setSavingDraft] = useState(false);
  const [submitState, setSubmitState] = useState('idle');
  const [wizardMessage, setWizardMessage] = useState('');
  const [isEditingQuestionnaire, setIsEditingQuestionnaire] = useState(false);
  const [planActionBusy] = useState(false);
  const [planActionMessage, setPlanActionMessage] = useState('');
  const [showDetailedAnalytics, setShowDetailedAnalytics] = useState(false);
  const [activeDashboardPanel, setActiveDashboardPanel] = useState('daily_macros');
  const [selectedMacroDay, setSelectedMacroDay] = useState(getTodayWeekdayKey());
  const [selectedOverviewDay, setSelectedOverviewDay] = useState(getTodayWeekdayKey());

  const questionnaire = dashboard?.questionnaire;
  const isQuestionnaireComplete = questionnaire?.status === 'completed';
  // Food preferences are considered complete if questionnaire is complete and food_preferences exists and is not empty
  const foodPrefs = questionnaire?.answers?.food_preferences;
  const isFoodPreferencesComplete = isQuestionnaireComplete && foodPrefs && typeof foodPrefs === 'object' && Object.keys(foodPrefs).length > 0;
  const isBlocked = !isQuestionnaireComplete;
  const showQuestionnaireModal = isBlocked || isEditingQuestionnaire;
  const activeQuestionSteps = showQuestionnaireModal && isQuestionnaireComplete
    ? EDITABLE_QUESTION_STEPS
    : QUESTION_STEPS;

  useEffect(() => {
    let ignore = false;
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const res = await apiRequest('/api/v1/users/client/app/dashboard/', { auth: true });
        if (ignore) return;
        if (res.status === 401) {
          navigate('/client_login', { replace: true });
          return;
        }
        if (!res.ok) {
          setError(res.data?.error?.message || 'Unable to load client dashboard.');
          return;
        }
        const data = res.data || {};
        setDashboard(data);
        const q = data.questionnaire || {};
        setAnswers(q.answers || {});
        setWizardStep(q.current_step || QUESTION_STEPS[0]);
      } catch (err) {
        console.error(err);
        if (!ignore) setError('Network error while loading client dashboard.');
      } finally {
        if (!ignore) setLoading(false);
      }
    };
    load();
    return () => { ignore = true; };
  }, [navigate]);

  useEffect(() => {
    if (activeQuestionSteps.includes(wizardStep)) return;
    setWizardStep(activeQuestionSteps[0] || QUESTION_STEPS[0]);
  }, [activeQuestionSteps, wizardStep]);

  const activeAnswer = answers[wizardStep];
  const stepIndex = Math.max(0, activeQuestionSteps.indexOf(wizardStep));
  const canGoBack = stepIndex > 0;
  const isLastStep = stepIndex === activeQuestionSteps.length - 1;

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
      default:
        return value !== undefined && value !== null && value !== '';
    }
  }, [wizardStep, activeAnswer, answers.workout_days, answers.meal_schedule]);

  const updateAnswer = (value) => {
    setAnswers((prev) => ({ ...prev, [wizardStep]: value }));
    setWizardMessage('');
  };

  const saveDraft = async (stepToSave, answerValue, nextStep) => {
    setSavingDraft(true);
    setWizardMessage('');
    try {
      const res = await apiRequest('/api/v1/users/client/app/questionnaire/', {
        method: 'PATCH',
        auth: true,
        body: { step_key: stepToSave, answer: answerValue, next_step: nextStep },
      });
      if (!res.ok) {
        setWizardMessage(res.data?.error?.message || 'Unable to save your progress.');
        return false;
      }
      const q = res.data?.questionnaire || {};
      setDashboard((prev) => (
        prev
          ? {
              ...prev,
              questionnaire: q,
              ...(res.data?.results ? { results: res.data.results } : {}),
            }
          : prev
      ));
      setAnswers(q.answers || answers);
      if (nextStep) setWizardStep(nextStep);
      if (res.data?.updates?.food_preferences_reset) {
        setWizardMessage('Schedule/plan changes cleared previous food preferences. Rebuild meal combos before generation.');
      }
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
    const nextStep = isLastStep ? wizardStep : activeQuestionSteps[stepIndex + 1];
    await saveDraft(wizardStep, answers[wizardStep], nextStep);
  };

  const handleBack = async () => {
    if (!canGoBack) return;
    const prevStep = activeQuestionSteps[stepIndex - 1];
    await saveDraft(wizardStep, answers[wizardStep], prevStep);
  };

  const handleSubmitQuestionnaire = async () => {
    setSubmitState('submitting');
    setWizardMessage('');
    try {
      // Save current step first if valid.
      if (activeStepValid) {
        const okSave = await saveDraft(wizardStep, answers[wizardStep], wizardStep);
        if (!okSave) {
          setSubmitState('idle');
          return;
        }
      }
      const res = await apiRequest('/api/v1/users/client/app/questionnaire/submit/', {
        method: 'POST',
        auth: true,
      });
      if (!res.ok) {
        setWizardMessage(res.data?.error?.message || 'Unable to submit questionnaire.');
        const missing = res.data?.error?.details?.missing_steps;
        if (Array.isArray(missing) && missing.length) {
          setWizardStep(missing[0]);
        }
        setSubmitState('idle');
        return;
      }
      const q = res.data?.questionnaire || {};
      setDashboard((prev) => (prev ? { ...prev, questionnaire: q, results: res.data?.results || prev.results } : prev));
      setWizardMessage(isEditingQuestionnaire ? 'Questionnaire updates saved successfully.' : 'Questionnaire submitted successfully.');
      if (isEditingQuestionnaire) {
        setIsEditingQuestionnaire(false);
      }
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
              <button
                key={v}
                type="button"
                className={`client-q-option-card ${activeAnswer === v ? 'is-active' : ''}`}
                onClick={() => updateAnswer(v)}
              >
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
              {[
                { key: 'imperial', label: 'Feet / Inches' },
                { key: 'cm', label: 'CM' },
              ].map((opt) => (
                <button
                  key={opt.key}
                  type="button"
                  className={value.unit === opt.key ? 'is-active' : ''}
                  onClick={() => updateAnswer({ ...value, unit: opt.key })}
                >
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
        return (
          <label className="client-q-single">
            Birthday
            <input type="date" value={activeAnswer ?? ''} onChange={(e) => updateAnswer(e.target.value)} />
          </label>
        );
      case 'goal':
        return (
          <div className="client-q-card-grid">
            {[
              ['lose', 'Lose Weight'],
              ['maintain', 'Maintain'],
              ['gain', 'Gain Weight'],
            ].map(([value, label]) => (
              <button key={value} type="button" className={`client-q-option-card ${activeAnswer === value ? 'is-active' : ''}`} onClick={() => updateAnswer(value)}>
                <span>{label}</span>
              </button>
            ))}
          </div>
        );
      case 'lifestyle':
        return (
          <div className="client-q-card-grid">
            {[
              ['low_active', 'Low Active'],
              ['middle_active', 'Middle Active'],
              ['high_active', 'Very Active'],
            ].map(([value, label]) => (
              <button key={value} type="button" className={`client-q-option-card ${activeAnswer === value ? 'is-active' : ''}`} onClick={() => updateAnswer(value)}>
                <span>{label}</span>
              </button>
            ))}
          </div>
        );
      case 'meal_plan_type':
        return (
          <div className="client-q-card-grid">
            {[
              ['standard', 'Standard'],
              ['carb_cycling', 'Carb Cycling'],
              ['keto', 'Keto'],
            ].map(([value, label]) => (
              <button key={value} type="button" className={`client-q-option-card ${activeAnswer === value ? 'is-active' : ''}`} onClick={() => updateAnswer(value)}>
                <span>{label}</span>
              </button>
            ))}
          </div>
        );
      case 'workout_days': {
        const selected = Array.isArray(activeAnswer) ? activeAnswer : [];
        return (
          <div className="client-q-stack">
            <p className="client-q-help">Select every day you plan to work out. This drives workout vs off-day TDEE logic.</p>
            <div className="client-q-day-grid">
              {WEEK_DAYS.map((day) => {
                const on = selected.includes(day);
                return (
                  <button
                    key={day}
                    type="button"
                    className={`client-q-day ${on ? 'is-active' : ''}`}
                    onClick={() => {
                      const next = on ? selected.filter((d) => d !== day) : [...selected, day];
                      updateAnswer(next);
                    }}
                  >
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
              <p className="client-q-help">No workout days selected. We will treat all days as off days for now.</p>
              <button type="button" className="client-q-btn secondary" onClick={() => updateAnswer({})}>
                Confirm No Training Schedule
              </button>
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
            <div className="client-q-stack">
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
  const results = dashboard?.results;
  const todayDayKey = getTodayWeekdayKey();
  const resultDays = useMemo(() => (Array.isArray(results?.weekly_days) ? results.weekly_days : []), [results?.weekly_days]);
  const resultDayMap = useMemo(
    () => resultDays.reduce((acc, row) => ({ ...acc, [row.day]: row }), {}),
    [resultDays]
  );
  const selectedMacroDayResult = resultDayMap[selectedMacroDay] || resultDayMap[todayDayKey] || resultDays[0] || null;
  const selectedOverviewRow = weeklySchedule.find((row) => row.day === selectedOverviewDay)
    || weeklySchedule.find((row) => row.day === todayDayKey)
    || weeklySchedule[0]
    || null;
  const selectedOverviewDayResult = selectedOverviewRow ? (resultDayMap[selectedOverviewRow.day] || null) : null;

  useEffect(() => {
    if (!resultDays.length) return;
    if (!resultDayMap[selectedMacroDay]) {
      setSelectedMacroDay(resultDayMap[todayDayKey] ? todayDayKey : resultDays[0].day);
    }
  }, [resultDays, resultDayMap, selectedMacroDay, todayDayKey]);

  useEffect(() => {
    if (!weeklySchedule.length) return;
    const exists = weeklySchedule.some((row) => row.day === selectedOverviewDay);
    if (!exists) {
      setSelectedOverviewDay(weeklySchedule.some((row) => row.day === todayDayKey) ? todayDayKey : weeklySchedule[0].day);
    }
  }, [weeklySchedule, selectedOverviewDay, todayDayKey]);

  const exportSelectedMacroDayPdf = () => {
    if (!dashboard?.client?.includes_food_plan) {
      setPlanActionMessage('PDF exports are available only for paid plans with food meal-plan access.');
      return;
    }
    const day = selectedMacroDayResult;
    if (!day) return;
    const opened = openPrintPdfWindow({
      title: `${prettyDay(day.day)} Daily Macros`,
      subtitle: 'Use your browser print dialog and choose "Save as PDF".',
      sections: [
        renderPrintSection(
          'Daily Macro Results',
          [
            renderChipList([
              day.is_workout_day ? 'Workout Day' : 'Off Day',
              `Meals: ${day.meals_per_day ?? '-'}`,
              `Training: ${formatTrainingLabel(day.training_before_meal)}`,
              `TDEE: ${day.tdee_calories ?? '-'} kcal`,
              `Target: ${day.calories_target ?? '-'} kcal`,
              `Protein: ${day.daily_macros?.protein_g ?? '-'} g`,
              `Carbs: ${day.daily_macros?.carbs_g ?? '-'} g`,
              `Fats: ${day.daily_macros?.fats_g ?? '-'} g`,
            ]),
            renderPrintTable(
              ['Meal', 'Protein', 'Carbs', 'Fats'],
              (day.meal_macro_splits || []).map((meal) => ([
                `Meal ${meal.meal_number ?? '-'}`,
                `${meal.grams?.protein_g ?? '-'} g (${meal.percentages?.protein ?? '-'}%)`,
                `${meal.grams?.carbs_g ?? '-'} g (${meal.percentages?.carbs ?? '-'}%)`,
                `${meal.grams?.fats_g ?? '-'} g (${meal.percentages?.fats ?? '-'}%)`,
              ]))
            ),
          ].join('')
        ),
      ],
    });
    if (!opened) {
      setPlanActionMessage('Unable to open PDF print window. Allow pop-ups and try again.');
    }
  };

  const handleStartTrialFromDashboard = async () => {
    navigate('/client_settings');
  };

  const handleOpenQuestionnaireEdit = () => {
    setWizardMessage('');
    setSubmitState('idle');
    setIsEditingQuestionnaire(true);
    setWizardStep(EDITABLE_QUESTION_STEPS[0]);
  };

  if (loading) return <div className="client-dashboard-page"><p>Loading dashboard…</p></div>;
  if (error) return <div className="client-dashboard-page"><p className="client-dash-error">{error}</p></div>;

  return (
    <div className="client-dashboard-page">
      <header className="client-dashboard-header">
        <div>
          <h1>Client Dashboard</h1>
          <div className="client-dash-chips" style={{ marginTop: '0.35rem' }}>
            <span>{portalLabel(dashboard?.client)}</span>
            <span>Source: {normalizeSubdomainLabel(dashboard?.client?.associated_admin_slug)}</span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'flex-end' }}>
          <div className="client-dash-chips">
            <span>{dashboard?.client?.offer_code}</span>
            <span>{dashboard?.client?.billing_cycle || 'free'}</span>
            {dashboard?.client?.trial_days ? <span>{dashboard.client.trial_days}-day teaser</span> : null}
          </div>
          <button type="button" className="client-q-btn danger" onClick={() => logout('/client_login')} disabled={loading}>
            Log Out
          </button>
        </div>
      </header>

      <section className="client-dashboard-card">
        <h2>Your Plan Access</h2>
        <ul>
          <li>Macro calculator: free for everyone</li>
          <li>Food-based calculations: {dashboard?.client?.includes_food_plan ? 'Enabled' : 'Not included in this plan'}</li>
          <li>Coaching messaging: {dashboard?.client?.includes_coaching ? 'Enabled' : 'Not included'}</li>
        </ul>
        {planActionMessage ? <p className={planActionMessage.toLowerCase().includes('unable') ? 'client-q-error' : 'client-q-message'}>{planActionMessage}</p> : null}
        <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
          {!dashboard?.client?.includes_food_plan ? (
            <button type="button" className="client-q-btn" onClick={handleStartTrialFromDashboard} disabled={planActionBusy || isBlocked}>
              Choose Plan + Start 5-Day Free Trial
            </button>
          ) : (
            <>
              <button type="button" className="client-q-btn" onClick={() => navigate('/client_food_preferences')} disabled={isBlocked}>
                Open Food Preferences / Meal Combos
              </button>
              {isFoodPreferencesComplete && (
                <button type="button" className="client-q-btn secondary" onClick={() => navigate('/client_meal_generation')} disabled={isBlocked}>
                  Run Meal Generation
                </button>
              )}
              <button type="button" className="client-q-btn secondary" onClick={() => navigate('/client_exports')} disabled={isBlocked}>
                Export Center
              </button>
            </>
          )}
          <button type="button" className="client-q-btn secondary" onClick={() => navigate('/client_settings')} disabled={isBlocked}>
            Manage Plan & Subscription
          </button>
        </div>
      </section>

      <section className="client-dashboard-card">
        <h2>Client Workflow</h2>
        <p className="client-dash-muted">
          Start here. Open only the section you need for this session.
        </p>
        <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
          {isFoodPreferencesComplete && (
            <>
              <button type="button" className="client-q-btn" onClick={() => navigate('/client_meal_generation')} disabled={isBlocked}>
                Meal Plan Generation
              </button>
              <button type="button" className="client-q-btn secondary" onClick={() => navigate('/client_meal_generation')} disabled={isBlocked}>
                Recipe Generation
              </button>
            </>
          )}
          <button type="button" className="client-q-btn secondary" onClick={handleOpenQuestionnaireEdit} disabled={isBlocked}>
            Edit Questionnaire
          </button>
          <button type="button" className="client-q-btn secondary" onClick={() => navigate('/client_tracking')}>
            Tracking
          </button>
          <button type="button" className="client-q-btn secondary" onClick={() => navigate('/client_coaching')}>
            Coaching
          </button>
          <button
            type="button"
            className="client-q-btn secondary"
            onClick={() => setShowDetailedAnalytics((prev) => !prev)}
            disabled={isBlocked}
          >
            {showDetailedAnalytics ? 'Hide Detailed Analytics' : 'Show Detailed Analytics'}
          </button>
        </div>
      </section>

      {showDetailedAnalytics && (
      <section className="client-dashboard-card">
        <h2>{isQuestionnaireComplete ? 'Dashboard Analytics' : 'Dashboard Preview'}</h2>
        {!isQuestionnaireComplete ? (
          <p className="client-dash-muted">
            Complete the questionnaire to unlock Daily Macros, Core Calculations, and Weekly Analytics toggles.
          </p>
        ) : (
          <div className="client-q-stack">
            <div className="client-dash-chips">
              <span>{(questionnaire?.answers?.gender || 'n/a').toString()}</span>
              <span>{(questionnaire?.answers?.goal || 'n/a').toString()}</span>
              <span>{(questionnaire?.answers?.meal_plan_type || 'n/a').toString()}</span>
              <span>{(questionnaire?.answers?.lifestyle || 'n/a').toString()}</span>
              <span>Today: {prettyDay(todayDayKey)}</span>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <button type="button" className={`client-q-btn ${activeDashboardPanel === 'daily_macros' ? '' : 'secondary'}`} onClick={() => setActiveDashboardPanel('daily_macros')}>
                Daily Macros
              </button>
              <button type="button" className={`client-q-btn ${activeDashboardPanel === 'core_calcs' ? '' : 'secondary'}`} onClick={() => setActiveDashboardPanel('core_calcs')}>
                Core Calculations
              </button>
              <button type="button" className={`client-q-btn ${activeDashboardPanel === 'weekly_overview' ? '' : 'secondary'}`} onClick={() => setActiveDashboardPanel('weekly_overview')}>
                Weekly Analytics Overview
              </button>
              {dashboard?.client?.includes_food_plan ? (
                <button type="button" className="client-q-btn secondary" onClick={() => navigate('/client_exports')}>
                  Open Export Center
                </button>
              ) : null}
              <button type="button" className="client-q-btn secondary" onClick={handleOpenQuestionnaireEdit}>
                Edit Questionnaire Inputs
              </button>
            </div>

            {activeDashboardPanel === 'weekly_overview' && (
              <div style={{ border: '1px solid rgba(20,40,74,0.1)', borderRadius: 12, padding: '0.9rem', background: '#fff' }}>
                <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap', alignItems: 'end', marginBottom: '0.75rem' }}>
                  <label>
                    Day
                    <select value={selectedOverviewRow?.day || selectedOverviewDay} onChange={(e) => setSelectedOverviewDay(e.target.value)}>
                      {weeklySchedule.map((row) => (
                        <option key={`overview-day-${row.day}`} value={row.day}>{prettyDay(row.day)}</option>
                      ))}
                    </select>
                  </label>
                  <button type="button" className="client-q-btn secondary" onClick={() => setSelectedOverviewDay(todayDayKey)}>
                    Today
                  </button>
                </div>
                {selectedOverviewRow ? (
                  <>
                    <div className="client-dashboard-header" style={{ marginBottom: '0.5rem' }}>
                      <div>
                        <strong>{prettyDay(selectedOverviewRow.day)}</strong>
                        <p className="client-dash-muted" style={{ margin: '0.2rem 0 0', fontWeight: selectedOverviewRow.day === todayDayKey ? 700 : 400 }}>
                          {selectedOverviewRow.isWorkout ? 'Workout Day' : 'Off Day'} • {selectedOverviewRow.meals || '-'} meals • {selectedOverviewRow.trainingBeforeMeal ? selectedOverviewRow.trainingBeforeMeal.replaceAll('_', ' ') : 'No training'}
                        </p>
                      </div>
                    </div>
                    <div style={{ overflowX: 'auto' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 420 }}>
                        <thead>
                          <tr>
                            <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Metric</th>
                            <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Value</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr>
                            <td style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>Day Type</td>
                            <td style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)', fontWeight: selectedOverviewRow.day === todayDayKey ? 700 : 400 }}>
                              {selectedOverviewRow.isWorkout ? 'Workout Day' : 'Off Day'}
                            </td>
                          </tr>
                          <tr>
                            <td style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>Meals</td>
                            <td style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>{selectedOverviewRow.meals || '-'}</td>
                          </tr>
                          <tr>
                            <td style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>Training Timing</td>
                            <td style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>
                              {selectedOverviewRow.trainingBeforeMeal ? selectedOverviewRow.trainingBeforeMeal.replaceAll('_', ' ') : 'No training'}
                            </td>
                          </tr>
                          {selectedOverviewDayResult ? (
                            <tr>
                              <td style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>Total Calories Target</td>
                              <td style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)', fontWeight: selectedOverviewRow.day === todayDayKey ? 700 : 500 }}>
                                {selectedOverviewDayResult.calories_target ?? '-'} kcal
                              </td>
                            </tr>
                          ) : null}
                        </tbody>
                      </table>
                    </div>
                  </>
                ) : (
                  <p className="client-dash-muted">No weekly overview data yet.</p>
                )}
              </div>
            )}

            {activeDashboardPanel === 'core_calcs' && results && (
              <div style={{ border: '1px solid rgba(20,40,74,0.1)', borderRadius: 12, padding: '0.9rem', background: '#fff' }}>
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
              </div>
            )}

            {activeDashboardPanel === 'daily_macros' && (
              <div style={{ border: '1px solid rgba(20,40,74,0.1)', borderRadius: 12, padding: '0.9rem', background: '#fff' }}>
                <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap', alignItems: 'end', marginBottom: '0.75rem' }}>
                  <label>
                    Day
                    <select value={selectedMacroDayResult?.day || selectedMacroDay} onChange={(e) => setSelectedMacroDay(e.target.value)}>
                      {resultDays.map((day) => (
                        <option key={`macro-day-${day.day}`} value={day.day}>{prettyDay(day.day)}</option>
                      ))}
                    </select>
                  </label>
                  <button type="button" className="client-q-btn secondary" onClick={() => setSelectedMacroDay(todayDayKey)}>
                    Today
                  </button>
                  {dashboard?.client?.includes_food_plan ? (
                    <button type="button" className="client-q-btn secondary" onClick={exportSelectedMacroDayPdf} disabled={!selectedMacroDayResult}>
                      Save Macros PDF
                    </button>
                  ) : null}
                </div>
                {!dashboard?.client?.includes_food_plan ? (
                  <p className="client-dash-muted" style={{ marginTop: '-0.1rem', marginBottom: '0.5rem' }}>
                    PDF exports are available for paid monthly plans.
                  </p>
                ) : null}

                {!selectedMacroDayResult ? (
                  <p className="client-dash-muted">No daily macro results available yet.</p>
                ) : (
                  <div>
                    <div className="client-dashboard-header" style={{ marginBottom: '0.5rem' }}>
                      <div>
                        <strong>{prettyDay(selectedMacroDayResult.day)}</strong>
                        <p className="client-dash-muted" style={{ margin: '0.2rem 0 0', fontWeight: selectedMacroDayResult.day === todayDayKey ? 700 : 400 }}>
                          {selectedMacroDayResult.is_workout_day ? 'Workout Day' : 'Off Day'} • {selectedMacroDayResult.meals_per_day} meals • {formatTrainingLabel(selectedMacroDayResult.training_before_meal)}
                        </p>
                      </div>
                      <div className="client-dash-chips">
                        <span>Mult: {selectedMacroDayResult.tdee_multiplier}</span>
                        <span style={{ fontWeight: selectedMacroDayResult.day === todayDayKey ? 700 : 500 }}>
                          TDEE: {selectedMacroDayResult.tdee_calories} kcal
                        </span>
                        <span style={{ fontWeight: selectedMacroDayResult.day === todayDayKey ? 700 : 500 }}>
                          Target: {selectedMacroDayResult.calories_target} kcal
                        </span>
                      </div>
                    </div>

                    <div className="client-dash-chips" style={{ marginBottom: '0.5rem' }}>
                      <span>Protein: {selectedMacroDayResult.daily_macros?.protein_g} g</span>
                      <span>Carbs: {selectedMacroDayResult.daily_macros?.carbs_g} g</span>
                      <span>Fats: {selectedMacroDayResult.daily_macros?.fats_g} g</span>
                      {selectedMacroDayResult.carb_cycling_mode ? <span>{selectedMacroDayResult.carb_cycling_mode === 'high_carbs' ? 'High Carb Day' : 'Low Carb Day'}</span> : null}
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
                          {(selectedMacroDayResult.meal_macro_splits || []).map((meal) => (
                            <tr key={`${selectedMacroDayResult.day}-${meal.meal_number}`}>
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
                )}
              </div>
            )}
          </div>
        )}
      </section>
      )}

      {isQuestionnaireComplete && dashboard?.client?.includes_food_plan && (
        <section className="client-dashboard-card">
          <h2>Food Preferences & Meal Combos</h2>
          <p className="client-dash-muted">
            This is now a separate form after questionnaire completion. Next step: build your default meal templates and customize Sunday-Saturday meals.
          </p>
          <button type="button" className="client-q-btn secondary" disabled>
            Food Preference Form (Use button above)
          </button>
        </section>
      )}

      {showQuestionnaireModal && (
        <div className="client-q-backdrop">
          <div className="client-q-modal" role="dialog" aria-modal="true" aria-labelledby="client-q-title">
            <div className="client-q-progress">
              <span>Question {stepIndex + 1} of {activeQuestionSteps.length}</span>
              <div className="client-q-progress-bar">
                <div className="client-q-progress-fill" style={{ width: `${((stepIndex + 1) / activeQuestionSteps.length) * 100}%` }} />
              </div>
            </div>
            <h2 id="client-q-title">{stepMeta[wizardStep]?.[0]}</h2>
            <p className="client-q-subtitle">
              {isBlocked
                ? stepMeta[wizardStep]?.[1]
                : 'Update your weekly inputs. Height and gender stay fixed after onboarding.'}
            </p>

            <div className="client-q-body">
              {renderQuestionStep()}
            </div>

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
                  {submitState === 'submitting' ? 'Submitting…' : isBlocked ? 'Submit Questionnaire' : 'Save Updates'}
                </button>
              )}
              {isBlocked ? (
                <button type="button" className="client-q-btn danger" onClick={() => logout('/client_login')} disabled={savingDraft || submitState === 'submitting'}>
                  Log Out
                </button>
              ) : (
                <button
                  type="button"
                  className="client-q-btn danger"
                  onClick={() => setIsEditingQuestionnaire(false)}
                  disabled={savingDraft || submitState === 'submitting'}
                >
                  Close
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ClientDashboardPage;
