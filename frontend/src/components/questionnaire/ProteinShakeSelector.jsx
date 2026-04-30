import React, { useMemo } from 'react';

export const PROTEIN_SHAKE_TIMING_OPTIONS = {
  pre_workout: { key: 'pre_workout', label: 'Pre-workout' },
  post_workout: { key: 'post_workout', label: 'Post-workout' },
  other: { key: 'other', label: 'Other' },
};

export const PROTEIN_SHAKE_WEEK_DAYS = [
  { code: 'sunday', label: 'Sun', fullLabel: 'Sunday' },
  { code: 'monday', label: 'Mon', fullLabel: 'Monday' },
  { code: 'tuesday', label: 'Tue', fullLabel: 'Tuesday' },
  { code: 'wednesday', label: 'Wed', fullLabel: 'Wednesday' },
  { code: 'thursday', label: 'Thu', fullLabel: 'Thursday' },
  { code: 'friday', label: 'Fri', fullLabel: 'Friday' },
  { code: 'saturday', label: 'Sat', fullLabel: 'Saturday' },
];

function normalizeMealCount(value, fallback = 3) {
  const parsed = Number(value);
  return [3, 4, 5, 6].includes(parsed) ? parsed : fallback;
}

function mealCountForDay(mealSchedule, day) {
  return normalizeMealCount(mealSchedule?.days?.[day], 3);
}

function clampMeal(value, mealCount) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 1;
  return Math.max(1, Math.min(normalizeMealCount(mealCount, 3), Math.round(parsed)));
}

function trainingMealForDay(trainingSchedule, day) {
  const match = /^before_meal_(\d+)$/.exec(String(trainingSchedule?.[day] || '').trim().toLowerCase());
  return match ? Number(match[1]) : null;
}

function normalizeTiming(value) {
  const timing = String(value || '').trim();
  return Object.prototype.hasOwnProperty.call(PROTEIN_SHAKE_TIMING_OPTIONS, timing) ? timing : 'other';
}

function legacyTiming(value = {}) {
  if (value.mode === 'extra_shake') {
    const timingMode = String(value.timing_mode || '').trim();
    if (timingMode === 'pre_workout') return 'pre_workout';
    if (timingMode === 'post_workout' || timingMode === 'recommended') return 'post_workout';
    return 'other';
  }
  return normalizeTiming(value.placement_mode || value.default_timing);
}

function deriveDaySelection({ timing, selectedMeal, mealSchedule, trainingSchedule, day, enabled }) {
  const mealCount = mealCountForDay(mealSchedule, day);
  const trainingMeal = trainingMealForDay(trainingSchedule, day);
  if (!trainingMeal && (timing === 'pre_workout' || timing === 'post_workout')) {
    return enabled === true
      ? { enabled: true, timing: 'other', selected_meal: 1 }
      : { enabled: false, timing: 'other', selected_meal: 1 };
  }
  if (enabled === false) return { enabled: false, timing: 'other', selected_meal: 1 };
  if (timing === 'post_workout') {
    return { enabled: true, timing, selected_meal: clampMeal(trainingMeal, mealCount) };
  }
  if (timing === 'pre_workout') {
    return { enabled: true, timing, selected_meal: clampMeal(Math.max(1, trainingMeal - 1), mealCount) };
  }
  return { enabled: true, timing: 'other', selected_meal: clampMeal(selectedMeal, mealCount) };
}

