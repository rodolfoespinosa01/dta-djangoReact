import React from 'react';

/**
 * Checklist component to guide the user through required actions in order.
 * Highlights next required action and disables/enables buttons accordingly.
 */
export default function ClientActionChecklist({
  foodPreferencesComplete,
  mealPlanGenerated,
  photoDue,
  weightDue,
  onOpenFoodPreferences,
  onOpenMealPlanGeneration,
  onOpenRecipeGeneration,
  onOpenPhotoUpload,
  onOpenWeightTracking,
  recipeGenerationEnabled
}) {
  // Determine which step is next
  let nextStep = null;
  if (photoDue) nextStep = 'photo';
  else if (weightDue) nextStep = 'weight';
  else if (!foodPreferencesComplete) nextStep = 'food';
  else if (!mealPlanGenerated) nextStep = 'meal';
  else if (!recipeGenerationEnabled) nextStep = 'recipe';

  return (
    <section className="client-dashboard-card" style={{ background: '#f8fbff', border: '1.5px solid #1976d2', marginBottom: 18 }}>
      <h2 style={{ color: '#1976d2', marginBottom: 8 }}>Your Next Steps</h2>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: '1.08em' }}>
        <li style={{ marginBottom: 10 }}>
          <button
            className={`client-q-btn${nextStep === 'photo' ? ' highlight' : ' secondary'}`}
            style={nextStep === 'photo' ? { background: '#fffbe0', color: '#b08000', fontWeight: 700 } : {}}
            onClick={onOpenPhotoUpload}
          >
            {photoDue ? 'Upload Progress Photo (Required)' : 'Progress Photo Up-to-date'}
          </button>
        </li>
        <li style={{ marginBottom: 10 }}>
          <button
            className={`client-q-btn${nextStep === 'weight' ? ' highlight' : ' secondary'}`}
            style={nextStep === 'weight' ? { background: '#fffbe0', color: '#b08000', fontWeight: 700 } : {}}
            onClick={onOpenWeightTracking}
          >
            {weightDue ? 'Update Weight (Required)' : 'Weight Up-to-date'}
          </button>
        </li>
        <li style={{ marginBottom: 10 }}>
          <button
            className={`client-q-btn${nextStep === 'food' ? ' highlight' : ' secondary'}`}
            style={nextStep === 'food' ? { background: '#ffe0e0', color: '#b00', fontWeight: 700 } : {}}
            onClick={onOpenFoodPreferences}
            disabled={foodPreferencesComplete}
          >
            {foodPreferencesComplete ? 'Food Preferences Complete' : 'Complete Food Preferences'}
          </button>
        </li>
        <li style={{ marginBottom: 10 }}>
          <button
            className={`client-q-btn${nextStep === 'meal' ? ' highlight' : ' secondary'}`}
            style={nextStep === 'meal' ? { background: '#e0f7fa', color: '#00796b', fontWeight: 700 } : {}}
            onClick={onOpenMealPlanGeneration}
            disabled={!foodPreferencesComplete || mealPlanGenerated}
          >
            {mealPlanGenerated ? 'Meal Plan Generated' : 'Generate Meal Plan'}
          </button>
        </li>
        <li>
          <button
            className={`client-q-btn${nextStep === 'recipe' ? ' highlight' : ' secondary'}`}
            style={nextStep === 'recipe' ? { background: '#e3f2fd', color: '#1976d2', fontWeight: 700 } : {}}
            onClick={onOpenRecipeGeneration}
            disabled={!mealPlanGenerated || recipeGenerationEnabled}
          >
            {recipeGenerationEnabled ? 'Recipe Generation Ready' : 'Generate Recipes (after meal plan)'}
          </button>
        </li>
      </ul>
    </section>
  );
}
