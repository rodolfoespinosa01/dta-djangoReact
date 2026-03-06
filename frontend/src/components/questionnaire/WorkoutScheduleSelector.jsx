import React, { useMemo, useState } from 'react';
import {
  WORKOUT_DAYS,
  WORKOUT_SCHEDULE_MODES,
  defaultTrainingDaysForMode,
  normalizeWorkoutScheduleValue,
} from './workoutSchedule.constants';
import './WorkoutScheduleSelector.css';

function WorkoutScheduleSelector({
  value,
  onChange,
}) {
  const normalized = useMemo(() => normalizeWorkoutScheduleValue(value), [value]);
  const { scheduleMode, trainingDays } = normalized;
  const [selectionError, setSelectionError] = useState('');

  const trainingCount = trainingDays.length;
  const offDaysCount = Math.max(0, 7 - trainingCount);

  const emitChange = (nextMode, nextDays) => {
    if (!onChange) return;
    onChange({
      scheduleMode: nextMode,
      trainingDays: nextDays,
    });
  };

  const handleModeChange = (nextMode) => {
    setSelectionError('');
    if (nextMode === 'everyday') {
      emitChange('everyday', defaultTrainingDaysForMode('everyday'));
      return;
    }
    if (nextMode === 'weekdays') {
      emitChange('weekdays', defaultTrainingDaysForMode('weekdays'));
      return;
    }

    const nextDays = trainingDays.length ? trainingDays : ['mon'];
    emitChange('custom', nextDays);
  };

  const toggleDay = (dayCode) => {
    const isActive = trainingDays.includes(dayCode);

    if (isActive && trainingDays.length === 1) {
      setSelectionError('Choose at least 1 training day in Custom mode.');
      return;
    }

    setSelectionError('');
    const nextDays = isActive
      ? trainingDays.filter((code) => code !== dayCode)
      : [...trainingDays, dayCode];

    emitChange('custom', nextDays);
  };

  return (
    <section className="wk-schedule-card" aria-label="Workout schedule selector">
      <header className="wk-schedule-header">
        <h3>What does your workout schedule look like?</h3>
        <p>
          Your meal plan is based on workout days versus off days. This helps us assign the right calorie totals and
          macro splits depending on whether you are training or resting.
        </p>
      </header>

      <div className="wk-schedule-mode-grid" role="radiogroup" aria-label="Schedule mode">
        {Object.values(WORKOUT_SCHEDULE_MODES).map((mode) => {
          const isSelected = scheduleMode === mode.key;
          return (
            <button
              key={mode.key}
              type="button"
              role="radio"
              aria-checked={isSelected}
              className={`wk-schedule-mode ${isSelected ? 'is-selected' : ''}`}
              onClick={() => handleModeChange(mode.key)}
            >
              <div className="wk-schedule-mode-top">
                <strong>{mode.label}</strong>
                <span className="wk-schedule-badge">{mode.badge}</span>
              </div>
              <p>{mode.description}</p>
            </button>
          );
        })}
      </div>

      <div className="wk-schedule-days" aria-label="Training days">
        {WORKOUT_DAYS.map((day) => {
          const isActive = trainingDays.includes(day.code);
          return (
            <button
              key={day.code}
              type="button"
              className={`wk-schedule-day ${isActive ? 'is-active' : ''}`}
              onClick={() => toggleDay(day.code)}
              aria-pressed={isActive}
              aria-label={`${day.fullLabel} ${isActive ? 'selected' : 'not selected'}`}
            >
              {day.label}
            </button>
          );
        })}
      </div>

      {selectionError ? (
        <p className="wk-schedule-error" role="alert">{selectionError}</p>
      ) : null}

      <div className="wk-schedule-summary" aria-live="polite">
        <p><strong>Training days:</strong> {trainingCount}</p>
        <p><strong>Off days:</strong> {offDaysCount}</p>
        <p><strong>Why it matters:</strong> We use this to assign workout-day and rest-day calories and macro splits.</p>
      </div>
    </section>
  );
}

export default WorkoutScheduleSelector;
