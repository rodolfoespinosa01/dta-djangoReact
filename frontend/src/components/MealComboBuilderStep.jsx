import React, { useEffect, useMemo, useRef, useState } from 'react';
import { apiRequest } from '../api/client';

const SLOT_KEYS = ['protein_1', 'protein_2', 'carbs_1', 'carbs_2', 'fats_1', 'fats_2'];
const SLOT_LABELS = {
  protein_1: 'Protein 1',
  protein_2: 'Protein 2',
  carbs_1: 'Carbs 1',
  carbs_2: 'Carbs 2',
  fats_1: 'Fats 1',
  fats_2: 'Fats 2',
};
const WEEK_DAYS = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
const MAX_SAVED_TEMPLATES = 7;
const SLOT_MIN_GRAMS_FOR_SECOND_SOURCE = {
  protein_2: 50,
  carbs_2: 45,
  fats_2: 20,
};
const TWO_CARB_ALLOWED_G = 60;
const TRAINING_ADJACENT_TWO_CARB_MIN_G = 45;

function createEmptyMeal() {
  return {
    protein_1: '-',
    protein_2: '-',
    carbs_1: '-',
    carbs_2: '-',
    fats_1: '-',
    fats_2: '-',
    combo_id: null,
    combo_match: 'unknown',
  };
}

function ensureMealArray(meals, count) {
  const next = Array.isArray(meals) ? [...meals] : [];
  while (next.length < count) next.push(createEmptyMeal());
  return next.slice(0, count).map((meal) => ({ ...createEmptyMeal(), ...(meal || {}) }));
}

function cloneMealsForCount(sourceMeals, count) {
  const normalized = ensureMealArray(sourceMeals, Math.max(count, sourceMeals?.length || 0));
  return ensureMealArray(normalized, count);
}

function normalizeSlotValue(value) {
  const normalized = String(value || '').trim();
  return normalized || '-';
}

function rowSignature(row) {
  return SLOT_KEYS.map((slot) => normalizeSlotValue(row?.[slot])).join('|');
}

function normalizeSavedTemplates(savedTemplates) {
  if (!Array.isArray(savedTemplates)) return [];
  return savedTemplates
    .slice(0, MAX_SAVED_TEMPLATES)
    .map((tpl, idx) => {
      const mealCount = [3, 4, 5, 6].includes(Number(tpl?.meal_count)) ? Number(tpl.meal_count) : 3;
      return {
        id: tpl?.id || `template_${idx + 1}`,
        name: (tpl?.name || `Template ${idx + 1}`).toString().slice(0, 40),
        meal_count: mealCount,
        meals: ensureMealArray(tpl?.meals, mealCount),
      };
    });
}

function prettyDay(day) {
  return (day || '').slice(0, 1).toUpperCase() + (day || '').slice(1);
}

function getMealContextLabel(dayResult, mealNumber) {
  if (!dayResult) return null;
  if (!dayResult.is_workout_day) return 'Off Day Meal';
  const trainingKey = dayResult.training_before_meal || '';
  const match = /^before_meal_(\d+)$/.exec(trainingKey);
  if (!match) return 'Workout Day Meal';
  const trainMeal = Number(match[1]);
  if (mealNumber === trainMeal) return 'Post-Workout Meal';
  if (mealNumber === trainMeal - 1) return 'Pre-Workout Meal';
  return 'Workout Day Meal';
}

