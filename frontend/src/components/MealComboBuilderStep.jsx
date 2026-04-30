import React, { useEffect, useMemo, useRef, useState } from 'react';
import { apiRequest } from '../api/client';
import ProductSearchPicker from './ProductSearchPicker';
import {
  mealTemplateBadges,
  mealTemplateDescription,
  mealTemplateImage,
  mealTemplateTitle,
  templateCoverImage,
} from './mealTemplateVisuals';

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

function clampMealNumber(value, mealCount) {
  const count = [3, 4, 5, 6].includes(Number(mealCount)) ? Number(mealCount) : 3;
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 1;
  return Math.max(1, Math.min(count, Math.round(parsed)));
}

function proteinShakeMealsByDay(proteinShake = {}, mealCounts = {}) {
  if (proteinShake?.enabled !== true || proteinShake?.counts_as_meal !== true) return {};
  const selectedByDay = proteinShake?.selected_meals_by_day || {};
  const fallback = proteinShake?.selected_meal || 1;
  return WEEK_DAYS.reduce((acc, day) => {
    acc[day] = clampMealNumber(selectedByDay[day] ?? fallback, mealCounts[day]);
    return acc;
  }, {});
}

function createProteinShakeMeal(source = {}) {
  return {
    ...createEmptyMeal(),
    ...(source || {}),
    meal_type: 'protein_shake',
    is_protein_shake: true,
    protein_1: '-',
    protein_2: '-',
    carbs_1: '-',
    carbs_2: '-',
    fats_1: '-',
    fats_2: '-',
    combo_id: null,
    combo_match: 'protein_shake',
  };
}