export function normalizeProteinShakeValue(value, { mealSchedule, trainingSchedule } = {}) {
  if (!value || typeof value !== 'object' || value.enabled !== true) {
    return {
      enabled: false,
      counts_as_meal: true,
    };
  }

  const hasNewShape = value.schedule_mode || value.days || value.default_timing;
  const explicitScheduleMode = String(value.schedule_mode || '').trim();
  const scheduleMode = explicitScheduleMode === 'custom' || (!hasNewShape && value.selected_meals_by_day) ? 'custom' : 'same';
  const defaultTiming = hasNewShape ? normalizeTiming(value.default_timing) : legacyTiming(value);
  const legacySelectedByDay = value.selected_meals_by_day || {};
  const defaultSelectedMeal = clampMeal(value.default_selected_meal ?? value.selected_meal ?? 1, 6);
  const rawDays = value.days && typeof value.days === 'object' ? value.days : {};
  const hasLegacyByDay = !hasNewShape && value.selected_meals_by_day;

  const days = PROTEIN_SHAKE_WEEK_DAYS.reduce((acc, day) => {
    const rawDay = rawDays[day.code] && typeof rawDays[day.code] === 'object' ? rawDays[day.code] : {};
    const trainingMeal = trainingMealForDay(trainingSchedule, day.code);
    const timing = scheduleMode === 'custom'
      ? normalizeTiming(rawDay.timing || legacyTiming({ placement_mode: value.placement_mode }))
      : defaultTiming;
    const selectedMeal = scheduleMode === 'custom'
      ? rawDay.selected_meal ?? legacySelectedByDay[day.code] ?? defaultSelectedMeal
      : defaultSelectedMeal;
    const enabled = scheduleMode === 'custom'
      ? rawDay.enabled ?? Boolean(trainingMeal || hasLegacyByDay)
      : (defaultTiming === 'other' || Boolean(trainingMeal));
    acc[day.code] = deriveDaySelection({
      timing,
      selectedMeal,
      mealSchedule,
      trainingSchedule,
      day: day.code,
      enabled,
    });
    return acc;
  }, {});

  const selectedMealSourceDay = PROTEIN_SHAKE_WEEK_DAYS.find((day) => trainingMealForDay(trainingSchedule, day.code))
    || PROTEIN_SHAKE_WEEK_DAYS[0];

  return {
    enabled: true,
    counts_as_meal: true,
    schedule_mode: scheduleMode,
    default_timing: defaultTiming,
    default_selected_meal: clampMeal(defaultSelectedMeal, mealCountForDay(mealSchedule, selectedMealSourceDay.code)),
    days,
    // Legacy fields remain for older consumers until every downstream reader uses days.
    placement_mode: scheduleMode === 'same' ? defaultTiming : 'other',
    selected_meal: days[selectedMealSourceDay.code]?.selected_meal || 1,
    selected_meals_by_day: PROTEIN_SHAKE_WEEK_DAYS.reduce((acc, day) => {
      if (days[day.code]?.enabled) acc[day.code] = days[day.code]?.selected_meal || 1;
      return acc;
    }, {}),
  };
}

function mealOptionsForDay(mealSchedule, day) {
  const mealCount = mealCountForDay(mealSchedule, day);
  return Array.from({ length: mealCount }, (_, idx) => idx + 1);
}

function SummaryDay({ day, mealCount, trainingMeal, shakeDay }) {
  const rows = [];
  for (let mealNumber = 1; mealNumber <= mealCount; mealNumber += 1) {
    if (trainingMeal === mealNumber) {
      rows.push(<span key={`${day.code}-workout-${mealNumber}`} className="client-q-chip warn">Workout</span>);
    }
    rows.push(
      <span key={`${day.code}-meal-${mealNumber}`} className={`client-q-chip ${shakeDay?.enabled && shakeDay?.selected_meal === mealNumber ? 'ok' : ''}`}>
        Meal {mealNumber}: {shakeDay?.enabled && shakeDay?.selected_meal === mealNumber ? 'Protein Shake' : 'Food'}
      </span>
    );
  }
  return (
    <div className="client-q-stack" style={{ border: '1px solid rgba(20,40,74,0.1)', borderRadius: 12, padding: '0.75rem' }}>
      <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <strong>{day.fullLabel}</strong>
        <span className="client-q-chip">{mealCount} meals</span>
        <span className="client-q-chip">{trainingMeal ? `Workout before Meal ${trainingMeal}` : 'No workout'}</span>
        <span className={`client-q-chip ${shakeDay?.enabled ? 'ok' : ''}`}>
          {shakeDay?.enabled ? `Shake: Meal ${shakeDay?.selected_meal || 1}` : 'No shake'}
        </span>
      </div>
      <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>{rows}</div>
      {!trainingMeal && !shakeDay?.enabled ? (
        <p className="client-q-help">No protein shake is included on this off day unless you customize this day and add one.</p>
      ) : null}
    </div>
  );
}

