export const WORKOUT_SCHEDULE_MODES = {
  weekdays: {
    key: 'weekdays',
    label: 'Weekdays',
    badge: 'Mon-Fri',
    description: 'Train on Monday through Friday.',
  },
  everyday: {
    key: 'everyday',
    label: 'Everyday',
    badge: '7 days',
    description: 'Train every day of the week.',
  },
  custom: {
    key: 'custom',
    label: 'Custom',
    badge: 'Build your own',
    description: 'Choose any combination of days.',
  },
};

export const WORKOUT_DAYS = [
  { code: 'mon', label: 'Mon', fullLabel: 'Monday', backendKey: 'monday' },
  { code: 'tue', label: 'Tue', fullLabel: 'Tuesday', backendKey: 'tuesday' },
  { code: 'wed', label: 'Wed', fullLabel: 'Wednesday', backendKey: 'wednesday' },
  { code: 'thu', label: 'Thu', fullLabel: 'Thursday', backendKey: 'thursday' },
  { code: 'fri', label: 'Fri', fullLabel: 'Friday', backendKey: 'friday' },
  { code: 'sat', label: 'Sat', fullLabel: 'Saturday', backendKey: 'saturday' },
  { code: 'sun', label: 'Sun', fullLabel: 'Sunday', backendKey: 'sunday' },
];

export const WEEKDAY_CODES = ['mon', 'tue', 'wed', 'thu', 'fri'];
export const EVERYDAY_CODES = WORKOUT_DAYS.map((day) => day.code);

export const WORKOUT_CODE_TO_BACKEND_DAY = WORKOUT_DAYS.reduce((acc, day) => {
  acc[day.code] = day.backendKey;
  return acc;
}, {});

export const BACKEND_DAY_TO_WORKOUT_CODE = WORKOUT_DAYS.reduce((acc, day) => {
  acc[day.backendKey] = day.code;
  return acc;
}, {});

export function normalizeScheduleMode(value) {
  const mode = String(value || '').trim().toLowerCase();
  if (mode === 'weekdays' || mode === 'everyday' || mode === 'custom') return mode;
  return 'weekdays';
}

export function normalizeTrainingDays(value) {
  const list = Array.isArray(value) ? value : [];
  const validCodes = new Set(EVERYDAY_CODES);
  const seen = new Set();

  return list
    .map((item) => String(item || '').trim().toLowerCase())
    .filter((code) => validCodes.has(code) && !seen.has(code) && seen.add(code));
}

export function inferScheduleMode(trainingDays = []) {
  const sorted = [...normalizeTrainingDays(trainingDays)].sort();
  const weekdaysSorted = [...WEEKDAY_CODES].sort();
  const everydaySorted = [...EVERYDAY_CODES].sort();

  if (sorted.length === everydaySorted.length && sorted.every((code, idx) => code === everydaySorted[idx])) {
    return 'everyday';
  }
  if (sorted.length === weekdaysSorted.length && sorted.every((code, idx) => code === weekdaysSorted[idx])) {
    return 'weekdays';
  }
  return 'custom';
}

export function defaultTrainingDaysForMode(mode) {
  if (mode === 'everyday') return [...EVERYDAY_CODES];
  if (mode === 'weekdays') return [...WEEKDAY_CODES];
  return [...WEEKDAY_CODES];
}

export function normalizeWorkoutScheduleValue(value) {
  const rawDays = normalizeTrainingDays(value?.trainingDays);
  const scheduleMode = normalizeScheduleMode(value?.scheduleMode || inferScheduleMode(rawDays));
  const trainingDays = rawDays.length ? rawDays : defaultTrainingDaysForMode(scheduleMode);

  return {
    scheduleMode,
    trainingDays,
  };
}