function isProteinShakeMeal(meal) {
  return meal?.is_protein_shake === true || meal?.meal_type === 'protein_shake';
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

function proteinShakePlacementLabel(proteinShake = {}) {
  if (proteinShake?.enabled !== true || proteinShake?.counts_as_meal !== true) return '';
  if (proteinShake.placement_mode === 'pre_workout') return 'pre-workout';
  if (proteinShake.placement_mode === 'post_workout') return 'post-workout';
  return `Meal ${proteinShake.selected_meal || 1}`;
}

function MealComboBuilderStep({ value, onChange, mealScheduleDays = {}, weeklyMacroResults = [], proteinShake = {} }) {
  const [slotOptions, setSlotOptions] = useState(null);
  const [optionsError, setOptionsError] = useState('');
  const [lookupBusy, setLookupBusy] = useState({});
  const [starterTemplates, setStarterTemplates] = useState([]);
  const [starterLoading, setStarterLoading] = useState(false);
  const [copyTargetDay, setCopyTargetDay] = useState('monday');
  const [templatePanelMode, setTemplatePanelMode] = useState('template');
  const [expandedCustomize, setExpandedCustomize] = useState({});
  const [templateChooserMeal, setTemplateChooserMeal] = useState(null);
  const [foodOverrides, setFoodOverrides] = useState({});
  const [usdaPicker, setUsdaPicker] = useState({
    open: false,
    canonicalCategory: '',
    query: '',
    barcode: '',
    loading: false,
    error: '',
    results: [],
    notFound: false,
    imageUploadingId: '',
  });

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

  const loadFoodOverrides = async () => {
    try {
      const res = await apiRequest('/api/v1/users/client/app/food-overrides/', { auth: true });
      if (!res.ok) return;
      const map = {};
      (Array.isArray(res.data?.food_overrides) ? res.data.food_overrides : []).forEach((row) => {
        if (row?.canonical_category) map[row.canonical_category] = row;
      });
      setFoodOverrides(map);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadFoodOverrides();
  }, []);

  const normalized = useMemo(() => {
    const weekCounts = WEEK_DAYS.reduce((acc, day) => {
      acc[day] = [3, 4, 5, 6].includes(Number(mealScheduleDays?.[day])) ? Number(mealScheduleDays[day]) : 3;
      return acc;
    }, {});
    const shakeMeals = proteinShakeMealsByDay(proteinShake, weekCounts);
    const defaultCount = Number(value?.default_day_meal_count || weekCounts.sunday || 3);
    const defaultMeals = ensureMealArray(value?.default_day_meals, defaultCount);
    const weekly = WEEK_DAYS.reduce((acc, day) => {
      const meals = ensureMealArray(value?.weekly_days?.[day], weekCounts[day]);
      const shakeMealNumber = shakeMeals[day];
      if (shakeMealNumber) {
        meals[shakeMealNumber - 1] = createProteinShakeMeal(meals[shakeMealNumber - 1]);
      }
      acc[day] = meals;
      return acc;
    }, {});
    return {
      active_day: value?.active_day || 'sunday',
      default_day_meal_count: [3, 4, 5, 6].includes(defaultCount) ? defaultCount : 3,
      default_day_meals: defaultMeals,
      weekly_days: weekly,
      week_counts: weekCounts,
      protein_shake_meals: shakeMeals,
      saved_templates: normalizeSavedTemplates(value?.saved_templates),
      next_template_number: Math.max(1, Number(value?.next_template_number || 1)),
    };
  }, [value, mealScheduleDays, proteinShake]);

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
      if (isProteinShakeMeal(meal)) return;
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
    if (isProteinShakeMeal(normalized.weekly_days?.[day]?.[mealIndex])) return;
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
    if (isProteinShakeMeal(meal)) return createProteinShakeMeal(meal);
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

  const openUsdaPicker = (canonicalCategory) => {
    const cleanCategory = normalizeSlotValue(canonicalCategory);
    setUsdaPicker({
      open: true,
      canonicalCategory: cleanCategory,
      query: cleanCategory.replace(/\sSTANDARD$/i, ''),
      barcode: '',
      loading: false,
      error: '',
      results: [],
      notFound: false,
      imageUploadingId: '',
    });
  };

  const searchUsdaFoods = async () => {
    const query = String(usdaPicker.query || '').trim();
    if (!query) return;
    setUsdaPicker((prev) => ({ ...prev, loading: true, error: '', notFound: false }));
    try {
      console.debug('[ProductSearchPicker] product search request', {
        url: '/api/v1/users/client/app/food-overrides/products/search/',
        query,
      });
      const res = await apiRequest('/api/v1/users/client/app/food-overrides/products/search/', {
        method: 'POST',
        auth: true,
        body: { query, page: 1, page_size: 12, providers: ['open_food_facts', 'usda'] },
      });
      console.debug('[ProductSearchPicker] product search response', {
        status: res.status,
        count: Array.isArray(res.data?.products) ? res.data.products.length : 0,
      });
      if (!res.ok) {
        setUsdaPicker((prev) => ({
          ...prev,
          loading: false,
          error: 'Could not search products right now. Try again.',
        }));
        return;
      }
      setUsdaPicker((prev) => ({
        ...prev,
        loading: false,
        results: Array.isArray(res.data?.products) ? res.data.products : [],
      }));
    } catch (err) {
      console.error(err);
      setUsdaPicker((prev) => ({ ...prev, loading: false, error: 'Could not search products right now. Try again.' }));
    }
  };

  const lookupBarcode = async () => {
    const barcode = String(usdaPicker.barcode || '').trim();
    if (!barcode) return;
    setUsdaPicker((prev) => ({ ...prev, loading: true, error: '', notFound: false }));
    try {
      console.debug('[ProductSearchPicker] barcode lookup request', {
        url: '/api/v1/users/client/app/food-overrides/products/barcode/',
        barcode,
      });
      const res = await apiRequest('/api/v1/users/client/app/food-overrides/products/barcode/', {
        method: 'POST',
        auth: true,
        body: { barcode },
      });
      console.debug('[ProductSearchPicker] barcode lookup response', {
        status: res.status,
        product: res.data?.product || null,
      });
      if (!res.ok) {
        const notFound = res.status === 404 || res.data?.error?.code === 'PRODUCT_NOT_FOUND';
        setUsdaPicker((prev) => ({
          ...prev,
          loading: false,
          notFound,
          error: notFound ? '' : 'Could not search products right now. Try again.',
        }));
        return;
      }
      setUsdaPicker((prev) => ({
        ...prev,
        loading: false,
        results: res.data?.product ? [res.data.product] : [],
      }));
    } catch (err) {
      console.error(err);
      setUsdaPicker((prev) => ({ ...prev, loading: false, error: 'Could not search products right now. Try again.' }));
    }
  };

  const saveUsdaOverride = async (food) => {
    const providerProductId = food?.provider_product_id || food?.external_food_id || food?.fdc_id || food?.barcode;
    const provider = food?.provider || food?.external_provider || (food?.fdc_id ? 'usda' : '');
    if (!providerProductId || !provider || !usdaPicker.canonicalCategory) return;
    setUsdaPicker((prev) => ({ ...prev, loading: true, error: '' }));
    try {
      const res = await apiRequest('/api/v1/users/client/app/food-overrides/save/', {
        method: 'POST',
        auth: true,
        body: {
          canonical_category: usdaPicker.canonicalCategory,
          provider,
          provider_product_id: providerProductId,
        },
      });
      if (!res.ok) {
        setUsdaPicker((prev) => ({
          ...prev,
          loading: false,
          error: 'Could not save this product right now. Try again.',
        }));
        return;
      }
      const saved = res.data?.food_override;
      if (saved?.canonical_category) {
        setFoodOverrides((prev) => ({ ...prev, [saved.canonical_category]: saved }));
      }
      setUsdaPicker({
        open: false,
        canonicalCategory: '',
        query: '',
        barcode: '',
        loading: false,
        error: '',
        results: [],
        notFound: false,
        imageUploadingId: '',
      });
    } catch (err) {
      console.error(err);
      setUsdaPicker((prev) => ({ ...prev, loading: false, error: 'Could not save this product right now. Try again.' }));
    }
  };

  const uploadProductImage = async (food, file) => {
    const providerProductId = food?.provider_product_id || food?.external_food_id || food?.fdc_id || food?.barcode;
    const provider = food?.provider || food?.external_provider || (food?.fdc_id ? 'usda' : '');
    if (!providerProductId || !provider || !file) return;
    const formData = new FormData();
    formData.append('provider', provider);
    formData.append('provider_product_id', providerProductId);
    formData.append('barcode', food?.barcode || '');
    formData.append('product_name', food?.display_name || food?.name || '');
    formData.append('brand', food?.brand_name || food?.brand || '');
    formData.append('image', file);
    setUsdaPicker((prev) => ({ ...prev, imageUploadingId: providerProductId, error: '' }));
    try {
      const res = await apiRequest('/api/v1/users/client/app/food-overrides/products/images/submit/', {
        method: 'POST',
        auth: true,
        body: formData,
      });
      if (!res.ok) {
        setUsdaPicker((prev) => ({
          ...prev,
          imageUploadingId: '',
          error: 'Could not upload image right now. Try again.',
        }));
        return;
      }
      const submission = res.data?.image_submission;
      setUsdaPicker((prev) => ({
        ...prev,
        imageUploadingId: '',
        results: (prev.results || []).map((row) => {
          const rowId = row.provider_product_id || row.external_food_id || row.fdc_id || row.barcode;
          if (rowId !== providerProductId || (row.provider || row.external_provider) !== provider) return row;
          return {
            ...row,
            image_submission_status: submission?.status || 'pending',
            image_submission_id: submission?.id || row.image_submission_id,
          };
        }),
      }));
    } catch (err) {
      console.error(err);
      setUsdaPicker((prev) => ({
        ...prev,
        imageUploadingId: '',
        error: 'Could not upload image right now. Try again.',
      }));
    }
  };

  const removeFoodOverride = async (override) => {
    if (!override?.id) return;
    try {
      const res = await apiRequest(`/api/v1/users/client/app/food-overrides/${override.id}/`, {
        method: 'DELETE',
        auth: true,
      });
      if (!res.ok) return;
      setFoodOverrides((prev) => {
        const next = { ...prev };
        delete next[override.canonical_category];
        return next;
      });
    } catch (err) {
      console.error(err);
    }
  };

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
      const matched = meals.filter((meal) => isProteinShakeMeal(meal) || Number(meal?.combo_id) > 0).length;
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
    emit({
      default_day_meal_count: count,
      default_day_meals: baseMeals,
    });
  };

  const applyStarterTemplateToActiveDay = (template) => {
    const cloned = cloneMealsForCount(template?.default_day_meals, normalized.week_counts[activeDay]);
    const shakeMealNumber = normalized.protein_shake_meals?.[activeDay];
    if (shakeMealNumber) cloned[shakeMealNumber - 1] = createProteinShakeMeal(cloned[shakeMealNumber - 1]);
    emit({
      weekly_days: {
        ...normalized.weekly_days,
        [activeDay]: cloned,
      },
    });
  };

  const applyStarterMealToActiveDay = (meal, mealIndex) => {
    if (normalized.protein_shake_meals?.[activeDay] === mealIndex + 1) return;
    const dayMeals = [...(normalized.weekly_days[activeDay] || [])];
    dayMeals[mealIndex] = {
      ...createEmptyMeal(),
      ...(meal || {}),
      combo_match: Number(meal?.combo_id) > 0 ? 'matched' : (meal?.combo_match || 'unknown'),
    };
    emit({
      weekly_days: {
        ...normalized.weekly_days,
        [activeDay]: dayMeals,
      },
    });
  };

  const starterMealOptionsForIndex = (mealIndex) => (
    normalized.protein_shake_meals?.[activeDay] === mealIndex + 1
      ? []
      : (starterTemplates || [])
      .map((template) => ({
        template,
        meal: Array.isArray(template?.default_day_meals) ? template.default_day_meals[mealIndex] : null,
      }))
      .filter((row) => row.meal)
  );

  const toggleCustomize = (key) => {
    setExpandedCustomize((prev) => ({ ...prev, [key]: !prev[key] }));
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
              const override = foodOverrides[selectValue];
              return (
                <>
                <select
                  value={disabled ? '-' : selectValue}
                  onChange={(e) => onSlotChange(mealIndex, slotKey, e.target.value)}
                  disabled={disabled}
                >
                  {baseOptions.map((opt) => (
                    <option key={`${slotKey}-${opt}`} value={opt}>{opt}</option>
                  ))}
                </select>
                {!disabled && selectValue !== '-' ? (
                  <div className="client-q-stack" style={{ gap: '0.3rem', marginTop: '0.35rem' }}>
                    {override ? (
                      <small className="client-q-help">
                        Product override: {override.display_name}
                        {override.measurement_basis_label ? ` • ${override.measurement_basis_label}` : ''}
                      </small>
                    ) : null}
                    <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                      <button
                        type="button"
                        className="client-q-btn secondary"
                        style={{ padding: '0.35rem 0.55rem', fontSize: '0.78rem' }}
                        onClick={() => openUsdaPicker(selectValue)}
                      >
                        {override ? 'Change product' : 'Choose product'}
                      </button>
                      {override ? (
                        <button
                          type="button"
                          className="client-q-btn secondary"
                          style={{ padding: '0.35rem 0.55rem', fontSize: '0.78rem' }}
                          onClick={() => removeFoodOverride(override)}
                        >
                          Remove
                        </button>
                      ) : null}
                    </div>
                  </div>
                ) : null}
                </>
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

  const renderTemplateSummaryCard = (template) => {
    const meals = Array.isArray(template?.default_day_meals) ? template.default_day_meals : [];
    const matched = meals.filter((meal) => Number(meal?.combo_id) > 0).length;
    return (
      <article key={template.template_key} className="meal-template-card">
        <div className="meal-template-card__image">
          <img src={templateCoverImage(template)} alt="" />
        </div>
        <div className="meal-template-card__body">
          <div className="meal-template-card__top">
            <strong>{template.name}</strong>
            <span className="client-q-chip">{template.default_meal_count} meals</span>
          </div>
          <p>{template.description}</p>
          <div className="meal-template-card__badges">
            <span className="client-q-chip ok">{matched}/{meals.length} matched</span>
            <span className="client-q-chip">STANDARD slots</span>
          </div>
          <div className="meal-template-card__actions">
            <button type="button" className="client-q-btn" onClick={() => applyStarterTemplateToActiveDay(template)}>
              Use for {prettyDay(activeDay)}
            </button>
            <button type="button" className="client-q-btn secondary" onClick={() => applyStarterTemplateToDefault(template)}>
              Use as default
            </button>
          </div>
        </div>
      </article>
    );
  };

  const renderMealTemplateOption = ({ template, meal }, mealIndex) => {
    const refDay = activeDay;
    const dayResult = macroResultsByDay[refDay];
    const mealSplit = getReferenceMealSplit(refDay, mealIndex);
    const mealContext = getMealContextLabel(dayResult, mealIndex + 1);
    const badges = mealTemplateBadges(meal, mealSplit, mealContext);
    return (
      <button
        key={`${template.template_key}-${mealIndex}-${meal.combo_id || rowSignature(meal)}`}
        type="button"
        className="meal-choice-card"
        onClick={() => {
          applyStarterMealToActiveDay(meal, mealIndex);
          setTemplateChooserMeal(null);
        }}
      >
        <img src={mealTemplateImage(meal)} alt="" />
        <span className="meal-choice-card__title">{mealTemplateTitle(meal, `Meal ${mealIndex + 1}`)}</span>
        <span className="meal-choice-card__description">{mealTemplateDescription(meal)}</span>
        <span className="meal-choice-card__badges">
          {badges.map((badge) => <span key={badge} className="client-q-chip">{badge}</span>)}
        </span>
        <span className="meal-choice-card__source">{template.name}</span>
      </button>
    );
  };

  const renderSelectedMealCard = (meal, idx) => {
    const scopeLabel = activeDay;
    const lookupKey = `weekly:${activeDay}:${idx}`;
    const dayResult = macroResultsByDay[activeDay];
    const mealSplit = getReferenceMealSplit(activeDay, idx);
    const mealContext = getMealContextLabel(dayResult, idx + 1);
    const customizeKey = `${activeDay}-${idx}`;
    const isOpen = Boolean(expandedCustomize[customizeKey]);
    const options = starterMealOptionsForIndex(idx);
    if (isProteinShakeMeal(meal)) {
      return (
        <article key={`${activeDay}-shake-${idx}`} className="visual-meal-card">
          <div className="visual-meal-card__body">
            <div className="visual-meal-card__header">
              <div>
                <span className="visual-meal-card__eyebrow">Meal {idx + 1}</span>
                <strong>Protein Shake</strong>
              </div>
              <span className="client-q-chip ok">Reserved</span>
            </div>
            <p className="visual-meal-card__description">
              This meal is reserved for your protein shake.
            </p>
            <div className="visual-meal-card__badges">
              <span className="client-q-chip">No meal combo required</span>
              {mealContext ? <span className="client-q-chip">{mealContext}</span> : null}
              {dayResult?.training_before_meal ? <span className="client-q-chip">{dayResult.training_before_meal.replace('before_meal_', 'Train before meal ')}</span> : null}
            </div>
          </div>
        </article>
      );
    }
    return (
      <article key={`${activeDay}-visual-${idx}`} className="visual-meal-card">
        <div className="visual-meal-card__image">
          <img src={mealTemplateImage(meal)} alt="" />
        </div>
        <div className="visual-meal-card__body">
          <div className="visual-meal-card__header">
            <div>
              <span className="visual-meal-card__eyebrow">Meal {idx + 1}</span>
              <strong>{mealTemplateTitle(meal, 'Choose a template')}</strong>
            </div>
            <span className={`client-q-chip ${meal.combo_match === 'matched' ? 'ok' : meal.combo_match === 'not_found' ? 'warn' : ''}`}>
              {meal.combo_match === 'matched'
                ? `Combo ${meal.combo_id}`
                : lookupBusy[lookupKey] || meal.combo_match === 'checking'
                  ? 'Checking'
                  : 'Pending'}
            </span>
          </div>
          <p className="visual-meal-card__description">{mealTemplateDescription(meal)}</p>
          <div className="visual-meal-card__badges">
            {mealSplit ? (
              <>
                <span className="client-q-chip">P {mealSplit.grams?.protein_g}g</span>
                <span className="client-q-chip">C {mealSplit.grams?.carbs_g}g</span>
                <span className="client-q-chip">F {mealSplit.grams?.fats_g}g</span>
              </>
            ) : null}
            {mealContext ? <span className="client-q-chip">{mealContext}</span> : null}
            {mealTemplateBadges(meal, mealSplit, mealContext).map((badge) => (
              <span key={`${idx}-${badge}`} className="client-q-chip">{badge}</span>
            ))}
          </div>
          <div className="visual-meal-card__actions">
            <button
              type="button"
              className="client-q-btn"
              onClick={() => setTemplateChooserMeal(templateChooserMeal === idx ? null : idx)}
            >
              {Number(meal?.combo_id) > 0 ? 'Change template' : 'Choose template'}
            </button>
            <button type="button" className="client-q-btn secondary" onClick={() => toggleCustomize(customizeKey)}>
              {isOpen ? 'Hide customization' : 'Customize foods'}
            </button>
          </div>
        </div>
        {templateChooserMeal === idx ? (
          <div className="meal-choice-panel">
            {starterLoading ? <p className="client-q-help">Loading templates...</p> : null}
            {!starterLoading && options.length ? (
              <div className="meal-choice-grid">
                {options.map((row) => renderMealTemplateOption(row, idx))}
              </div>
            ) : null}
            {!starterLoading && !options.length ? <p className="client-q-help">No database templates are available for this meal yet.</p> : null}
          </div>
        ) : null}
        {isOpen ? (
          <div className="visual-meal-card__customize">
            {renderMealRow({
              meal,
              mealIndex: idx,
              scopeLabel,
              lookupKey,
              onSlotChange: (mealIndex, slotKey, slotValue) => updateWeeklyMealSlot(activeDay, mealIndex, slotKey, slotValue),
            })}
          </div>
        ) : null}
      </article>
    );
  };

  return (
    <div className="client-q-stack">
      <div className="food-pref-intro">
        <div>
          <h2>Choose your preferred meals</h2>
          <p>Start with database templates, then customize only the foods you care about.</p>
        </div>
        <div className="food-pref-progress">
          <span className={`client-q-chip ${weeklyCompletionSummary.isComplete ? 'ok' : weeklyCompletionSummary.missingMeals ? 'warn' : ''}`}>
            {weeklyCompletionSummary.matchedMeals}/{weeklyCompletionSummary.totalMeals} meals complete
          </span>
          <span className="client-q-chip">{weeklyCompletionSummary.daysComplete}/{weeklyCompletionSummary.totalDays} days complete</span>
        </div>
      </div>
      {optionsError ? <p className="client-q-error">{optionsError}</p> : null}
      {proteinShake?.enabled === true && proteinShake?.counts_as_meal === true ? (
        <div className="client-q-stack" style={{ border: '1px solid rgba(20,40,74,0.1)', borderRadius: 12, padding: '0.75rem' }}>
          <strong>Protein Shake</strong>
          <p className="client-q-help">
            One meal is reserved for a protein shake ({proteinShakePlacementLabel(proteinShake)}). Food meals still need combo selections.
          </p>
        </div>
      ) : null}

      <ProductSearchPicker
        picker={usdaPicker}
        onClose={() => setUsdaPicker({ open: false, canonicalCategory: '', query: '', barcode: '', loading: false, error: '', results: [], notFound: false, imageUploadingId: '' })}
        onQueryChange={(query) => setUsdaPicker((prev) => ({ ...prev, query }))}
        onBarcodeChange={(barcode) => setUsdaPicker((prev) => ({ ...prev, barcode }))}
        onSearch={searchUsdaFoods}
        onBarcodeLookup={lookupBarcode}
        onSelect={saveUsdaOverride}
        onAddImage={uploadProductImage}
      />

      <div className="food-pref-mode-toggle">
          <button
            type="button"
            className={`food-pref-mode ${templatePanelMode === 'template' ? 'is-active' : ''}`}
            onClick={() => setTemplatePanelMode('template')}
          >
            <strong>Template + customization</strong>
            <span>Choose visual meal templates first.</span>
          </button>
          <button
            type="button"
            className={`food-pref-mode ${templatePanelMode === 'custom' ? 'is-active' : ''}`}
            onClick={() => setTemplatePanelMode('custom')}
          >
            <strong>Customization only</strong>
            <span>Manually build each meal from slots.</span>
          </button>
      </div>

      <div className="client-q-stack">
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
                  {dayCompletion[day]?.isComplete ? 'Complete' : `${dayCompletion[day]?.missing || 0} pending`}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {templatePanelMode === 'template' ? (
      <div className="client-q-stack">
        <div className="food-pref-section-title">
          <strong>{prettyDay(activeDay)} templates</strong>
          <span className="client-q-help">Pick a full-day template or choose per meal.</span>
        </div>
        {starterLoading ? (
          <p className="client-q-help">Loading starter templates…</p>
        ) : (
          <div className="meal-template-grid">
            {starterTemplates.map((template) => renderTemplateSummaryCard(template))}
            {!starterTemplates.length ? (
              <p className="client-q-help">No starter templates available yet.</p>
            ) : null}
          </div>
        )}
        <div className="visual-meal-list">
          {(normalized.weekly_days[activeDay] || []).map((meal, idx) => renderSelectedMealCard(meal, idx))}
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
        </div>
      </div>
      ) : null}

      {templatePanelMode === 'custom' ? (
      <div className="client-q-stack">
        <strong>Customization only</strong>
        <p className="client-q-help">Build a default day manually, apply it across the week, then adjust individual days.</p>
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
      </div>
      ) : null}

      <div className="client-q-stack food-pref-saved">
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

      {templatePanelMode === 'custom' ? (
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
        <div className="client-q-stack">
          {(normalized.weekly_days[activeDay] || []).map((meal, idx) =>
            isProteinShakeMeal(meal) ? renderSelectedMealCard(meal, idx) : renderMealRow({
              meal,
              mealIndex: idx,
              scopeLabel: activeDay,
              lookupKey: `weekly:${activeDay}:${idx}`,
              onSlotChange: (mealIndex, slotKey, slotValue) => updateWeeklyMealSlot(activeDay, mealIndex, slotKey, slotValue),
            }))}
        </div>
      </div>
      ) : null}
    </div>
  );
}

export default MealComboBuilderStep;