function MealComboBuilderStep({ value, onChange, mealScheduleDays = {}, weeklyMacroResults = [] }) {
  const [slotOptions, setSlotOptions] = useState(null);
  const [optionsError, setOptionsError] = useState('');
  const [lookupBusy, setLookupBusy] = useState({});
  const [starterTemplates, setStarterTemplates] = useState([]);
  const [starterLoading, setStarterLoading] = useState(false);
  const [copyTargetDay, setCopyTargetDay] = useState('monday');
  const [templatePanelMode, setTemplatePanelMode] = useState('starter');

  useEffect(() => {
    let ignore = false;
    apiRequest('/api/v1/users/client/public/meal-combo-options/')
      .then((res) => {
        if (ignore) return;
        if (!res.ok) {
          setOptionsError(res.data?.error?.message || 'Unable to load meal combo options.');
          return;
        }
        setSlotOptions(res.data?.slot_options || {});
      })
      .catch((err) => {
        console.error(err);
        if (!ignore) setOptionsError('Unable to load meal combo options.');
      });
    return () => { ignore = true; };
  }, []);

  const normalized = useMemo(() => {
    const weekCounts = WEEK_DAYS.reduce((acc, day) => {
      acc[day] = [3, 4, 5, 6].includes(Number(mealScheduleDays?.[day])) ? Number(mealScheduleDays[day]) : 3;
      return acc;
    }, {});
    const defaultCount = Number(value?.default_day_meal_count || weekCounts.sunday || 3);
    const defaultMeals = ensureMealArray(value?.default_day_meals, defaultCount);
    const weekly = WEEK_DAYS.reduce((acc, day) => {
      acc[day] = ensureMealArray(value?.weekly_days?.[day], weekCounts[day]);
      return acc;
    }, {});
    return {
      active_day: value?.active_day || 'sunday',
      default_day_meal_count: [3, 4, 5, 6].includes(defaultCount) ? defaultCount : 3,
      default_day_meals: defaultMeals,
      weekly_days: weekly,
      week_counts: weekCounts,
      saved_templates: normalizeSavedTemplates(value?.saved_templates),
      next_template_number: Math.max(1, Number(value?.next_template_number || 1)),
    };
  }, [value, mealScheduleDays]);

  const normalizedRef = useRef(normalized);

  useEffect(() => {
    normalizedRef.current = normalized;
  }, [normalized]);

  const emit = (patchOrFactory) => {
    const base = normalizedRef.current;
    const patch = typeof patchOrFactory === 'function' ? patchOrFactory(base) : patchOrFactory;
    if (!patch) return;
    onChange({ ...base, ...patch });
  };

  const updateDefaultMealCount = (count) => {
    const meals = ensureMealArray(normalized.default_day_meals, count);
    emit({
      default_day_meal_count: count,
      default_day_meals: meals,
    });
    triggerAutoLookupForMeals({ scope: 'default', meals });
  };

  const lookupComboForRow = async ({ row, scope, day, mealIndex }) => {
    const key = `${scope}:${day || 'default'}:${mealIndex}`;
    const requestedSignature = rowSignature(row);

    setLookupBusy((prev) => ({ ...prev, [key]: true }));
    emit((base) => {
      if (scope === 'default') {
        const meals = [...base.default_day_meals];
        const current = meals[mealIndex] || createEmptyMeal();
        if (rowSignature(current) !== requestedSignature) return null;
        meals[mealIndex] = { ...current, combo_match: 'checking' };
        return { default_day_meals: meals };
      }
      if (scope === 'weekly' && day) {
        const dayMeals = [...(base.weekly_days?.[day] || [])];
        const current = dayMeals[mealIndex] || createEmptyMeal();
        if (rowSignature(current) !== requestedSignature) return null;
        dayMeals[mealIndex] = { ...current, combo_match: 'checking' };
        return { weekly_days: { ...base.weekly_days, [day]: dayMeals } };
      }
      return null;
    });

    try {
      const payload = SLOT_KEYS.reduce((acc, slot) => ({ ...acc, [slot]: normalizeSlotValue(row[slot]) }), {});
      const res = await apiRequest('/api/v1/users/client/public/meal-combo-lookup/', {
        method: 'POST',
        body: payload,
      });
      const found = Boolean(res.ok && res.data?.combo_match?.found);
      const comboId = found ? res.data.combo_match.combo_id : null;

      emit((base) => {
        if (scope === 'default') {
          const meals = [...base.default_day_meals];
          const current = meals[mealIndex] || createEmptyMeal();
          if (rowSignature(current) !== requestedSignature) return null;
          meals[mealIndex] = {
            ...current,
            combo_id: comboId,
            combo_match: found ? 'matched' : 'not_found',
          };
          return { default_day_meals: meals };
        }
        if (scope === 'weekly' && day) {
          const dayMeals = [...(base.weekly_days?.[day] || [])];
          const current = dayMeals[mealIndex] || createEmptyMeal();
          if (rowSignature(current) !== requestedSignature) return null;
          dayMeals[mealIndex] = {
            ...current,
            combo_id: comboId,
            combo_match: found ? 'matched' : 'not_found',
          };
          return { weekly_days: { ...base.weekly_days, [day]: dayMeals } };
        }
        return null;
      });
    } catch (err) {
      console.error(err);
      emit((base) => {
        if (scope === 'default') {
          const meals = [...base.default_day_meals];
          const current = meals[mealIndex] || createEmptyMeal();
          if (rowSignature(current) !== requestedSignature) return null;
          meals[mealIndex] = { ...current, combo_id: null, combo_match: 'not_found' };
          return { default_day_meals: meals };
        }
        if (scope === 'weekly' && day) {
          const dayMeals = [...(base.weekly_days?.[day] || [])];
          const current = dayMeals[mealIndex] || createEmptyMeal();
          if (rowSignature(current) !== requestedSignature) return null;
          dayMeals[mealIndex] = { ...current, combo_id: null, combo_match: 'not_found' };
          return { weekly_days: { ...base.weekly_days, [day]: dayMeals } };
        }
        return null;
      });
    } finally {
      setLookupBusy((prev) => ({ ...prev, [key]: false }));
    }
  };

  const triggerAutoLookupForMeals = ({ scope, day, meals }) => {
    (Array.isArray(meals) ? meals : []).forEach((meal, mealIndex) => {
      lookupComboForRow({ row: meal, scope, day, mealIndex });
    });
  };

  const updateDefaultMealSlot = (mealIndex, slotKey, slotValue) => {
    const meals = [...normalized.default_day_meals];
    const nextMeal = { ...meals[mealIndex], [slotKey]: slotValue, combo_id: null, combo_match: 'unknown' };
    meals[mealIndex] = nextMeal;
    emit({ default_day_meals: meals });
    lookupComboForRow({ row: nextMeal, scope: 'default', mealIndex });
  };

  const updateWeeklyMealSlot = (day, mealIndex, slotKey, slotValue) => {
    const dayMeals = [...normalized.weekly_days[day]];
    const nextMeal = { ...dayMeals[mealIndex], [slotKey]: slotValue, combo_id: null, combo_match: 'unknown' };
    dayMeals[mealIndex] = nextMeal;
    emit({ weekly_days: { ...normalized.weekly_days, [day]: dayMeals } });
    lookupComboForRow({ row: nextMeal, scope: 'weekly', day, mealIndex });
  };

  const macroResultsByDay = useMemo(() => {
    const map = {};
    (Array.isArray(weeklyMacroResults) ? weeklyMacroResults : []).forEach((dayRow) => {
      if (dayRow?.day) map[dayRow.day] = dayRow;
    });
    return map;
  }, [weeklyMacroResults]);

  function applyMacroThresholdsToMeal(meal, mealSplit) {
    const next = { ...(meal || {}) };
    const beforeSignature = rowSignature(next);
    const proteinG = Number(mealSplit?.grams?.protein_g || 0);
    const carbsG = Number(mealSplit?.grams?.carbs_g || 0);
    const fatsG = Number(mealSplit?.grams?.fats_g || 0);
    const isTrainingAdjacent = mealSplit?.is_training_adjacent === true;

    if (proteinG === 0) {
      next.protein_1 = '-';
      next.protein_2 = '-';
    } else if (proteinG < SLOT_MIN_GRAMS_FOR_SECOND_SOURCE.protein_2) {
      next.protein_2 = '-';
    }

    if (carbsG === 0) {
      next.carbs_1 = '-';
      next.carbs_2 = '-';
    } else if (carbsG < SLOT_MIN_GRAMS_FOR_SECOND_SOURCE.carbs_2) {
      next.carbs_2 = '-';
    } else if (carbsG < TWO_CARB_ALLOWED_G && !(isTrainingAdjacent && carbsG >= TRAINING_ADJACENT_TWO_CARB_MIN_G)) {
      next.carbs_2 = '-';
    }

    if (fatsG === 0) {
      next.fats_1 = '-';
      next.fats_2 = '-';
    } else if (fatsG < SLOT_MIN_GRAMS_FOR_SECOND_SOURCE.fats_2) {
      next.fats_2 = '-';
    }

    const afterSignature = rowSignature(next);
    if (beforeSignature !== afterSignature) {
      return {
        ...next,
        combo_id: null,
        combo_match: 'unknown',
      };
    }
    return {
      ...next,
      combo_id: Number(meal?.combo_id) > 0 ? Number(meal.combo_id) : null,
      combo_match: meal?.combo_match || (Number(meal?.combo_id) > 0 ? 'matched' : 'unknown'),
    };
  }

  function applyMacroThresholdsToMealsForDay(meals, day) {
    const dayResult = macroResultsByDay[day];
    if (!dayResult) return meals;
    const trainingMatch = /^before_meal_(\d+)$/.exec(dayResult.training_before_meal || '');
    const postWorkoutMeal = trainingMatch ? Number(trainingMatch[1]) : null;
    return (Array.isArray(meals) ? meals : []).map((meal, idx) => {
      const mealNumber = idx + 1;
      const split = (dayResult.meal_macro_splits || []).find((row) => Number(row?.meal_number) === mealNumber) || null;
      const splitWithContext = split
        ? { ...split, is_training_adjacent: postWorkoutMeal === mealNumber || postWorkoutMeal === mealNumber + 1 }
        : null;
      return applyMacroThresholdsToMeal(meal, splitWithContext);
    });
  }

  const applyDefaultToAllDays = () => {
    const weeklyDays = { ...normalized.weekly_days };
    const lookupQueue = [];
    WEEK_DAYS.forEach((day) => {
      const cloned = cloneMealsForCount(normalized.default_day_meals, normalized.week_counts[day]);
      const patched = applyMacroThresholdsToMealsForDay(cloned, day);
      weeklyDays[day] = patched;
      lookupQueue.push({ day, meals: patched });
    });
    emit({ weekly_days: weeklyDays });
    lookupQueue.forEach(({ day, meals }) => triggerAutoLookupForMeals({ scope: 'weekly', day, meals }));
  };

  const saveDefaultAsTemplate = () => {
    const existing = normalized.saved_templates || [];
    if (existing.length >= MAX_SAVED_TEMPLATES) return;
    const nextNum = normalized.next_template_number || (existing.length + 1);
    const template = {
      id: `template_${Date.now()}`,
      name: `Template ${nextNum}`,
      meal_count: normalized.default_day_meal_count,
      meals: cloneMealsForCount(normalized.default_day_meals, normalized.default_day_meal_count),
    };
    emit({
      saved_templates: [...existing, template],
      next_template_number: nextNum + 1,
    });
  };

  const deleteTemplate = (templateId) => {
    emit({
      saved_templates: (normalized.saved_templates || []).filter((tpl) => tpl.id !== templateId),
    });
  };

  const renameTemplate = (templateId, name) => {
    emit({
      saved_templates: (normalized.saved_templates || []).map((tpl) =>
        tpl.id === templateId ? { ...tpl, name: name.slice(0, 40) } : tpl
      ),
    });
  };

  const loadTemplateIntoDefault = (template) => {
    const nextMeals = cloneMealsForCount(template.meals, template.meal_count);
    emit({
      default_day_meal_count: template.meal_count,
      default_day_meals: nextMeals,
    });
    triggerAutoLookupForMeals({ scope: 'default', meals: nextMeals });
  };

  const applyTemplateToDay = (template, day) => {
    const cloned = cloneMealsForCount(template.meals, normalized.week_counts[day]);
    const patched = applyMacroThresholdsToMealsForDay(cloned, day);
    emit({
      weekly_days: {
        ...normalized.weekly_days,
        [day]: patched,
      },
    });
    triggerAutoLookupForMeals({ scope: 'weekly', day, meals: patched });
  };

  const applyTemplateToAllDays = (template) => {
    const weeklyDays = { ...normalized.weekly_days };
    const lookupQueue = [];
    WEEK_DAYS.forEach((day) => {
      const cloned = cloneMealsForCount(template.meals, normalized.week_counts[day]);
      const patched = applyMacroThresholdsToMealsForDay(cloned, day);
      weeklyDays[day] = patched;
      lookupQueue.push({ day, meals: patched });
    });
    emit({ weekly_days: weeklyDays });
    lookupQueue.forEach(({ day, meals }) => triggerAutoLookupForMeals({ scope: 'weekly', day, meals }));
  };

  const activeDay = normalized.active_day;

  useEffect(() => {
    let ignore = false;
    const dayPayload = macroResultsByDay[activeDay] || null;
    setStarterLoading(true);
    apiRequest('/api/v1/users/client/public/meal-combo-starter-templates/', {
      method: dayPayload ? 'POST' : 'GET',
      body: dayPayload ? { day_payload: dayPayload } : undefined,
    })
      .then((res) => {
        if (ignore) return;
        if (res.ok) {
          setStarterTemplates(Array.isArray(res.data?.starter_templates) ? res.data.starter_templates : []);
        }
      })
      .catch((err) => {
        console.error(err);
      })
      .finally(() => {
        if (!ignore) setStarterLoading(false);
      });
    return () => { ignore = true; };
  }, [activeDay, macroResultsByDay]);

  useEffect(() => {
    if (copyTargetDay !== activeDay) return;
    setCopyTargetDay(WEEK_DAYS.find((day) => day !== activeDay) || 'monday');
  }, [activeDay, copyTargetDay]);

  const dayCompletion = useMemo(() => {
    const statuses = {};
    WEEK_DAYS.forEach((day) => {
      const meals = normalized.weekly_days?.[day] || [];
      const total = meals.length;
      const matched = meals.filter((meal) => Number(meal?.combo_id) > 0).length;
      statuses[day] = {
        total,
        matched,
        missing: Math.max(0, total - matched),
        isComplete: total > 0 && matched === total,
      };
    });
    return statuses;
  }, [normalized.weekly_days]);

  const weeklyCompletionSummary = useMemo(() => {
    const totalMeals = WEEK_DAYS.reduce((sum, day) => sum + (dayCompletion[day]?.total || 0), 0);
    const matchedMeals = WEEK_DAYS.reduce((sum, day) => sum + (dayCompletion[day]?.matched || 0), 0);
    const daysComplete = WEEK_DAYS.filter((day) => dayCompletion[day]?.isComplete).length;
    return {
      totalMeals,
      matchedMeals,
      missingMeals: Math.max(0, totalMeals - matchedMeals),
      daysComplete,
      totalDays: WEEK_DAYS.length,
      isComplete: totalMeals > 0 && matchedMeals === totalMeals,
    };
  }, [dayCompletion]);

  const getReferenceMealSplit = (scopeLabel, mealIndex) => {
    const referenceDay = scopeLabel === 'default' ? activeDay : scopeLabel;
    const dayResult = macroResultsByDay[referenceDay];
    if (!dayResult) return null;
    return (dayResult.meal_macro_splits || []).find((m) => Number(m.meal_number) === mealIndex + 1) || null;
  };

  const isSecondSlotDisabled = (slotKey, scopeLabel, mealIndex) => {
    const minRequired = SLOT_MIN_GRAMS_FOR_SECOND_SOURCE[slotKey];
    const mealSplit = getReferenceMealSplit(scopeLabel, mealIndex);
    if (!mealSplit) return false;
    const gramsKey = slotKey.startsWith('protein') ? 'protein_g' : slotKey.startsWith('carbs') ? 'carbs_g' : 'fats_g';
    const macroAmount = Number(mealSplit?.grams?.[gramsKey] || 0);
    const dayResult = macroResultsByDay[scopeLabel === 'default' ? activeDay : scopeLabel];
    const trainingMatch = /^before_meal_(\d+)$/.exec(dayResult?.training_before_meal || '');
    const postWorkoutMeal = trainingMatch ? Number(trainingMatch[1]) : null;
    const mealNumber = mealIndex + 1;
    const isTrainingAdjacent = postWorkoutMeal === mealNumber || postWorkoutMeal === mealNumber + 1;
    // Block second source if macro is below threshold, or if macro is zero (block all sources)
    if (slotKey.endsWith('_2')) {
      if (macroAmount < minRequired) return true;
      if (slotKey === 'carbs_2' && macroAmount < TWO_CARB_ALLOWED_G && !(isTrainingAdjacent && macroAmount >= TRAINING_ADJACENT_TWO_CARB_MIN_G)) return true;
    }
    // Block all sources if macro is zero
    if (macroAmount === 0) return true;
    return false;
  };

  const applyStarterTemplateToDefault = (template) => {
    const count = [3, 4, 5, 6].includes(Number(template?.default_meal_count)) ? Number(template.default_meal_count) : 6;
    const baseMeals = ensureMealArray(template?.default_day_meals, count);
    const patched = applyMacroThresholdsToMealsForDay(baseMeals, activeDay);
    emit({
      default_day_meal_count: count,
      default_day_meals: patched,
    });
    triggerAutoLookupForMeals({ scope: 'default', meals: patched });
  };

  const applyStarterTemplateToActiveDay = (template) => {
    const cloned = cloneMealsForCount(template?.default_day_meals, normalized.week_counts[activeDay]);
    const patched = applyMacroThresholdsToMealsForDay(cloned, activeDay);
    emit({
      weekly_days: {
        ...normalized.weekly_days,
        [activeDay]: patched,
      },
    });
    triggerAutoLookupForMeals({ scope: 'weekly', day: activeDay, meals: patched });
  };

  const copyDayToDay = (fromDay, toDay) => {
    if (!fromDay || !toDay || fromDay === toDay) return;
    const cloned = cloneMealsForCount(normalized.weekly_days[fromDay], normalized.week_counts[toDay]);
    const patched = applyMacroThresholdsToMealsForDay(cloned, toDay);
    emit({
      weekly_days: {
        ...normalized.weekly_days,
        [toDay]: patched,
      },
    });
    triggerAutoLookupForMeals({ scope: 'weekly', day: toDay, meals: patched });
  };

  const copyDayToAllIncompleteDays = (fromDay) => {
    if (!fromDay) return;
    const weeklyDays = { ...normalized.weekly_days };
    const lookupQueue = [];
    let changed = 0;
    WEEK_DAYS.forEach((day) => {
      if (day === fromDay) return;
      if (dayCompletion[day]?.isComplete) return;
      const cloned = cloneMealsForCount(normalized.weekly_days[fromDay], normalized.week_counts[day]);
      const patched = applyMacroThresholdsToMealsForDay(cloned, day);
      weeklyDays[day] = patched;
      lookupQueue.push({ day, meals: patched });
      changed += 1;
    });
    if (!changed) return;
    emit({ weekly_days: weeklyDays });
    lookupQueue.forEach(({ day, meals }) => triggerAutoLookupForMeals({ scope: 'weekly', day, meals }));
  };

  const renderMealRow = ({ meal, mealIndex, onSlotChange, scopeLabel, lookupKey }) => {
    const refDay = scopeLabel === 'default' ? activeDay : scopeLabel;
    const dayResult = macroResultsByDay[refDay];
    const mealSplit = getReferenceMealSplit(scopeLabel, mealIndex);
    const mealContext = getMealContextLabel(dayResult, mealIndex + 1);
    return (
    <div key={`${scopeLabel}-${mealIndex}`} className="client-q-stack" style={{ border: '1px solid rgba(20,40,74,0.1)', borderRadius: 12, padding: '0.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem', alignItems: 'center' }}>
        <div className="client-q-stack" style={{ gap: '0.25rem' }}>
          <strong>Meal {mealIndex + 1}</strong>
          <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
            {scopeLabel !== 'default' ? (
              <span className="client-q-chip">{prettyDay(refDay)}</span>
            ) : null}
            {dayResult ? <span className="client-q-chip">{dayResult.is_workout_day ? 'Workout Day' : 'Off Day'}</span> : null}
            {mealContext ? <span className="client-q-chip">{mealContext}</span> : null}
            {dayResult?.training_before_meal ? <span className="client-q-chip">{dayResult.training_before_meal.replace('before_meal_', 'Train before meal ')}</span> : null}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {mealSplit ? (
            <>
              <span className="client-q-chip">P {mealSplit.grams?.protein_g}g</span>
              <span className="client-q-chip">C {mealSplit.grams?.carbs_g}g</span>
              <span className="client-q-chip">F {mealSplit.grams?.fats_g}g</span>
            </>
          ) : null}
          <span className={`client-q-chip ${meal.combo_match === 'matched' ? 'ok' : meal.combo_match === 'not_found' ? 'warn' : ''}`}>
            {meal.combo_match === 'matched'
              ? `Combo ID: ${meal.combo_id}`
              : meal.combo_match === 'not_found'
                ? 'No combo match'
                : lookupBusy[lookupKey] || meal.combo_match === 'checking'
                  ? 'Checking combo...'
                  : 'Waiting...'}
          </span>
        </div>
      </div>
      <div className="client-q-inline-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}>
        {SLOT_KEYS.map((slotKey) => (
          <label key={`${scopeLabel}-${mealIndex}-${slotKey}`}>
            {SLOT_LABELS[slotKey]}
            {(() => {
              const disabled = isSecondSlotDisabled(slotKey, scopeLabel, mealIndex);
              const currentValue = meal[slotKey] || '-';
              const baseOptions = slotOptions?.[slotKey] || ['-'];
              const selectValue = baseOptions.includes(currentValue) ? currentValue : '-';
              return (
                <select
                  value={disabled ? '-' : selectValue}
                  onChange={(e) => onSlotChange(mealIndex, slotKey, e.target.value)}
                  disabled={disabled}
                >
                  {baseOptions.map((opt) => (
                    <option key={`${slotKey}-${opt}`} value={opt}>{opt}</option>
                  ))}
                </select>
              );
            })()}
            {(() => {
              const mealSplit = getReferenceMealSplit(scopeLabel, mealIndex);
              const gramsKey = slotKey.startsWith('protein') ? 'protein_g' : slotKey.startsWith('carbs') ? 'carbs_g' : 'fats_g';
              const macroAmount = Number(mealSplit?.grams?.[gramsKey] || 0);
              if (macroAmount === 0) {
                return (
                  <small className="client-q-help">
                    Locked for this meal (no {slotKey.startsWith('protein') ? 'protein' : slotKey.startsWith('carbs') ? 'carb' : 'fat'} assigned).
                  </small>
                );
              }
              if (slotKey.endsWith('_2')) {
                const minRequired = SLOT_MIN_GRAMS_FOR_SECOND_SOURCE[slotKey];
                if (macroAmount < minRequired) {
                  return (
                    <small className="client-q-help">
                      Locked for this meal (macro amount too low for a second {slotKey.startsWith('protein') ? 'protein' : slotKey.startsWith('carbs') ? 'carb' : 'fat'} source).
                    </small>
                  );
                }
              }
              return null;
            })()}
          </label>
        ))}
      </div>
    </div>
  );
  };

  return (
    <div className="client-q-stack">
      <p className="client-q-help">
        Build one full default day of meals using food combo dropdowns. We match each meal to a `meal_combo_id`, then you can apply it to the whole week and customize specific days.
      </p>
      {optionsError ? <p className="client-q-error">{optionsError}</p> : null}

      <div className="client-q-stack">
        <strong>Template Setup Mode</strong>
        <div className="client-q-card-grid" style={{ gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
          <button
            type="button"
            className={`client-q-option-card ${templatePanelMode === 'starter' ? 'is-active' : ''}`}
            onClick={() => setTemplatePanelMode('starter')}
          >
            <span>Starter Template Library</span>
          </button>
          <button
            type="button"
            className={`client-q-option-card ${templatePanelMode === 'default' ? 'is-active' : ''}`}
            onClick={() => setTemplatePanelMode('default')}
          >
            <span>Default Day Template</span>
          </button>
        </div>
      </div>

      {templatePanelMode === 'starter' ? (
      <div className="client-q-stack">
        <strong>Starter Template Library</strong>
        <p className="client-q-help">
          Quick defaults built from your combo database: Meal 1 is breakfast-style, Meals 2-6 are lunch/dinner combos. Use one, then customize.
        </p>
        {starterLoading ? (
          <p className="client-q-help">Loading starter templates…</p>
        ) : (
          <div className="client-q-stack">
            {starterTemplates.map((template) => (
              <div key={template.template_key} style={{ border: '1px solid rgba(20,40,74,0.1)', borderRadius: 12, padding: '0.75rem' }}>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                  <strong>{template.name}</strong>
                  <span className="client-q-chip">{template.default_meal_count} meals</span>
                </div>
                <p className="client-q-help" style={{ marginTop: '0.35rem' }}>{template.description}</p>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
                  <button type="button" className="client-q-btn secondary" onClick={() => applyStarterTemplateToDefault(template)}>
                    Use As Default Day
                  </button>
                  <button type="button" className="client-q-btn secondary" onClick={() => applyStarterTemplateToActiveDay(template)}>
                    Apply To {activeDay.slice(0, 3).toUpperCase()}
                  </button>
                </div>
              </div>
            ))}
            {!starterTemplates.length ? (
              <p className="client-q-help">No starter templates available yet.</p>
            ) : null}
          </div>
        )}
      </div>
      ) : null}

      {templatePanelMode === 'default' ? (
      <div className="client-q-stack">
        <strong>Default Day Template</strong>
        <p className="client-q-help">
          Build one full day, then apply it across the week. You can also save multiple templates and reuse them for different days.
        </p>
        <div className="client-q-card-grid">
          {[3, 4, 5, 6].map((count) => (
            <button
              key={`default-count-${count}`}
              type="button"
              className={`client-q-option-card ${normalized.default_day_meal_count === count ? 'is-active' : ''}`}
              onClick={() => updateDefaultMealCount(count)}
            >
              <span>{count} Meals</span>
            </button>
          ))}
        </div>
        <div className="client-q-stack">
          {normalized.default_day_meals.map((meal, idx) =>
            renderMealRow({
              meal,
              mealIndex: idx,
              scopeLabel: 'default',
              lookupKey: `default:default:${idx}`,
              onSlotChange: updateDefaultMealSlot,
            }))}
        </div>
        <button type="button" className="client-q-btn" onClick={applyDefaultToAllDays}>
          Apply Default Day To Whole Week
        </button>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="client-q-btn secondary"
            onClick={saveDefaultAsTemplate}
            disabled={(normalized.saved_templates || []).length >= MAX_SAVED_TEMPLATES}
          >
            {(normalized.saved_templates || []).length >= MAX_SAVED_TEMPLATES
              ? `Template Limit Reached (${MAX_SAVED_TEMPLATES})`
              : 'Save This Day As Template'}
          </button>
          <span className="client-q-help" style={{ alignSelf: 'center' }}>
            You can save up to {MAX_SAVED_TEMPLATES} templates and apply them to one day or the whole week.
          </span>
        </div>
      </div>
      ) : null}

      <div className="client-q-stack">
        <strong>Saved Templates</strong>
        {(normalized.saved_templates || []).length === 0 ? (
          <p className="client-q-help">No saved templates yet. Build a default day and save it as a template.</p>
        ) : (
          <div className="client-q-stack">
            {normalized.saved_templates.map((template) => (
              <div
                key={template.id}
                className="client-q-stack"
                style={{ border: '1px solid rgba(20,40,74,0.1)', borderRadius: 12, padding: '0.75rem' }}
              >
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                  <input
                    type="text"
                    value={template.name}
                    onChange={(e) => renameTemplate(template.id, e.target.value)}
                    style={{ maxWidth: 220 }}
                  />
                  <span className="client-q-chip">{template.meal_count} meals</span>
                  <span className="client-q-help">
                    {template.meals.filter((m) => Number(m?.combo_id) > 0).length}/{template.meals.length} combo IDs matched
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <button type="button" className="client-q-btn secondary" onClick={() => loadTemplateIntoDefault(template)}>
                    Load Into Default Day
                  </button>
                  <button type="button" className="client-q-btn secondary" onClick={() => applyTemplateToAllDays(template)}>
                    Apply To Whole Week
                  </button>
                  <button type="button" className="client-q-btn secondary" onClick={() => applyTemplateToDay(template, activeDay)}>
                    Apply To {activeDay.slice(0, 3).toUpperCase()}
                  </button>
                  <button type="button" className="client-q-btn danger" onClick={() => deleteTemplate(template.id)}>
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="client-q-stack">
        <strong>Customize Specific Day (Optional)</strong>
        <p className="client-q-help">
          Every day must end up with valid meal combo IDs. Use templates to speed up setup, then tweak specific meals if needed.
        </p>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <span className={`client-q-chip ${weeklyCompletionSummary.isComplete ? 'ok' : weeklyCompletionSummary.missingMeals ? 'warn' : ''}`}>
            {weeklyCompletionSummary.isComplete
              ? 'Week complete'
              : `${weeklyCompletionSummary.missingMeals} missing combo${weeklyCompletionSummary.missingMeals === 1 ? '' : 's'}`}
          </span>
          <span className="client-q-chip">{weeklyCompletionSummary.daysComplete}/{weeklyCompletionSummary.totalDays} days complete</span>
          <span className="client-q-chip">{weeklyCompletionSummary.matchedMeals}/{weeklyCompletionSummary.totalMeals} meals matched</span>
        </div>
        <div className="client-q-inline-grid" style={{ gridTemplateColumns: 'minmax(0, 1fr) minmax(180px, 260px) auto' }}>
          <label>
            Copy source day
            <input type="text" value={`${prettyDay(activeDay)} (${normalized.week_counts[activeDay]} meals)`} readOnly />
          </label>
          <label>
            Copy to day
            <select value={copyTargetDay} onChange={(e) => setCopyTargetDay(e.target.value)}>
              {WEEK_DAYS.filter((day) => day !== activeDay).map((day) => (
                <option key={`copy-target-${day}`} value={day}>
                  {prettyDay(day)} ({normalized.week_counts[day]} meals)
                </option>
              ))}
            </select>
          </label>
          <div style={{ display: 'flex', alignItems: 'end' }}>
            <button
              type="button"
              className="client-q-btn secondary"
              onClick={() => copyDayToDay(activeDay, copyTargetDay)}
              disabled={!copyTargetDay || copyTargetDay === activeDay}
            >
              Copy Day
            </button>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="client-q-btn secondary"
            onClick={() => copyDayToAllIncompleteDays(activeDay)}
            disabled={weeklyCompletionSummary.isComplete || WEEK_DAYS.every((day) => day === activeDay || dayCompletion[day]?.isComplete)}
          >
            Copy {prettyDay(activeDay)} To All Incomplete Days
          </button>
          <span className="client-q-help" style={{ alignSelf: 'center' }}>
            This only fills days that are still incomplete and keeps completed/customized days untouched.
          </span>
        </div>
        <div className="client-q-day-grid">
          {WEEK_DAYS.map((day) => (
            <button
              key={`day-tab-${day}`}
              type="button"
              className={`client-q-day ${activeDay === day ? 'is-active' : ''}`}
              onClick={() => emit({ active_day: day })}
            >
              <div style={{ display: 'grid', gap: '0.1rem', justifyItems: 'center' }}>
                <span>{day.slice(0, 3).toUpperCase()} • {normalized.week_counts[day]}</span>
                <span style={{ fontSize: '0.68rem', fontWeight: 700, opacity: activeDay === day ? 0.95 : 0.8 }}>
                  {dayCompletion[day]?.isComplete ? 'Complete' : `${dayCompletion[day]?.missing || 0} missing`}
                </span>
              </div>
            </button>
          ))}
        </div>
        <div className="client-q-stack">
          {(normalized.weekly_days[activeDay] || []).map((meal, idx) =>
            renderMealRow({
              meal,
              mealIndex: idx,
              scopeLabel: activeDay,
              lookupKey: `weekly:${activeDay}:${idx}`,
              onSlotChange: (mealIndex, slotKey, slotValue) => updateWeeklyMealSlot(activeDay, mealIndex, slotKey, slotValue),
            }))}
        </div>
      </div>
    </div>
  );
}

export default MealComboBuilderStep;