function TimingControls({ timing, onTimingChange, selectedMeal, onMealChange, mealSchedule, trainingSchedule, dayCode = null, enabled = true, onEnabledChange = null }) {
  const trainingMeal = dayCode ? trainingMealForDay(trainingSchedule, dayCode) : null;
  const mealOptions = dayCode ? mealOptionsForDay(mealSchedule, dayCode) : Array.from({
    length: Math.max(...PROTEIN_SHAKE_WEEK_DAYS.map((day) => mealCountForDay(mealSchedule, day.code))),
  }, (_, idx) => idx + 1);
  const forceManual = dayCode && !trainingMeal;
  return (
    <div className="client-q-stack">
      {dayCode ? (
        <div className="client-q-toggle">
          <button type="button" className={enabled ? 'is-active' : ''} onClick={() => onEnabledChange?.(true)}>
            Include shake
          </button>
          <button type="button" className={!enabled ? 'is-active' : ''} onClick={() => onEnabledChange?.(false)}>
            No shake
          </button>
        </div>
      ) : null}
      {!enabled ? (
        <p className="client-q-help">No protein shake will be included for this day.</p>
      ) : null}
      {enabled ? (
      <>
      <div className="client-q-toggle">
        {Object.values(PROTEIN_SHAKE_TIMING_OPTIONS).map((option) => (
          <button
            key={`${dayCode || 'same'}-${option.key}`}
            type="button"
            className={timing === option.key ? 'is-active' : ''}
            onClick={() => onTimingChange(option.key)}
            disabled={forceManual && option.key !== 'other'}
          >
            {option.label}
          </button>
        ))}
      </div>
      {forceManual ? (
        <p className="client-q-help">No workout is scheduled for this day, so choose a meal manually.</p>
      ) : null}
      {timing === 'other' || forceManual ? (
        <div className="client-q-card-grid">
          {mealOptions.map((mealNumber) => (
            <button
              key={`${dayCode || 'same'}-shake-meal-${mealNumber}`}
              type="button"
              className={`client-q-option-card ${Number(selectedMeal) === mealNumber ? 'is-active' : ''}`}
              onClick={() => onMealChange(mealNumber)}
            >
              <span>Meal {mealNumber}</span>
            </button>
          ))}
        </div>
      ) : null}
      </>
      ) : null}
    </div>
  );
}

