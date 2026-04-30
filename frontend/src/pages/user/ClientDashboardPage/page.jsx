import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../../../api/client';
import { useAuth } from '../../../context/AuthContext';
import { openPrintPdfWindow, renderPrintTable, escapeHtml } from '../../../utils/printPdf';
import BodyVisualizationSelector, { normalizeHeightCmValue } from '../../../components/questionnaire/BodyVisualizationSelector';
import WeightSelector, { lbsToKg, normalizeWeightLbsValue } from '../../../components/questionnaire/WeightSelector';
import DOBSelector from '../../../components/questionnaire/DOBSelector';
import GoalSelector from '../../../components/questionnaire/GoalSelector';
import LifestyleSelector, { normalizeLifestyleCode } from '../../../components/questionnaire/LifestyleSelector';
import MealPlanTypeSelector, { normalizeMealPlanTypeCode } from '../../../components/questionnaire/MealPlanTypeSelector';
import MealFrequencySelector from '../../../components/questionnaire/MealFrequencySelector';
import TrainingMealTimingSelector from '../../../components/questionnaire/TrainingMealTimingSelector';
import WorkoutScheduleSelector from '../../../components/questionnaire/WorkoutScheduleSelector';
import ProteinShakeSelector, { normalizeProteinShakeValue } from '../../../components/questionnaire/ProteinShakeSelector';
import {
  BACKEND_DAY_TO_WORKOUT_CODE,
  WORKOUT_DAYS,
  WORKOUT_CODE_TO_BACKEND_DAY,
  inferScheduleMode,
  normalizeTrainingDays,
} from '../../../components/questionnaire/workoutSchedule.constants';
import maleSignImage from '../../../assets/questionnaire/1/malesign.png';
import femaleSignImage from '../../../assets/questionnaire/1/femalesign.png';
import settingsIcon from '../../../assets/misc/settingsicon.png';
import formEditIcon from '../../../assets/misc/formedit.png';
import trackingIcon from '../../../assets/misc/tracking.png';
import coachingMessagesIcon from '../../../assets/misc/coachmessageicon.png';
import analyticsIcon from '../../../assets/misc/analytics';
import foodIcon from '../../../assets/foods_png/Salmon.png';
import '../../../styles/shared/client-app-shell.css';
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
  'protein_shake',
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
  'protein_shake',
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

function hasCompletedFoodPreferences(questionnaire) {
  const foodPreferences = questionnaire?.answers?.food_preferences;
  return Boolean(
    questionnaire?.status === 'completed'
    && foodPreferences
    && typeof foodPreferences === 'object'
    && Object.keys(foodPreferences).length > 0
  );
}

function shouldCollectFoodPreferences(client, questionnaire, onboarding) {
  const requiresFoodPreferences = onboarding?.requires_food_preferences ?? Boolean(client?.includes_food_plan);
  const questionnaireCompleted = onboarding?.questionnaire_completed ?? questionnaire?.status === 'completed';
  const foodPreferencesCompleted = onboarding?.food_preferences_completed ?? hasCompletedFoodPreferences(questionnaire);
  return Boolean(requiresFoodPreferences && questionnaireCompleted && !foodPreferencesCompleted);
}

function toWorkoutCodeDays(value) {
  const list = Array.isArray(value) ? value : [];
  const mapped = list.map((backendDay) => BACKEND_DAY_TO_WORKOUT_CODE[backendDay]).filter(Boolean);
  return normalizeTrainingDays(mapped);
}

function toBackendWorkoutDays(value) {
  const list = normalizeTrainingDays(value);
  return list.map((code) => WORKOUT_CODE_TO_BACKEND_DAY[code]).filter(Boolean);
}

function toMealFrequencyUiValue(value) {
  const existingDays = value?.days || {};
  const fallbackDefault = [3, 4, 5, 6].includes(Number(value?.default_meals)) ? Number(value.default_meals) : 4;

  const days = WORKOUT_DAYS.reduce((acc, day) => {
    const parsed = Number(existingDays[day.backendKey]);
    acc[day.code] = [3, 4, 5, 6].includes(parsed) ? parsed : fallbackDefault;
    return acc;
  }, {});

  const firstDayCode = WORKOUT_DAYS[0]?.code || 'mon';
  const inferredDefaultMeals = Number(days[firstDayCode] || fallbackDefault);
  const inferredSame = WORKOUT_DAYS.every((day) => Number(days[day.code]) === inferredDefaultMeals);
  const mode = value?.mode === 'custom' ? 'custom' : (inferredSame ? 'same' : 'custom');

  return {
    mode,
    defaultMeals: inferredDefaultMeals,
    days,
  };
}

