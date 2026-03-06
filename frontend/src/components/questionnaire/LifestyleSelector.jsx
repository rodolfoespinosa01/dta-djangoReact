import React, { useMemo } from 'react';
import highFemaleImage from '../../assets/questionnaire/5/activity-high-female.png';
import highMaleImage from '../../assets/questionnaire/5/activity-high-male.png';
import lowFemaleImage from '../../assets/questionnaire/5/activity-low-female.png';
import lowMaleImage from '../../assets/questionnaire/5/activity-low-male.png';
import moderateFemaleImage from '../../assets/questionnaire/5/activity-moderate-female.png';
import moderateMaleImage from '../../assets/questionnaire/5/activity-moderate-male.png';
import './LifestyleSelector.css';

export const LIFESTYLE_CONTENT = {
  low: {
    key: 'low',
    title: 'Low Activity',
    description:
      'You spend most of the day sitting, driving, studying, or working at a desk, with little physical movement outside of normal daily tasks.',
  },
  moderate: {
    key: 'moderate',
    title: 'Moderate Activity',
    description:
      'You move around regularly during the day and may spend part of your time walking, standing, or doing light physical work.',
  },
  high: {
    key: 'high',
    title: 'High Activity',
    description:
      'You stay on your feet a lot, move frequently throughout the day, or do physically demanding work or activity on a regular basis.',
  },
};

export function normalizeLifestyleCode(value) {
  const v = String(value || '').trim().toLowerCase();
  if (v === 'low' || v === 'low_active') return 'low';
  if (v === 'moderate' || v === 'middle_active') return 'moderate';
  if (v === 'high' || v === 'high_active') return 'high';
  return '';
}

function getLifestyleImage(lifestyleKey, gender) {
  const normalizedGender = gender === 'female' ? 'female' : 'male';
  if (lifestyleKey === 'low') return normalizedGender === 'female' ? lowFemaleImage : lowMaleImage;
  if (lifestyleKey === 'high') return normalizedGender === 'female' ? highFemaleImage : highMaleImage;
  return normalizedGender === 'female' ? moderateFemaleImage : moderateMaleImage;
}

function LifestyleSelector({
  value = '',
  onChange,
  gender = 'male',
}) {
  const selected = normalizeLifestyleCode(value);
  const selectedMeta = selected ? LIFESTYLE_CONTENT[selected] : null;
  const cards = useMemo(() => ['low', 'moderate', 'high'].map((key) => LIFESTYLE_CONTENT[key]), []);

  return (
    <section className="lifesel-card" aria-label="Lifestyle selector">
      <div className="lifesel-header">
        <h3>What is your lifestyle like?</h3>
        <p>
          Your daily movement matters. We use your lifestyle activity level to better estimate how many calories your
          body uses throughout the day, which helps us calculate your final calorie and macro targets.
        </p>
      </div>

      <div className="lifesel-grid">
        {cards.map((card) => {
          const isSelected = selected === card.key;
          return (
            <button
              key={card.key}
              type="button"
              className={`lifesel-option ${isSelected ? 'is-selected' : ''}`}
              onClick={() => onChange && onChange(card.key)}
            >
              <div className="lifesel-image-wrap">
                <img
                  className="lifesel-image"
                  src={getLifestyleImage(card.key, gender)}
                  alt={`${card.title} visual`}
                />
              </div>
              <div className="lifesel-copy">
                <h4>{card.title}</h4>
                <p>{card.description}</p>
              </div>
            </button>
          );
        })}
      </div>

      {selectedMeta ? (
        <div className="lifesel-summary" aria-live="polite">
          <p><strong>Selected lifestyle:</strong> {selectedMeta.title}</p>
          <p><strong>Why it matters:</strong> This helps estimate your total daily energy expenditure.</p>
        </div>
      ) : (
        <div className="lifesel-summary is-empty" aria-live="polite">
          <p>Select one lifestyle level to continue.</p>
        </div>
      )}
    </section>
  );
}

export default LifestyleSelector;