function ProteinShakeSelector({ value, mealSchedule, trainingSchedule, onChange }) {
  const normalized = useMemo(
    () => normalizeProteinShakeValue(value, { mealSchedule, trainingSchedule }),
    [value, mealSchedule, trainingSchedule]
  );

  const emit = (nextValue) => {
    if (!onChange) return;
    onChange(normalizeProteinShakeValue(nextValue, { mealSchedule, trainingSchedule }));
  };

  const setEnabled = (enabled) => {
    if (!enabled) {
      emit({ enabled: false, counts_as_meal: true });
      return;
    }
    emit({
      enabled: true,
      counts_as_meal: true,
      schedule_mode: 'same',
      default_timing: 'post_workout',
      default_selected_meal: 1,
    });
  };

  const updateDefaultTiming = (timing) => {
    emit({ ...normalized, schedule_mode: 'same', default_timing: timing });
  };

  const updateDefaultMeal = (mealNumber) => {
    emit({ ...normalized, schedule_mode: 'same', default_timing: 'other', default_selected_meal: mealNumber });
  };

  const updateDay = (dayCode, patch) => {
    emit({
      ...normalized,
      schedule_mode: 'custom',
      days: {
        ...(normalized.days || {}),
        [dayCode]: {
          ...(normalized.days?.[dayCode] || { enabled: true, timing: 'other', selected_meal: 1 }),
          ...patch,
        },
      },
    });
  };

  return (
    <section className="client-q-stack" aria-label="Protein shake selector">
      <div className="client-q-stack">
        <h3>Would you like one of your meals to be a protein shake?</h3>
      </div>

      <div className="client-q-card-grid">
        <button type="button" className={`client-q-option-card ${normalized.enabled ? '' : 'is-active'}`} onClick={() => setEnabled(false)}>
          <span>No, all meals are food meals</span>
        </button>
        <button type="button" className={`client-q-option-card ${normalized.enabled ? 'is-active' : ''}`} onClick={() => setEnabled(true)}>
          <span>Yes, replace one meal with a protein shake</span>
        </button>
      </div>

      {normalized.enabled ? (
        <div className="client-q-stack">
          <div className="client-q-stack">
            <strong>When would you like your protein shake?</strong>
            <p className="client-q-help">The shake counts as one of your selected meals.</p>
          </div>

          <div className="client-q-toggle">
            <button
              type="button"
              className={normalized.schedule_mode === 'same' ? 'is-active' : ''}
              onClick={() => emit({ ...normalized, schedule_mode: 'same' })}
            >
              Same every day
            </button>
            <button
              type="button"
              className={normalized.schedule_mode === 'custom' ? 'is-active' : ''}
              onClick={() => emit({ ...normalized, schedule_mode: 'custom' })}
            >
              Customize by day
            </button>
          </div>

          {normalized.schedule_mode === 'same' ? (
            <div className="client-q-stack">
              <strong>Same timing for the week</strong>
              <TimingControls
                timing={normalized.default_timing}
                onTimingChange={updateDefaultTiming}
                selectedMeal={normalized.default_selected_meal}
                onMealChange={updateDefaultMeal}
                mealSchedule={mealSchedule}
                trainingSchedule={trainingSchedule}
              />
            </div>
          ) : (
            <div className="client-q-stack">
              {PROTEIN_SHAKE_WEEK_DAYS.map((day) => (
                <div key={`shake-day-${day.code}`} className="client-q-stack" style={{ border: '1px solid rgba(20,40,74,0.1)', borderRadius: 12, padding: '0.75rem' }}>
                  <strong>{day.fullLabel}</strong>
                  <TimingControls
                    timing={normalized.days?.[day.code]?.timing || 'other'}
                    onTimingChange={(timing) => updateDay(day.code, { timing })}
                    selectedMeal={normalized.days?.[day.code]?.selected_meal || 1}
                    onMealChange={(mealNumber) => updateDay(day.code, { timing: 'other', selected_meal: mealNumber })}
                    mealSchedule={mealSchedule}
                    trainingSchedule={trainingSchedule}
                    dayCode={day.code}
                    enabled={normalized.days?.[day.code]?.enabled !== false}
                    onEnabledChange={(enabled) => updateDay(day.code, { enabled, timing: enabled ? (normalized.days?.[day.code]?.timing || 'other') : 'other' })}
                  />
                </div>
              ))}
            </div>
          )}

          <div className="client-q-stack">
            <strong>Weekly structure</strong>
            {PROTEIN_SHAKE_WEEK_DAYS.map((day) => (
              <SummaryDay
                key={`shake-summary-${day.code}`}
                day={day}
                mealCount={mealCountForDay(mealSchedule, day.code)}
                trainingMeal={trainingMealForDay(trainingSchedule, day.code)}
                shakeDay={normalized.days?.[day.code]}
              />
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

export default ProteinShakeSelector;