function toBackendMealScheduleValue(value) {
  const mode = value?.mode === 'custom' ? 'custom' : 'same';
  const defaultMeals = [3, 4, 5, 6].includes(Number(value?.defaultMeals)) ? Number(value.defaultMeals) : 4;
  const days = WORKOUT_DAYS.reduce((acc, day) => {
    const parsed = Number(value?.days?.[day.code]);
    acc[day.backendKey] = [3, 4, 5, 6].includes(parsed) ? parsed : defaultMeals;
    return acc;
  }, {});

  return {
    mode,
    default_meals: defaultMeals,
    days,
  };
}

function toMealScheduleByCode(value) {
  const days = value?.days || {};
  return WORKOUT_DAYS.reduce((acc, day) => {
    const parsed = Number(days[day.backendKey]);
    acc[day.code] = [3, 4, 5, 6].includes(parsed) ? parsed : 3;
    return acc;
  }, {});
}

function toTrainingMealTimingUiValue(value, trainingDays = [], mealScheduleByDay = {}) {
  const trainingSet = new Set(trainingDays);

  const days = WORKOUT_DAYS.reduce((acc, day) => {
    if (!trainingSet.has(day.code)) {
      acc[day.code] = null;
      return acc;
    }

    const mealCount = Number(mealScheduleByDay[day.code] || 3);
    const raw = String(value?.[day.backendKey] || '');
    const parsed = Number(raw.replace('before_meal_', ''));
    const safe = Number.isFinite(parsed) ? parsed : 1;
    acc[day.code] = Math.max(1, Math.min(mealCount, safe));
    return acc;
  }, {});

  const inferredSame = trainingDays.length > 0
    ? trainingDays.every((dayCode) => days[dayCode] === days[trainingDays[0]])
    : true;
  const sharedMax = trainingDays.length
    ? Math.min(...trainingDays.map((dayCode) => Number(mealScheduleByDay?.[dayCode] || 1)))
    : 1;
  const fallbackSame = trainingDays.length ? Number(days[trainingDays[0]]) : 1;
  const rawSame = Number(value?._default_before_meal);
  const safeSame = Number.isFinite(rawSame) ? rawSame : fallbackSame;
  const sameBeforeMeal = Math.max(1, Math.min(sharedMax, safeSame));
  const explicitMode = String(value?._mode || '').trim().toLowerCase();
  const inferredMode = inferredSame ? 'same' : 'custom';
  const mode = explicitMode === 'custom' || explicitMode === 'same' ? explicitMode : inferredMode;

  return {
    mode,
    sameBeforeMeal,
    days,
  };
}

