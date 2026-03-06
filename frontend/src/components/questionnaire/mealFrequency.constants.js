export const MEAL_SCHEDULE_MODES = {
  same: { key: 'same', label: 'Same every day' },
  custom: { key: 'custom', label: 'Customize by day' },
};

export const MEAL_FREQUENCY_OPTIONS = [3, 4, 5, 6];
export const DEFAULT_MEAL_COUNT = 4;

export const MEAL_SCHEDULE_DAYS = [
  { code: 'mon', label: 'Mon', fullLabel: 'Monday', backendKey: 'monday' },
  { code: 'tue', label: 'Tue', fullLabel: 'Tuesday', backendKey: 'tuesday' },
  { code: 'wed', label: 'Wed', fullLabel: 'Wednesday', backendKey: 'wednesday' },
  { code: 'thu', label: 'Thu', fullLabel: 'Thursday', backendKey: 'thursday' },
  { code: 'fri', label: 'Fri', fullLabel: 'Friday', backendKey: 'friday' },
  { code: 'sat', label: 'Sat', fullLabel: 'Saturday', backendKey: 'saturday' },
  { code: 'sun', label: 'Sun', fullLabel: 'Sunday', backendKey: 'sunday' },
];

export function normalizeMealFrequencyMode(value) {
  const mode = String(value || '').trim().toLowerCase();
  return mode === 'custom' ? 'custom' : 'same';
}

export function normalizeMealCount(value, fallback = DEFAULT_MEAL_COUNT) {
  const parsed = Number(value);
  return MEAL_FREQUENCY_OPTIONS.includes(parsed) ? parsed : fallback;
}

export function normalizeMealFrequencyValue(value) {
  const mode = normalizeMealFrequencyMode(value?.mode);
  const defaultMeals = normalizeMealCount(value?.defaultMeals ?? value?.default_meals, DEFAULT_MEAL_COUNT);

  const days = MEAL_SCHEDULE_DAYS.reduce((acc, day) => {
    const raw = value?.days?.[day.code] ?? value?.days?.[day.backendKey] ?? defaultMeals;
    acc[day.code] = normalizeMealCount(raw, defaultMeals);
    return acc;
  }, {});

  return {
    mode,
    defaultMeals,
    days,
  };
}

export function getMealFrequencyGuidance(dailyCalories) {
  const calories = Number(dailyCalories);
  if (!Number.isFinite(calories)) {
    return 'Most users feel best with a meal pattern they can consistently follow each day.';
  }
  if (calories < 1600) {
    return 'For your current calorie target, 3-4 meals usually feels most practical.';
  }
  if (calories <= 2400) {
    return 'For your current calorie target, 3-5 meals is usually the most balanced range.';
  }
  return 'For your current calorie target, 4-6 meals can help keep portions more manageable.';
}

export function getMealFrequencyRecommendation(calorieTarget, mealCount) {
  const calories = Number(calorieTarget);
  if (!Number.isFinite(calories)) {
    return {
      level: 'neutral',
      tag: '',
      helperText: '',
    };
  }

  if (calories < 1600) {
    if (mealCount === 3 || mealCount === 4) {
      return {
        level: 'recommended',
        tag: 'Recommended',
        helperText: 'Usually practical for lower calorie targets.',
      };
    }
    return {
      level: 'less_practical',
      tag: 'Less practical',
      helperText: 'This may create meals that are too small to feel practical.',
    };
  }

  if (calories <= 2400) {
    if (mealCount >= 3 && mealCount <= 5) {
      return {
        level: 'recommended',
        tag: 'Recommended',
        helperText: 'Usually a practical split for this calorie range.',
      };
    }
    return {
      level: 'less_practical',
      tag: 'Less practical',
      helperText: 'Six meals may feel harder to sustain in this range.',
    };
  }

  if (mealCount >= 4 && mealCount <= 6) {
    return {
      level: 'recommended',
      tag: 'Recommended',
      helperText: 'Can help distribute larger calorie targets realistically.',
    };
  }

  return {
    level: 'neutral',
    tag: '',
    helperText: 'May require larger meals than some users prefer.',
  };
}

export function averageMealsPerDay(days = {}) {
  const values = MEAL_SCHEDULE_DAYS.map((day) => Number(days[day.code]));
  const valid = values.filter((value) => MEAL_FREQUENCY_OPTIONS.includes(value));
  if (!valid.length) return DEFAULT_MEAL_COUNT;
  const sum = valid.reduce((acc, value) => acc + value, 0);
  return Math.round((sum / valid.length) * 10) / 10;
}
