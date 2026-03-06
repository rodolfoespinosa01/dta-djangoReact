import React, { useMemo } from 'react';
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
  buildTrainingMealTimeline,
  getSharedBeforeMealOptions,
  getValidBeforeMealOptions,
  normalizeMealCount,
  normalizeTrainingTimingValue,
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

  const normalized = useMemo(
    () => normalizeTrainingTimingValue({ value, trainingDays, mealScheduleByDay }),
    [value, trainingDays, mealScheduleByDay]
  );

  const { mode, sameBeforeMeal, days } = normalized;
  const sharedOptions = getSharedBeforeMealOptions(trainingDays, mealScheduleByDay);

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
    emitChange({ ...normalized, mode: nextMode });
  };

  const setSameBeforeMeal = (beforeMeal) => {
    const nextDays = { ...days };
    trainingDays.forEach((dayCode) => {
      const dayMealCount = normalizeMealCount(mealScheduleByDay?.[dayCode], 1);
      nextDays[dayCode] = Math.min(beforeMeal, dayMealCount);
    });

    emitChange({
      mode: 'same',
      sameBeforeMeal: beforeMeal,
      days: nextDays,
    });
  };

  const setDayBeforeMeal = (dayCode, beforeMeal) => {
    emitChange({
      ...normalized,
      mode: 'custom',
      days: {
        ...days,
        [dayCode]: beforeMeal,
      },
    });
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
          <div className="train-time-pill-row">
            {sharedOptions.map((option) => (
              <button
                key={`same-before-${option}`}
                type="button"
                className={`train-time-pill ${sameBeforeMeal === option ? 'is-selected' : ''}`}
                onClick={() => setSameBeforeMeal(option)}
              >
                Before Meal {option}
              </button>
            ))}
          </div>
          <p>
            Available options are based on the minimum meals across your training days so the same timing stays valid
            everywhere.
          </p>
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
          const options = getValidBeforeMealOptions(mealCount);
          const timeline = buildTrainingMealTimeline({ mealCount, beforeMeal: selectedBeforeMeal });

          return (
            <article key={`training-day-${dayCode}`} className="train-time-day-card">
              <div className="train-time-day-head">
                <div>
                  <strong>{dayMeta?.label || dayCode.toUpperCase()}</strong>
                  <span>Training Day</span>
                </div>
                <em>{mealCount} meals</em>
              </div>

              {mode === 'custom' ? (
                <div className="train-time-pill-row">
                  {options.map((option) => (
                    <button
                      key={`${dayCode}-before-${option}`}
                      type="button"
                      className={`train-time-pill ${selectedBeforeMeal === option ? 'is-selected' : ''}`}
                      onClick={() => setDayBeforeMeal(dayCode, option)}
                    >
                      Before {option}
                    </button>
                  ))}
                </div>
              ) : null}

              <div className="train-time-timeline" role="list" aria-label={`${dayMeta?.fullLabel || dayCode} training timeline`}>
                {timeline.map((entry, itemIdx) => {
                  if (entry.type === 'training') {
                    return (
                      <React.Fragment key={`${dayCode}-${entry.id}-${selectedBeforeMeal}`}>
                        <div className="train-time-node training" role="listitem">
                          <img src={pickCycledImage(trainingImagePool, dayIdx + itemIdx)} alt="Workout" />
                          <span>Train</span>
                        </div>
                        <span className="train-time-arrow" aria-hidden="true">-></span>
                      </React.Fragment>
                    );
                  }

                  const isLast = itemIdx === timeline.length - 1;
                  return (
                    <React.Fragment key={`${dayCode}-${entry.id}`}>
                      <div className="train-time-node meal" role="listitem">
                        <img src={pickCycledImage(mealImagePool, dayIdx + itemIdx)} alt={`Meal ${entry.mealNumber}`} />
                        <span>Meal {entry.mealNumber}</span>
                      </div>
                      {!isLast ? <span className="train-time-arrow" aria-hidden="true">-></span> : null}
                    </React.Fragment>
                  );
                })}
              </div>
            </article>
          );
        })}
      </div>

      <div className="train-time-summary" aria-live="polite">
        {mode === 'same' ? (
          <>
            <p><strong>Training timing:</strong> Same every training day</p>
            <p><strong>Selected position:</strong> Before Meal {sameBeforeMeal || '-'}</p>
          </>
        ) : (
          <>
            <p><strong>Training timing:</strong> Custom by day</p>
            {trainingDays.map((dayCode) => {
              const dayMeta = TIMING_WEEK_DAYS.find((entry) => entry.code === dayCode);
              return <p key={`summary-${dayCode}`}><strong>{dayMeta?.label || dayCode.toUpperCase()}:</strong> Before Meal {days[dayCode]}</p>;
            })}
          </>
        )}
        <p><strong>Why it matters:</strong> We use this to customize workout-day calorie and macro placement around your training window.</p>
      </div>
    </section>
  );
}

export default TrainingMealTimingSelector;
