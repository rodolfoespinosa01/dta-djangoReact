import React, { useMemo } from 'react';
import meal3Image from '../../assets/questionnaire/7/meals-3.jpg';
import meal4Image from '../../assets/questionnaire/7/meals-4.jpg';
import meal5Image from '../../assets/questionnaire/7/meals-5.png';
import meal6Image from '../../assets/questionnaire/7/meals-6.png';
import {
  MEAL_FREQUENCY_OPTIONS,
  MEAL_SCHEDULE_DAYS,
  MEAL_SCHEDULE_MODES,
  averageMealsPerDay,
  getMealFrequencyGuidance,
  getMealFrequencyRecommendation,
  normalizeMealFrequencyValue,
} from './mealFrequency.constants';
import './MealFrequencySelector.css';

const MEAL_COUNT_IMAGES = {
  3: meal3Image,
  4: meal4Image,
  5: meal5Image,
  6: meal6Image,
};

function MealFrequencySelector({
  value,
  onChange,
  dailyCalories = null,
  dayCaloriesByCode = {},
  disableLessPractical = false,
}) {
  const normalized = useMemo(() => normalizeMealFrequencyValue(value), [value]);
  const { mode, defaultMeals, days } = normalized;

  const guidance = getMealFrequencyGuidance(dailyCalories);
  const averageMeals = averageMealsPerDay(days);

  const emitChange = (nextValue) => {
    if (!onChange) return;
    onChange(nextValue);
  };

  const setMode = (nextMode) => {
    if (nextMode === mode) return;
    emitChange({ ...normalized, mode: nextMode });
  };

  const selectDefaultMeals = (mealCount) => {
    const nextDays = MEAL_SCHEDULE_DAYS.reduce((acc, day) => {
      acc[day.code] = mealCount;
      return acc;
    }, {});

    emitChange({
      mode: 'same',
      defaultMeals: mealCount,
      days: nextDays,
    });
  };

  const setDayMeals = (dayCode, mealCount) => {
    emitChange({
      ...normalized,
      mode: 'custom',
      days: {
        ...days,
        [dayCode]: mealCount,
      },
    });
  };

  return (
    <section className="mealfreq-card" aria-label="Meal frequency selector">
      <header className="mealfreq-header">
        <h3>How many meals would you like each day?</h3>
        <p>
          We use meal frequency to distribute your daily calories and macros in a way that feels realistic for your
          schedule. The goal is to choose a meal pattern that makes sense for your calorie target and day-to-day routine.
        </p>
      </header>

      <div className="mealfreq-guidance" aria-live="polite">
        <p>{guidance}</p>
      </div>

      <div className="mealfreq-mode-toggle" role="radiogroup" aria-label="Meal frequency mode">
        {Object.values(MEAL_SCHEDULE_MODES).map((entry) => {
          const selected = mode === entry.key;
          return (
            <button
              key={entry.key}
              type="button"
              role="radio"
              aria-checked={selected}
              className={`mealfreq-mode-btn ${selected ? 'is-active' : ''}`}
              onClick={() => setMode(entry.key)}
            >
              {entry.label}
            </button>
          );
        })}
      </div>

      {mode === 'same' ? (
        <div className="mealfreq-card-grid">
          {MEAL_FREQUENCY_OPTIONS.map((mealCount) => {
            const recommendation = getMealFrequencyRecommendation(dailyCalories, mealCount);
            const isSelected = defaultMeals === mealCount;
            const isLessPractical = recommendation.level === 'less_practical';
            const shouldDisable = disableLessPractical && isLessPractical;

            return (
              <button
                key={`same-${mealCount}`}
                type="button"
                className={`mealfreq-option ${isSelected ? 'is-selected' : ''} ${recommendation.level === 'recommended' ? 'is-recommended' : ''} ${isLessPractical ? 'is-less-practical' : ''}`}
                onClick={() => selectDefaultMeals(mealCount)}
                disabled={shouldDisable}
              >
                <div className="mealfreq-option-image-wrap">
                  <img src={MEAL_COUNT_IMAGES[mealCount]} alt={`${mealCount} meals visual`} className="mealfreq-option-image" />
                </div>
                <div className="mealfreq-option-copy">
                  <h4>{mealCount} meals</h4>
                  {recommendation.tag ? <span className={`mealfreq-tag ${recommendation.level}`}>{recommendation.tag}</span> : null}
                  {recommendation.helperText ? <p>{recommendation.helperText}</p> : null}
                </div>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="mealfreq-custom-grid">
          {MEAL_SCHEDULE_DAYS.map((day) => {
            const selectedMeals = days[day.code];
            const dayCalories = Number(dayCaloriesByCode?.[day.code]);
            const recommendation = getMealFrequencyRecommendation(dayCalories, selectedMeals);
            return (
              <article key={day.code} className="mealfreq-day-row">
                <div className="mealfreq-day-head">
                  <strong>{day.label}</strong>
                  <span>{Number.isFinite(dayCalories) ? `${Math.round(dayCalories)} kcal` : ''}</span>
                </div>

                <div className="mealfreq-day-options">
                  {MEAL_FREQUENCY_OPTIONS.map((mealCount) => {
                    const choiceRecommendation = getMealFrequencyRecommendation(dayCalories, mealCount);
                    const isSelected = selectedMeals === mealCount;
                    const shouldDisable = disableLessPractical && choiceRecommendation.level === 'less_practical';
                    return (
                      <button
                        key={`${day.code}-${mealCount}`}
                        type="button"
                        className={`mealfreq-day-pill ${isSelected ? 'is-selected' : ''}`}
                        onClick={() => setDayMeals(day.code, mealCount)}
                        disabled={shouldDisable}
                      >
                        {mealCount}
                      </button>
                    );
                  })}
                </div>

                <div className="mealfreq-day-foot">
                  <img src={MEAL_COUNT_IMAGES[selectedMeals]} alt="Selected meal pattern" className="mealfreq-day-thumb" />
                  <div>
                    <span>{selectedMeals} meals selected</span>
                    {recommendation.level === 'less_practical' ? (
                      <p>Not recommended for your current calorie target. This may create meals that are too small to feel practical.</p>
                    ) : recommendation.level === 'recommended' ? (
                      <p>Recommended for your current calorie target.</p>
                    ) : (
                      <p>Choose what feels easiest to sustain in your weekly routine.</p>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      <div className="mealfreq-summary" aria-live="polite">
        {mode === 'same' ? (
          <>
            <p><strong>Selected pattern:</strong> Same every day</p>
            <p><strong>Meal frequency:</strong> {defaultMeals} meals</p>
            <p><strong>Why it matters:</strong> This helps us spread your calories and macros into realistic meal sizes.</p>
          </>
        ) : (
          <>
            <p><strong>Selected pattern:</strong> Custom by day</p>
            <p><strong>Average meals per day:</strong> {averageMeals}</p>
            <p><strong>Why it matters:</strong> This helps us match meal structure to your weekly routine.</p>
          </>
        )}
      </div>
    </section>
  );
}

export default MealFrequencySelector;