function toBackendTrainingMealTimingValue(value, trainingDays = [], mealScheduleByDay = {}) {
  const mode = String(value?.mode || '').trim().toLowerCase() === 'custom' ? 'custom' : 'same';
  const payload = {
    _mode: mode,
    _default_before_meal: Number(value?.sameBeforeMeal) || 1,
  };

  trainingDays.forEach((dayCode) => {
    const backendDay = WORKOUT_CODE_TO_BACKEND_DAY[dayCode];
    if (!backendDay) return;
    const mealCount = Number(mealScheduleByDay?.[dayCode] || 1);
    const parsed = Number(value?.days?.[dayCode]);
    const safe = Number.isFinite(parsed) ? parsed : 1;
    const clamped = Math.max(1, Math.min(mealCount, safe));
    payload[backendDay] = `before_meal_${clamped}`;
  });

  return payload;
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
  const results = dashboard?.results;
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
        if (shouldCollectFoodPreferences(data.client, data.questionnaire, data.onboarding)) {
          navigate('/client_food_preferences', { replace: true });
          return;
        }
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
        return value === 'male' || value === 'female';
      case 'goal':
        return value === 'lose' || value === 'maintain' || value === 'gain';
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
        return Array.isArray(value) && value.length >= 1;
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
      case 'protein_shake': {
        const normalized = normalizeProteinShakeValue(value, {
          mealSchedule: answers.meal_schedule,
          trainingSchedule: answers.training_schedule,
        });
        if (!normalized.enabled) return true;
        return ['pre_workout', 'post_workout', 'other'].includes(normalized.placement_mode);
      }
      default:
        return value !== undefined && value !== null && value !== '';
    }
  }, [wizardStep, activeAnswer, answers.workout_days, answers.meal_schedule, answers.training_schedule]);

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
      if (['meal_schedule', 'training_schedule'].includes(wizardStep) && nextAnswers.protein_shake) {
        nextAnswers.protein_shake = normalizeProteinShakeValue(nextAnswers.protein_shake, {
          mealSchedule: nextAnswers.meal_schedule,
          trainingSchedule: nextAnswers.training_schedule,
        });
      }
      return nextAnswers;
    });
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
    if (activeStepValid) {
      await saveDraft(wizardStep, answers[wizardStep], prevStep);
      return;
    }
    setWizardStep(prevStep);
    setWizardMessage('');
  };

  const handleStepAnswerAndAdvance = async (value) => {
    updateAnswer(value);
    if (!activeQuestionSteps.includes(wizardStep)) return;
    const nextStep = isLastStep ? wizardStep : activeQuestionSteps[stepIndex + 1];
    await saveDraft(wizardStep, value, nextStep);
  };

  const mealFrequencyRecommendationContext = useMemo(() => {
    const workoutSet = new Set(Array.isArray(answers?.workout_days) ? answers.workout_days : []);
    const weeklyDays = Array.isArray(results?.weekly_days) ? results.weekly_days : [];
    const weeklyMap = weeklyDays.reduce((acc, row) => {
      acc[row.day] = row;
      return acc;
    }, {});

    const workoutAvgCalories = Number(results?.summary?.workout_day_avg_calories);
    const offAvgCalories = Number(results?.summary?.off_day_avg_calories);

    const dayCaloriesByCode = WORKOUT_DAYS.reduce((acc, day) => {
      const direct = Number(weeklyMap?.[day.backendKey]?.calories_target);
      const fallback = workoutSet.has(day.backendKey) ? workoutAvgCalories : offAvgCalories;
      const selected = Number.isFinite(direct) ? direct : (Number.isFinite(fallback) ? fallback : null);
      acc[day.code] = selected;
      return acc;
    }, {});

    const numeric = Object.values(dayCaloriesByCode).filter((value) => Number.isFinite(Number(value))).map(Number);
    const average = numeric.length ? (numeric.reduce((acc, value) => acc + value, 0) / numeric.length) : null;

    return {
      dailyCalories: average,
      dayCaloriesByCode,
    };
  }, [answers?.workout_days, results?.weekly_days, results?.summary?.workout_day_avg_calories, results?.summary?.off_day_avg_calories]);

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
      setDashboard((prev) => (prev ? { ...prev, questionnaire: q, onboarding: res.data?.onboarding || prev.onboarding, results: res.data?.results || prev.results } : prev));
      setWizardMessage(isEditingQuestionnaire ? 'Questionnaire updates saved successfully.' : 'Questionnaire submitted successfully.');
      if (isEditingQuestionnaire) {
        setIsEditingQuestionnaire(false);
      }
      if (shouldCollectFoodPreferences(dashboard?.client, q, res.data?.onboarding)) {
        navigate('/client_food_preferences', { replace: true });
        return;
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
                disabled={savingDraft}
                onClick={() => handleStepAnswerAndAdvance(v)}
              >
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
        const trainingDays = toWorkoutCodeDays(activeAnswer);
        const scheduleMode = inferScheduleMode(trainingDays);
        return (
          <WorkoutScheduleSelector
            value={{ scheduleMode, trainingDays }}
            onChange={(nextValue) => updateAnswer(toBackendWorkoutDays(nextValue?.trainingDays))}
          />
        );
      }
      case 'meal_schedule': {
        const value = toMealFrequencyUiValue(activeAnswer);
        return (
          <MealFrequencySelector
            value={value}
            dailyCalories={mealFrequencyRecommendationContext.dailyCalories}
            dayCaloriesByCode={mealFrequencyRecommendationContext.dayCaloriesByCode}
            onChange={(nextValue) => updateAnswer(toBackendMealScheduleValue(nextValue))}
          />
        );
      }
      case 'training_schedule': {
        const trainingDays = toWorkoutCodeDays(answers.workout_days);
        const mealScheduleByDay = toMealScheduleByCode(answers.meal_schedule);
        const value = toTrainingMealTimingUiValue(activeAnswer, trainingDays, mealScheduleByDay);

        return (
          <TrainingMealTimingSelector
            gender={answers?.gender === 'female' ? 'female' : 'male'}
            trainingDays={trainingDays}
            mealScheduleByDay={mealScheduleByDay}
            value={value}
            onChange={(nextValue) => updateAnswer(toBackendTrainingMealTimingValue(nextValue, trainingDays, mealScheduleByDay))}
          />
        );
      }
      case 'protein_shake':
        return (
          <ProteinShakeSelector
            value={activeAnswer}
            mealSchedule={answers.meal_schedule}
            trainingSchedule={answers.training_schedule}
            onChange={(nextValue) => updateAnswer(nextValue)}
          />
        );
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
    workout_days: ['What days do you work out?', 'Workout and off days drive calorie totals and macro splitting.'],
    meal_schedule: ['How many meals do you want per day?', 'If you choose a protein shake later, it will count as one of these meals.'],
    training_schedule: ['Before which meal do you train?', 'Your workout timing helps us customize calorie and macro placement around training for each day.'],
    protein_shake: ['Would you like one of your meals to be a protein shake?', 'Choose whether one meal slot should be reserved for a shake.'],
  };

  const weeklySchedule = useMemo(() => summarizeAnswers(questionnaire?.answers || {}), [questionnaire?.answers]);
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

      {/* Messaging Portal Section */}
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
        </div>
      </section>

      <section className="client-dashboard-card">
        <h2>Client Workflow</h2>
        <p className="client-dash-muted">
          Start here. Open only the section you need for this session.
        </p>
        <div className="client-dashboard-actions">
          {dashboard?.client?.includes_food_plan && (
            <button type="button" className="client-q-btn secondary client-dash-action-btn" onClick={() => navigate('/client_food_preferences')} disabled={isBlocked}>
              <span className="client-dash-action-icon-stack" aria-hidden="true">
                <img className="client-dash-action-icon client-dash-action-icon-food" src={foodIcon} alt="" />
                <img className="client-dash-action-icon client-dash-action-icon-overlay" src={settingsIcon} alt="" />
              </span>
              <span className="client-dash-action-copy">
                <span className="client-dash-action-title">Food Preferences</span>
                <span className="client-dash-action-desc">Customize foods included in your meal plan.</span>
              </span>
            </button>
          )}
          <button type="button" className="client-q-btn secondary client-dash-action-btn" onClick={() => navigate('/client_settings')} disabled={isBlocked}>
            <img className="client-dash-action-icon" src={settingsIcon} alt="" aria-hidden="true" />
            <span className="client-dash-action-copy">
              <span className="client-dash-action-title">Account Settings</span>
              <span className="client-dash-action-desc">Manage your account theme and preferences.</span>
            </span>
          </button>
          <button type="button" className="client-q-btn secondary client-dash-action-btn" onClick={handleOpenQuestionnaireEdit} disabled={isBlocked}>
            <img className="client-dash-action-icon" src={formEditIcon} alt="" aria-hidden="true" />
            <span className="client-dash-action-copy">
              <span className="client-dash-action-title">Edit Questionnaire</span>
              <span className="client-dash-action-desc">Update your goals, body data, and routine answers.</span>
            </span>
          </button>
          <button type="button" className="client-q-btn secondary client-dash-action-btn" onClick={() => navigate('/client_tracking')}>
            <img className="client-dash-action-icon" src={trackingIcon} alt="" aria-hidden="true" />
            <span className="client-dash-action-copy">
              <span className="client-dash-action-title">Tracking</span>
              <span className="client-dash-action-desc">Track weight, adherence, and check-ins.</span>
            </span>
          </button>
          {dashboard?.client?.includes_coaching && (
            <button
              type="button"
              className="client-q-btn secondary client-dash-action-btn"
              onClick={() => navigate('/client_coaching')}
            >
              <img className="client-dash-action-icon" src={coachingMessagesIcon} alt="" aria-hidden="true" />
              <span className="client-dash-action-copy">
                <span className="client-dash-action-title">Coaching Messages</span>
                <span className="client-dash-action-desc">Message your coach directly from this area.</span>
              </span>
            </button>
          )}
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
          <button
            type="button"
            className="client-q-btn secondary client-dash-action-btn"
            onClick={() => setShowDetailedAnalytics((prev) => !prev)}
            disabled={isBlocked}
          >
            <img className="client-dash-action-icon" src={analyticsIcon} alt="" aria-hidden="true" />
            <span className="client-dash-action-copy">
              <span className="client-dash-action-title">Show Analytics</span>
              <span className="client-dash-action-desc">
                {showDetailedAnalytics
                  ? 'Detailed analytics are currently visible.'
                  : 'Display macro breakdowns, calorie insights, and performance data.'}
              </span>
            </span>
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
