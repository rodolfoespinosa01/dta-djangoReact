import React, { useMemo, useState } from 'react';
import mealFemale1 from '../../assets/questionnaire/8/meal-female-1.jpg';
import mealFemale2 from '../../assets/questionnaire/8/meal-female-2.jpg';
import mealFemale3 from '../../assets/questionnaire/8/meal-female-3.jpg';
import mealMale1 from '../../assets/questionnaire/8/meal-male-1.jpg';
import mealMale2 from '../../assets/questionnaire/8/meal-male-2.jpg';
import mealMale3 from '../../assets/questionnaire/8/meal-male-3.png';
import trainingFemale1 from '../../assets/questionnaire/8/training-female-1.png';
import trainingFemale2 from '../../assets/questionnaire/8/training-female-2.png';
import trainingFemale3 from '../../assets/questionnaire/8/training-female-3.png';
import trainingFemale4 from '../../assets/questionnaire/8/training-female-4.png';
import trainingMale1 from '../../assets/questionnaire/8/training-male-1.png';
import trainingMale2 from '../../assets/questionnaire/8/training-male-2.png';
import trainingMale3 from '../../assets/questionnaire/8/training-male-3.png';
import trainingMale4 from '../../assets/questionnaire/8/training-male-4.png';
import {
  TRAINING_TIMING_MODES,
  TIMING_WEEK_DAYS,
  beforeMealToSlotIndex,
  buildTimelineItems,
  getSharedValidSlots,
  getValidTrainingSlots,
  normalizeMealCount,
  normalizeTrainingTimingValue,
  slotIndexToBeforeMeal,
} from './trainingMealTiming.constants';
import './TrainingMealTimingSelector.css';

const MEAL_IMAGE_POOLS = {
  female: [mealFemale1, mealFemale2, mealFemale3],
  male: [mealMale1, mealMale2, mealMale3],
};

const TRAINING_IMAGE_POOLS = {
  female: [trainingFemale1, trainingFemale2, trainingFemale3, trainingFemale4],
  male: [trainingMale1, trainingMale2, trainingMale3, trainingMale4],
};

function pickCycledImage(pool = [], index = 0) {
  if (!pool.length) return '';
  return pool[index % pool.length];
}

