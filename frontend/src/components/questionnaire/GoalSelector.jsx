import React, { useMemo } from 'react';
import gainFemaleImage from '../../assets/questionnaire/4/goal-gain-female.png';
import gainMaleImage from '../../assets/questionnaire/4/goal-gain-male.png';
import loseFemaleImage from '../../assets/questionnaire/4/goal-lose-female.png';
import loseMaleImage from '../../assets/questionnaire/4/goal-lose-male.png';
import maintainFemaleImage from '../../assets/questionnaire/4/goal-maintain-female.png';
import maintainMaleImage from '../../assets/questionnaire/4/goal-maintain-male.png';
import './GoalSelector.css';

export const GOAL_CARD_CONTENT = {
  lose: {
    key: 'lose',
    title: 'Lose Weight',
    description: 'Eat below maintenance calories to reduce body weight.',
    calorieAdjustmentType: 'deficit',
  },
  maintain: {
    key: 'maintain',
    title: 'Maintain',
    description: 'Stay near maintenance calories to support your current weight.',
    calorieAdjustmentType: 'maintenance',
  },
  gain: {
    key: 'gain',
    title: 'Gain Weight',
    description: 'Eat above maintenance calories to support muscle and weight gain.',
    calorieAdjustmentType: 'surplus',
  },
};

export function goalToCalorieAdjustmentType(goalKey) {
  return GOAL_CARD_CONTENT[goalKey]?.calorieAdjustmentType || null;
}

export function getGoalMeta(goalKey) {
  if (!GOAL_CARD_CONTENT[goalKey]) return null;
  return { ...GOAL_CARD_CONTENT[goalKey] };
}

function getGoalImage(goalKey, gender) {
  const normalizedGender = gender === 'female' ? 'female' : 'male';
  if (goalKey === 'lose') return normalizedGender === 'female' ? loseFemaleImage : loseMaleImage;
  if (goalKey === 'maintain') return normalizedGender === 'female' ? maintainFemaleImage : maintainMaleImage;
  return normalizedGender === 'female' ? gainFemaleImage : gainMaleImage;
}

function GoalSelector({
  value = '',
  onChange,
  onMetaChange,
  gender = 'male',
}) {
  const selectedGoal = GOAL_CARD_CONTENT[value] ? value : '';
  const selectedMeta = selectedGoal ? GOAL_CARD_CONTENT[selectedGoal] : null;

  const cards = useMemo(
    () => ['lose', 'maintain', 'gain'].map((key) => GOAL_CARD_CONTENT[key]),
    []
  );

  const handleSelect = (goalKey) => {
    if (onChange) onChange(goalKey);
    if (onMetaChange) {
      const meta = getGoalMeta(goalKey);
      onMetaChange(meta ? { goal: goalKey, calorieAdjustmentType: meta.calorieAdjustmentType, title: meta.title } : null);
    }
  };

  return (
    <section className="goalsel-card" aria-label="Goal selector">
      <div className="goalsel-header">
        <h3>What are your goals?</h3>
        <p>
          Now that we&apos;ve estimated your baseline calorie needs and total daily energy expenditure, choose the goal
          that best matches what you want to do next. This helps us decide whether your plan should place you in a
          calorie deficit, maintenance range, or calorie surplus.
        </p>
      </div>

      <div className="goalsel-grid">
        {cards.map((card) => {
          const isSelected = selectedGoal === card.key;
          return (
            <button
              key={card.key}
              type="button"
              className={`goalsel-option ${isSelected ? 'is-selected' : ''}`}
              onClick={() => handleSelect(card.key)}
            >
              <div className="goalsel-image-wrap">
                <img
                  className="goalsel-image"
                  src={getGoalImage(card.key, gender)}
                  alt={`${card.title} visual`}
                />
              </div>
              <div className="goalsel-copy">
                <h4>{card.title}</h4>
                <p>{card.description}</p>
              </div>
            </button>
          );
        })}
      </div>

      {selectedMeta ? (
        <div className="goalsel-summary" aria-live="polite">
          <p><strong>Selected goal:</strong> {selectedMeta.title}</p>
          <p><strong>Nutrition approach:</strong> Calorie {selectedMeta.calorieAdjustmentType}</p>
        </div>
      ) : (
        <div className="goalsel-summary is-empty" aria-live="polite">
          <p>Select one goal to continue.</p>
        </div>
      )}
    </section>
  );
}

export default GoalSelector;
