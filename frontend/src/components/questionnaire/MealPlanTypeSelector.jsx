import React, { useMemo } from 'react';
import standardImage from '../../assets/questionnaire/6/standard.png';
import carbCyclingImage from '../../assets/questionnaire/6/carb-cycling.png';
import ketoImage from '../../assets/questionnaire/6/keto.png';
import './MealPlanTypeSelector.css';

export const MEAL_PLAN_TYPE_CONTENT = {
  standard: {
    key: 'standard',
    title: 'Standard Meal Plan',
    badge: 'Recommended',
    description:
      'Your calories and macros are distributed using our standard structure based on your training time and schedule. This is the most balanced and straightforward option for most users.',
    bestFor: 'Best for: Most users who want a balanced and simple structure',
    summary: 'Macro distribution is based on your training schedule.',
  },
  carb_cycling: {
    key: 'carb_cycling',
    title: 'Carb Cycling Plan',
    badge: 'Advanced',
    description:
      'Your calories and carbs vary between higher-carb and lower-carb days throughout the week. This is a more advanced dieting approach that some users prefer for flexibility, performance, or adherence.',
    bestFor: 'Best for: Users who want alternating higher-carb and lower-carb days',
    summary: 'Carbs and calories vary across higher- and lower-carb days.',
  },
  keto: {
    key: 'keto',
    title: 'Keto Plan',
    badge: 'Low Carb',
    description:
      'Your plan keeps carbohydrates very low and shifts your macros toward fats and protein. This option is for users who specifically want a ketogenic-style approach.',
    bestFor: 'Best for: Users who prefer a very low-carb approach',
    summary: 'Macros shift toward fats and protein with very low carbs.',
  },
};

export function normalizeMealPlanTypeCode(value) {
  const v = String(value || '').trim().toLowerCase();
  if (v === 'standard' || v === 'carb_cycling' || v === 'keto') return v;
  return '';
}

function mealPlanImageFor(code) {
  if (code === 'carb_cycling') return carbCyclingImage;
  if (code === 'keto') return ketoImage;
  return standardImage;
}

function MealPlanTypeSelector({
  value = '',
  onChange,
}) {
  const selected = normalizeMealPlanTypeCode(value);
  const selectedMeta = selected ? MEAL_PLAN_TYPE_CONTENT[selected] : null;
  const cards = useMemo(() => ['standard', 'carb_cycling', 'keto'].map((key) => MEAL_PLAN_TYPE_CONTENT[key]), []);

  return (
    <section className="mplansel-card" aria-label="Meal plan type selector">
      <div className="mplansel-header">
        <h3>How would you like your meal plan structured?</h3>
        <p>
          Now that we understand your body data, lifestyle, and goals, the final step is choosing the type of meal
          plan structure you want to follow. Each option organizes your calories and macros differently.
        </p>
      </div>

      <div className="mplansel-grid">
        {cards.map((card) => {
          const isSelected = selected === card.key;
          return (
            <button
              key={card.key}
              type="button"
              className={`mplansel-option ${isSelected ? 'is-selected' : ''}`}
              onClick={() => onChange && onChange(card.key)}
            >
              <div className="mplansel-badge">{card.badge}</div>
              <div className="mplansel-image-wrap">
                <img
                  className="mplansel-image"
                  src={mealPlanImageFor(card.key)}
                  alt={`${card.title} visual`}
                />
              </div>
              <div className="mplansel-copy">
                <h4>{card.title}</h4>
                <p>{card.description}</p>
                <p className="mplansel-bestfor">{card.bestFor}</p>
              </div>
            </button>
          );
        })}
      </div>

      {selectedMeta ? (
        <div className="mplansel-summary" aria-live="polite">
          <p><strong>Selected structure:</strong> {selectedMeta.title}</p>
          <p><strong>How it works:</strong> {selectedMeta.summary}</p>
        </div>
      ) : (
        <div className="mplansel-summary is-empty" aria-live="polite">
          <p>Select a structure to continue.</p>
        </div>
      )}
    </section>
  );
}

export default MealPlanTypeSelector;