function TrainingMealTimingSelector({
  gender = 'male',
  trainingDays = [],
  mealScheduleByDay = {},
  value,
  onChange,
}) {
  const normalizedGender = gender === 'female' ? 'female' : 'male';
  const mealImagePool = MEAL_IMAGE_POOLS[normalizedGender] || MEAL_IMAGE_POOLS.male;
  const trainingImagePool = TRAINING_IMAGE_POOLS[normalizedGender] || TRAINING_IMAGE_POOLS.male;
  const [dragging, setDragging] = useState(null);
  const [hoveredSlotKey, setHoveredSlotKey] = useState('');

  const normalized = useMemo(
    () => normalizeTrainingTimingValue({ value, trainingDays, mealScheduleByDay }),
    [value, trainingDays, mealScheduleByDay]
  );

  const { mode, sameBeforeMeal, days } = normalized;
  const sharedValidSlots = getSharedValidSlots(trainingDays, mealScheduleByDay);
  const selectedSameSlot = beforeMealToSlotIndex(sameBeforeMeal || 1);

  const restDays = useMemo(
    () => TIMING_WEEK_DAYS.filter((day) => !trainingDays.includes(day.code)),
    [trainingDays]
  );

  const emitChange = (nextValue) => {
    if (!onChange) return;
    onChange(nextValue);
  };

  const setMode = (nextMode) => {
    if (nextMode === mode) return;

    if (nextMode === 'same') {
      if (!sharedValidSlots.length) {
        emitChange({ ...normalized, mode: 'same' });
        return;
      }

      const currentDaySlots = trainingDays
        .map((dayCode) => beforeMealToSlotIndex(days?.[dayCode]))
        .filter((slotIndex) => Number.isFinite(slotIndex));

      const maxSharedSlot = sharedValidSlots[sharedValidSlots.length - 1];
      const lowestExistingSlot = currentDaySlots.length ? Math.min(...currentDaySlots) : sharedValidSlots[0];
      const safeSharedSlot = Math.max(0, Math.min(maxSharedSlot, lowestExistingSlot));
      const nextBeforeMeal = slotIndexToBeforeMeal(safeSharedSlot);
      const nextDays = { ...days };

      trainingDays.forEach((dayCode) => {
        const dayMealCount = normalizeMealCount(mealScheduleByDay?.[dayCode], 1);
        // If meal counts change, clamp to the nearest earlier valid position to keep training in range.
        nextDays[dayCode] = Math.min(nextBeforeMeal, dayMealCount);
      });

      emitChange({
        mode: 'same',
        sameBeforeMeal: nextBeforeMeal,
        days: nextDays,
      });
      return;
    }

    emitChange({ ...normalized, mode: nextMode });
  };

  const setSameSlot = (slotIndex) => {
    const beforeMeal = slotIndexToBeforeMeal(slotIndex);
    const nextDays = { ...days };

    trainingDays.forEach((dayCode) => {
      const dayMealCount = normalizeMealCount(mealScheduleByDay?.[dayCode], 1);
      // If meal counts change, clamp to the nearest earlier valid position to keep training in range.
      nextDays[dayCode] = Math.min(beforeMeal, dayMealCount);
    });

    emitChange({
      mode: 'same',
      sameBeforeMeal: beforeMeal,
      days: nextDays,
    });
  };

  const setDaySlot = (dayCode, slotIndex) => {
    const mealCount = normalizeMealCount(mealScheduleByDay?.[dayCode], 1);
    const validSlots = getValidTrainingSlots(mealCount);
    const maxSlot = validSlots[validSlots.length - 1] || 0;
    const safeSlot = Math.max(0, Math.min(maxSlot, slotIndex));
    const beforeMeal = slotIndexToBeforeMeal(safeSlot);

    emitChange({
      ...normalized,
      mode: 'custom',
      days: {
        ...days,
        [dayCode]: beforeMeal,
      },
    });
  };

  const applySlotSelection = (dayCode, slotIndex) => {
    if (mode === 'same') {
      if (sharedValidSlots.includes(slotIndex)) {
        setSameSlot(slotIndex);
      }
      return;
    }
    setDaySlot(dayCode, slotIndex);
  };

  const onTrainingDragStart = (event, dayCode) => {
    event.dataTransfer.effectAllowed = 'move';
    try {
      event.dataTransfer.setData('text/plain', dayCode);
    } catch (error) {
      // no-op: Safari can reject setData for some drag types.
    }
    setDragging({ dayCode });
  };

  const onTrainingDragEnd = () => {
    setDragging(null);
    setHoveredSlotKey('');
  };

  const onSlotDragOver = (event, dayCode, slotIndex) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    setHoveredSlotKey(`${dayCode}-${slotIndex}`);
  };

  const onSlotDrop = (event, dayCode, slotIndex) => {
    event.preventDefault();
    applySlotSelection(dayCode, slotIndex);
    setDragging(null);
    setHoveredSlotKey('');
  };

  if (!trainingDays.length) {
    return (
      <section className="train-time-card" aria-label="Training timing selector">
        <header className="train-time-header">
          <h3>Before which meal do you train?</h3>
          <p>
            We use your training time to place your workout within your daily meal schedule. This helps us assign the
            right calorie and macro structure for each day based on when you train.
          </p>
        </header>
        <div className="train-time-empty">
          <p>No training days selected yet. Choose workout days first, then set training timing.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="train-time-card" aria-label="Training timing selector">
      <header className="train-time-header">
        <h3>Before which meal do you train?</h3>
        <p>
          We use your training time to place your workout within your daily meal schedule. This helps us assign the
          right calorie and macro structure for each day based on when you train.
        </p>
      </header>

      <div className="train-time-mode-toggle" role="radiogroup" aria-label="Training timing mode">
        {Object.values(TRAINING_TIMING_MODES).map((entry) => {
          const selected = mode === entry.key;
          return (
            <button
              key={entry.key}
              type="button"
              role="radio"
              aria-checked={selected}
              className={`train-time-mode-btn ${selected ? 'is-active' : ''}`}
              onClick={() => setMode(entry.key)}
            >
              {entry.label}
            </button>
          );
        })}
      </div>

      {mode === 'same' ? (
        <div className="train-time-same-picker">
          <strong>Choose one position for all training days</strong>
          <p>Shared timing options are limited by your shortest training-day meal schedule.</p>
        </div>
      ) : null}

      {restDays.length ? (
        <div className="train-time-rest-days">
          <strong>Rest days</strong>
          <div>
            {restDays.map((day) => <span key={`rest-${day.code}`}>{day.label}</span>)}
          </div>
        </div>
      ) : null}

      <div className="train-time-days-grid">
        {trainingDays.map((dayCode, dayIdx) => {
          const dayMeta = TIMING_WEEK_DAYS.find((entry) => entry.code === dayCode);
          const mealCount = normalizeMealCount(mealScheduleByDay?.[dayCode], 1);
          const selectedBeforeMeal = days?.[dayCode] || 1;
          const selectedSlotIndex = mode === 'same' ? selectedSameSlot : beforeMealToSlotIndex(selectedBeforeMeal);
          const timeline = buildTimelineItems({
            mealCount,
            trainingSlotIndex: selectedSlotIndex,
            gender: normalizedGender,
            imagePools: { meal: mealImagePool, training: trainingImagePool },
            daySeed: dayIdx,
          });

          return (
            <article key={`training-day-${dayCode}`} className="train-time-day-card">
              <div className="train-time-day-head">
                <div>
                  <strong>{dayMeta?.label || dayCode.toUpperCase()}</strong>
                  <span>Training Day</span>
                </div>
                <em>{mealCount} meals</em>
              </div>

              <div
                className="train-time-timeline"
                role="list"
                aria-label={`${dayMeta?.fullLabel || dayCode} training timeline`}
              >
                {timeline.map((entry) => {
                  if (entry.type === 'slot') {
                    const slotKey = `${dayCode}-${entry.slotIndex}`;
                    const sharedInvalid = mode === 'same' && !sharedValidSlots.includes(entry.slotIndex);
                    const isHovered = hoveredSlotKey === slotKey;

                    return (
                      <div key={`${dayCode}-${entry.id}`} className="train-time-slot-wrap" role="listitem">
                        <button
                          type="button"
                          className={`train-time-slot ${entry.isTrainingHere ? 'has-training' : ''} ${isHovered ? 'is-hovered' : ''}`}
                          onClick={() => applySlotSelection(dayCode, entry.slotIndex)}
                          onDragOver={(event) => !sharedInvalid && onSlotDragOver(event, dayCode, entry.slotIndex)}
                          onDragEnter={(event) => !sharedInvalid && onSlotDragOver(event, dayCode, entry.slotIndex)}
                          onDragLeave={() => isHovered && setHoveredSlotKey('')}
                          onDrop={(event) => !sharedInvalid && onSlotDrop(event, dayCode, entry.slotIndex)}
                          disabled={sharedInvalid}
                          aria-label={`Set training before Meal ${entry.beforeMeal}`}
                        >
                          {entry.isTrainingHere ? (
                            <div
                              className={`train-time-node training ${dragging ? 'is-dragging-source' : ''}`}
                              draggable
                              onDragStart={(event) => onTrainingDragStart(event, dayCode)}
                              onDragEnd={onTrainingDragEnd}
                            >
                              <img src={entry.trainingImage || pickCycledImage(trainingImagePool, dayIdx)} alt="Workout" />
                              <span>Train</span>
                            </div>
                          ) : (
                            <span className="train-time-slot-hint">
                              {sharedInvalid ? 'Not shared' : `Before Meal ${entry.beforeMeal}`}
                            </span>
                          )}
                        </button>
                      </div>
                    );
                  }

                  return (
                    <div key={`${dayCode}-${entry.id}`} className="train-time-node meal" role="listitem">
                      <img src={entry.image || pickCycledImage(mealImagePool, dayIdx)} alt={`Meal ${entry.mealNumber}`} />
                      <span>Meal {entry.mealNumber}</span>
                    </div>
                  );
                })}
              </div>

              <p className="train-time-feedback">Training happens before Meal {slotIndexToBeforeMeal(selectedSlotIndex)}</p>
            </article>
          );
        })}
      </div>

      <div className="train-time-summary" aria-live="polite">
        {mode === 'same' ? (
          <>
            <p><strong>Training timing:</strong> Same every training day</p>
            <p><strong>Selected position:</strong> Before Meal {slotIndexToBeforeMeal(selectedSameSlot)}</p>
          </>
        ) : (
          <>
            <p><strong>Training timing:</strong> Custom by day</p>
            {trainingDays.map((dayCode) => {
              const dayMeta = TIMING_WEEK_DAYS.find((entry) => entry.code === dayCode);
              const daySlot = beforeMealToSlotIndex(days[dayCode]);
              return <p key={`summary-${dayCode}`}><strong>{dayMeta?.label || dayCode.toUpperCase()}:</strong> Before Meal {slotIndexToBeforeMeal(daySlot)}</p>;
            })}
          </>
        )}
        <p><strong>Why it matters:</strong> We use this to customize workout-day calorie and macro placement around your training window.</p>
      </div>
    </section>
  );
}

export default TrainingMealTimingSelector;
