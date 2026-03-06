export const TRAINING_TIMING_MODES = {
  same: { key: 'same', label: 'Same every training day' },
  custom: { key: 'custom', label: 'Customize by day' },
};

export const TIMING_WEEK_DAYS = [
  { code: 'mon', label: 'Mon', fullLabel: 'Monday' },
  { code: 'tue', label: 'Tue', fullLabel: 'Tuesday' },
  { code: 'wed', label: 'Wed', fullLabel: 'Wednesday' },
  { code: 'thu', label: 'Thu', fullLabel: 'Thursday' },
  { code: 'fri', label: 'Fri', fullLabel: 'Friday' },
  { code: 'sat', label: 'Sat', fullLabel: 'Saturday' },
  { code: 'sun', label: 'Sun', fullLabel: 'Sunday' },
];

export function normalizeTrainingTimingMode(value) {
  return String(value || '').trim().toLowerCase() === 'custom' ? 'custom' : 'same';
}

export function normalizeMealCount(value, fallback = 3) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(1, Math.round(parsed));
}

export function getValidBeforeMealOptions(mealCount) {
  const count = normalizeMealCount(mealCount, 1);
  return Array.from({ length: count }, (_, idx) => idx + 1);
}

export function getValidTrainingSlots(mealCount) {
  const count = normalizeMealCount(mealCount, 1);
  return Array.from({ length: count }, (_, idx) => idx);
}

export function slotIndexToBeforeMeal(slotIndex) {
  const parsed = Number(slotIndex);
  if (!Number.isFinite(parsed)) return 1;
  return Math.max(1, Math.round(parsed) + 1);
}

export function beforeMealToSlotIndex(beforeMeal) {
  const parsed = Number(beforeMeal);
  if (!Number.isFinite(parsed)) return 0;
  return Math.max(0, Math.round(parsed) - 1);
}

export function clampBeforeMeal(beforeMeal, mealCount) {
  const max = normalizeMealCount(mealCount, 1);
  const parsed = Number(beforeMeal);
  if (!Number.isFinite(parsed)) return 1;
  return Math.max(1, Math.min(max, Math.round(parsed)));
}

export function getSharedValidSlots(trainingDays = [], mealScheduleByDay = {}) {
  const validMealCounts = trainingDays
    .map((dayCode) => normalizeMealCount(mealScheduleByDay?.[dayCode], 0))
    .filter((count) => count > 0);

  if (!validMealCounts.length) return [];
  const sharedMax = Math.min(...validMealCounts);
  return getValidTrainingSlots(sharedMax);
}

export function getSharedBeforeMealOptions(trainingDays = [], mealScheduleByDay = {}) {
  return getSharedValidSlots(trainingDays, mealScheduleByDay).map(slotIndexToBeforeMeal);
}

export function normalizeTrainingTimingValue({
  value,
  trainingDays = [],
  mealScheduleByDay = {},
}) {
  const trainingSet = new Set(trainingDays);
  const mode = normalizeTrainingTimingMode(value?.mode);
  const sharedValidSlots = getSharedValidSlots(trainingDays, mealScheduleByDay);
  const sharedOptions = sharedValidSlots.map(slotIndexToBeforeMeal);

  let sameBeforeMeal = Number(value?.sameBeforeMeal);
  if (!Number.isFinite(sameBeforeMeal)) {
    sameBeforeMeal = sharedOptions[0] || null;
  }
  if (sameBeforeMeal != null && sharedValidSlots.length) {
    const sameSlot = beforeMealToSlotIndex(sameBeforeMeal);
    const maxSharedSlot = sharedValidSlots[sharedValidSlots.length - 1];
    sameBeforeMeal = slotIndexToBeforeMeal(Math.max(0, Math.min(maxSharedSlot, sameSlot)));
  }

  const days = TIMING_WEEK_DAYS.reduce((acc, day) => {
    if (!trainingSet.has(day.code)) {
      acc[day.code] = null;
      return acc;
    }

    const mealCount = normalizeMealCount(mealScheduleByDay?.[day.code], 1);
    const fromDays = Number(value?.days?.[day.code]);
    const base = Number.isFinite(fromDays)
      ? fromDays
      : (mode === 'same' && Number.isFinite(sameBeforeMeal) ? sameBeforeMeal : 1);

    acc[day.code] = clampBeforeMeal(base, mealCount);
    return acc;
  }, {});

  return {
    mode,
    sameBeforeMeal,
    days,
  };
}

export function buildTrainingMealTimeline({ mealCount, beforeMeal }) {
  const count = normalizeMealCount(mealCount, 1);
  const before = clampBeforeMeal(beforeMeal, count);
  const items = [];

  for (let mealNum = 1; mealNum <= count; mealNum += 1) {
    if (mealNum === before) {
      items.push({
        id: `train-before-${mealNum}`,
        type: 'training',
        label: 'Train',
        beforeMeal: mealNum,
      });
    }

    items.push({
      id: `meal-${mealNum}`,
      type: 'meal',
      label: `Meal ${mealNum}`,
      mealNumber: mealNum,
    });
  }

  return items;
}

export function buildTimelineItems({
  mealCount,
  trainingSlotIndex,
  gender,
  imagePools = {},
  daySeed = 0,
}) {
  const count = normalizeMealCount(mealCount, 1);
  const validSlots = getValidTrainingSlots(count);
  const maxSlot = validSlots.length ? validSlots[validSlots.length - 1] : 0;
  const slot = Math.max(0, Math.min(maxSlot, Number(trainingSlotIndex) || 0));
  const mealPool = imagePools?.meal || [];
  const trainingPool = imagePools?.training || [];
  const items = [];

  for (let idx = 0; idx < count; idx += 1) {
    const slotIndex = idx;
    const mealNumber = idx + 1;
    const mealImage = mealPool.length ? mealPool[(daySeed + idx) % mealPool.length] : '';
    const trainingImage = trainingPool.length ? trainingPool[(daySeed + idx) % trainingPool.length] : '';

    items.push({
      id: `slot-${slotIndex}`,
      type: 'slot',
      slotIndex,
      beforeMeal: slotIndexToBeforeMeal(slotIndex),
      isTrainingHere: slotIndex === slot,
      trainingImage,
      gender,
    });

    items.push({
      id: `meal-${mealNumber}`,
      type: 'meal',
      mealNumber,
      image: mealImage,
    });
  }

  return items;
}
