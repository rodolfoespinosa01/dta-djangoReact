
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiRequest } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { getFoodImageUrl } from '../../utils/foodImageLookup';
import { escapeHtml, openPrintPdfWindow, renderPrintTable } from '../../utils/printPdf';
import aiLogo from '../../assets/misc/ailogo.png';

import './ClientDashboardPage.css';


const WEEK_DAYS = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];

function prettyDay(day) {
  const value = (day || '').toLowerCase();
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : 'Day';
}

function formatTrainingLabel(value) {
  if (!value || value === 'none') return 'No training';
  return String(value).replace('before_meal_', 'Before Meal ');
}

function toMealCount(value) {
  const count = Number(value || 0);
  return [3, 4, 5, 6].includes(count) ? count : 0;
}

function buildComboCoverage(foodPreferencesPayload) {
  const builder = foodPreferencesPayload?.builder_value || {};
  const schedule = foodPreferencesPayload?.meal_schedule_days || {};
  const weekly = builder?.weekly_days || {};
  const byDay = {};
  let weekComplete = true;
  WEEK_DAYS.forEach((day) => {
    const expected = toMealCount(schedule?.[day]);
    const meals = Array.isArray(weekly?.[day]) ? weekly[day] : [];
    const validLength = meals.length === expected;
    const matched = meals.filter((meal) => Number(meal?.combo_id) > 0).length;
    const isComplete = expected > 0 && validLength && matched === expected;
    byDay[day] = { expected, actualMeals: meals.length, matched, isComplete };
    if (!isComplete) weekComplete = false;
  });
  return { byDay, isWeekComplete: weekComplete };
}

function amountLabel(slot, unitMode) {
  if (!slot) return '-';
  if (unitMode === 'g') return `${Number(slot.amount_g || 0).toFixed(2)} g`;
  return `${Number(slot.amount_oz || 0).toFixed(2)} oz`;
}

function printableAmountLabel(slot, unitMode) {
  if (!slot) return '-';
  return unitMode === 'g'
    ? `${Number(slot.amount_g || 0).toFixed(2)} g`
    : `${Number(slot.amount_oz || 0).toFixed(2)} oz`;
}

function renderPrintSection(title, innerHtml) {
  return `<section class="section"><h2>${escapeHtml(title)}</h2>${innerHtml}</section>`;
}

function renderChipList(items = []) {
  const rows = items.filter(Boolean);
  if (!rows.length) return '';
  return `<div class="chips">${rows.map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join('')}</div>`;
}

function buildMacrosSectionHtml(jobSnapshot, detail) {
  const snapshot = jobSnapshot?.input_snapshot || {};
  const dayPayload = snapshot?.day_payload || null;
  if (!dayPayload) {
    return renderPrintSection(
      'Macros',
      '<p class="muted">Macro snapshot is not loaded yet. Load the job snapshot for this day first.</p>'
    );
  }

  const macroRows = (dayPayload.meal_macro_splits || []).map((meal) => ([
    `Meal ${meal.meal_number ?? '-'}`,
    `${meal.grams?.protein_g ?? '-'} g (${meal.percentages?.protein ?? '-'}%)`,
    `${meal.grams?.carbs_g ?? '-'} g (${meal.percentages?.carbs ?? '-'}%)`,
    `${meal.grams?.fats_g ?? '-'} g (${meal.percentages?.fats ?? '-'}%)`,
  ]));

  return renderPrintSection(
    'Macros',
    [
      renderChipList([
        `Day: ${prettyDay(dayPayload.day || detail?.day_of_week || 'day')}`,
        `${dayPayload.is_workout_day ? 'Workout Day' : 'Off Day'}`,
        `Meals: ${dayPayload.meals_per_day ?? detail?.meals_per_day ?? '-'}`,
        `Training: ${formatTrainingLabel(dayPayload.training_before_meal || detail?.training_time || 'none')}`,
        dayPayload.tdee_calories != null ? `TDEE: ${dayPayload.tdee_calories} kcal` : null,
        dayPayload.calories_target != null ? `Target: ${dayPayload.calories_target} kcal` : null,
      ]),
      renderChipList([
        `Protein: ${dayPayload.daily_macros?.protein_g ?? '-'} g`,
        `Carbs: ${dayPayload.daily_macros?.carbs_g ?? '-'} g`,
        `Fats: ${dayPayload.daily_macros?.fats_g ?? '-'} g`,
        dayPayload.carb_cycling_mode
          ? `Mode: ${dayPayload.carb_cycling_mode === 'high_carbs' ? 'High Carb Day' : 'Low Carb Day'}`
          : null,
      ]),
      renderPrintTable(['Meal', 'Protein', 'Carbs', 'Fats'], macroRows),
    ].join('')
  );
}

function buildFoodPlanSectionHtml(detail, unitMode) {
  const meals = Array.isArray(detail?.meals) ? detail.meals : [];
  const rows = meals.map((meal) => ([
    `Meal ${meal.meal_number ?? '-'}`,
    String(meal.combo_id ?? '-'),
    `${meal.slots?.protein_1?.name || '-'} (${printableAmountLabel(meal.slots?.protein_1, unitMode)})`,
    `${meal.slots?.protein_2?.name || '-'} (${printableAmountLabel(meal.slots?.protein_2, unitMode)})`,
    `${meal.slots?.carbs_1?.name || '-'} (${printableAmountLabel(meal.slots?.carbs_1, unitMode)})`,
    `${meal.slots?.carbs_2?.name || '-'} (${printableAmountLabel(meal.slots?.carbs_2, unitMode)})`,
    `${meal.slots?.fats_1?.name || '-'} (${printableAmountLabel(meal.slots?.fats_1, unitMode)})`,
    `${meal.slots?.fats_2?.name || '-'} (${printableAmountLabel(meal.slots?.fats_2, unitMode)})`,
  ]));

  return renderPrintSection(
    'Food Plan',
    [
      renderChipList([
        `Day: ${prettyDay(detail?.day_of_week || 'day')}`,
        `Job: #${detail?.job_id ?? '-'}`,
        `Status: ${detail?.job_status || '-'}`,
        `Meals: ${detail?.meals_per_day || meals.length || 0}`,
        `Training: ${formatTrainingLabel(detail?.training_time || 'none')}`,
        `Units: ${unitMode === 'g' ? 'grams' : 'ounces'}`,
      ]),
      renderPrintTable(
        ['Meal', 'Combo', 'Protein 1', 'Protein 2', 'Carbs 1', 'Carbs 2', 'Fats 1', 'Fats 2'],
        rows
      ),
    ].join('')
  );
}

function buildRecipesSectionHtml(detail, recipeIdeasResult) {
  const providerLine = recipeIdeasResult?.provider_used
    ? `<p class="muted">Provider: ${escapeHtml(String(recipeIdeasResult.provider_used))} (${escapeHtml(String(recipeIdeasResult.model || 'n/a'))})</p>`
    : '';
  const meals = Array.isArray(detail?.meals) ? detail.meals : [];
  const recipeMeals = Array.isArray(recipeIdeasResult?.meals) ? recipeIdeasResult.meals : [];

  const cards = meals.map((meal) => {
    const recipeMeal = recipeMeals.find((row) => row.meal_number === meal.meal_number);
    const ideas = Array.isArray(recipeMeal?.ideas) ? recipeMeal.ideas : [];
    const ideasHtml = ideas.length
      ? ideas.map((idea, idx) => {
        const steps = Array.isArray(idea.steps) ? idea.steps : [];
        const seasoning = Array.isArray(idea.seasoning) ? idea.seasoning.join(', ') : '';
        const variations = Array.isArray(idea.variation_options) ? idea.variation_options : [];
        return `
          <div class="section" style="margin:8px 0 0; padding:10px;">
            <h3>Idea ${idx + 1}: ${escapeHtml(idea.title || 'Recipe Idea')}</h3>
            ${renderChipList([
              idea.prep_style ? `Style: ${idea.prep_style}` : null,
              idea.cook_time_minutes != null ? `Cook Time: ${idea.cook_time_minutes} min` : null,
            ])}
            ${seasoning ? `<p><strong>Seasoning:</strong> ${escapeHtml(seasoning)}</p>` : ''}
            ${steps.length ? `<ol>${steps.map((step) => `<li>${escapeHtml(step)}</li>`).join('')}</ol>` : ''}
            ${idea.meal_prep_tip ? `<p><strong>Prep Tip:</strong> ${escapeHtml(idea.meal_prep_tip)}</p>` : ''}
            ${variations.length ? `<p><strong>Variations:</strong> ${escapeHtml(variations.join(' | '))}</p>` : ''}
          </div>
        `;
      }).join('')
      : '<p class="muted">No recipe ideas available for this meal.</p>';

    return `
      <div class="section">
        <h3>Meal ${escapeHtml(String(meal.meal_number ?? '-'))} (Combo ${escapeHtml(String(meal.combo_id ?? '-'))})</h3>
        ${recipeMeal?.fallback_reason ? '<p class="muted">Mock recipe ideas used because the AI provider was unavailable.</p>' : ''}
        ${ideasHtml}
      </div>
    `;
  }).join('');

  return renderPrintSection(
    'Recipes',
    [
      renderChipList([
        `Day: ${prettyDay(detail?.day_of_week || 'day')}`,
        `Meals: ${meals.length}`,
        recipeIdeasResult?.provider_requested ? `Requested: ${recipeIdeasResult.provider_requested}` : null,
      ]),
      providerLine,
      cards || '<p class="muted">No recipe ideas generated yet.</p>',
    ].join('')
  );
}

function FoodSlotCell({ slot, unitMode }) {
  const imageUrl = getFoodImageUrl(slot?.name);
  return (
    <div style={{ display: 'grid', gap: '0.35rem' }}>
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={slot?.name || 'Food'}
            style={{
              width: 38,
              height: 38,
              borderRadius: 8,
              objectFit: 'cover',
              border: '1px solid rgba(20,40,74,0.12)',
              background: '#fff',
            }}
          />
        ) : (
          <div
            aria-hidden="true"
            style={{
              width: 38,
              height: 38,
              borderRadius: 8,
              border: '1px dashed rgba(20,40,74,0.18)',
              background: '#f8fbff',
            }}
          />
        )}
        <strong style={{ fontSize: '0.92rem' }}>{slot?.name || '-'}</strong>
      </div>
      <span className="client-dash-muted" style={{ fontSize: '0.85rem', paddingLeft: imageUrl ? 46 : 0 }}>
        {amountLabel(slot, unitMode)}
      </span>
    </div>
  );
}

function RecipeIdeasMealCard({ meal, recipeMeal }) {
  const ideas = Array.isArray(recipeMeal?.ideas) ? recipeMeal.ideas : [];
  const mealNumber = meal?.meal_number ?? 0;
  const [activeIdeaIndex, setActiveIdeaIndex] = useState(0);

  useEffect(() => {
    setActiveIdeaIndex(0);
  }, [mealNumber, ideas.length]);

  if (!meal) return null;

  const hasIdeas = ideas.length > 0;
  const safeIndex = Math.min(activeIdeaIndex, Math.max(ideas.length - 1, 0));
  const activeIdea = hasIdeas ? ideas[safeIndex] : null;

  return (
    <div
      style={{
        border: '1px solid rgba(20,40,74,0.12)',
        borderRadius: 12,
        padding: '0.9rem',
        background: '#fff',
        display: 'grid',
        gap: '0.65rem',
      }}
    >
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <strong>Meal {meal.meal_number}</strong>
        <span className="client-dash-muted">Combo {meal.combo_id}</span>
      </div>

      {recipeMeal?.fallback_reason ? (
        <p className="client-dash-muted" style={{ margin: 0 }}>
          Using mock recipe ideas because the AI provider was unavailable (for example: no API key configured).
        </p>
      ) : null}

      {!hasIdeas ? (
        <p className="client-dash-muted" style={{ margin: 0 }}>
          No recipe ideas available for this meal.
        </p>
      ) : (
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span className="client-dash-muted">
              Idea {safeIndex + 1} of {ideas.length}
            </span>
            <div style={{ display: 'inline-flex', gap: '0.35rem', alignItems: 'center' }}>
              <button
                type="button"
                className="client-q-btn secondary"
                onClick={() => setActiveIdeaIndex((prev) => (prev - 1 + ideas.length) % ideas.length)}
                disabled={ideas.length <= 1}
                style={{ padding: '0.35rem 0.6rem' }}
              >
                Prev
              </button>
              <button
                type="button"
                className="client-q-btn secondary"
                onClick={() => setActiveIdeaIndex((prev) => (prev + 1) % ideas.length)}
                disabled={ideas.length <= 1}
                style={{ padding: '0.35rem 0.6rem' }}
              >
                Next
              </button>
            </div>
          </div>

          <div
            style={{
              border: '1px solid rgba(20,40,74,0.08)',
              borderRadius: 10,
              padding: '0.75rem',
              background: '#f8fbff',
            }}
          >
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
              <strong>{activeIdea.title}</strong>
              <span className="client-dash-muted">{activeIdea.prep_style}</span>
              <span className="client-dash-muted">{activeIdea.cook_time_minutes} min</span>
            </div>
            {Array.isArray(activeIdea.seasoning) && activeIdea.seasoning.length ? (
              <p className="client-dash-muted" style={{ margin: '0.4rem 0 0' }}>
                Seasoning: {activeIdea.seasoning.join(', ')}
              </p>
            ) : null}
            {Array.isArray(activeIdea.steps) && activeIdea.steps.length ? (
              <ol style={{ margin: '0.5rem 0 0', paddingLeft: '1.2rem' }}>
                {activeIdea.steps.map((step, stepIdx) => (
                  <li key={`meal-${meal.meal_number}-idea-${safeIndex}-step-${stepIdx}`} style={{ marginBottom: '0.25rem' }}>
                    {step}
                  </li>
                ))}
              </ol>
            ) : null}
            {activeIdea.meal_prep_tip ? (
              <p style={{ margin: '0.5rem 0 0', fontSize: '0.9rem' }}>
                <strong>Prep Tip:</strong> {activeIdea.meal_prep_tip}
              </p>
            ) : null}
            {Array.isArray(activeIdea.variation_options) && activeIdea.variation_options.length ? (
              <div style={{ marginTop: '0.45rem' }}>
                <p className="client-dash-muted" style={{ margin: 0 }}>
                  Variations:
                </p>
                <ul style={{ margin: '0.3rem 0 0', paddingLeft: '1.1rem' }}>
                  {activeIdea.variation_options.map((option, optionIdx) => (
                    <li key={`meal-${meal.meal_number}-idea-${safeIndex}-variation-${optionIdx}`} style={{ marginBottom: '0.2rem' }}>
                      {option}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}

function ClientMealPlanGenerationPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [dayOfWeek, setDayOfWeek] = useState('sunday');
  const [unitMode, setUnitMode] = useState('oz');
  const [running, setRunning] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [generationResult, setGenerationResult] = useState(null);
  const [generationWeekResult, setGenerationWeekResult] = useState(null);
  const [jobSnapshot, setJobSnapshot] = useState(null);
  const [detail, setDetail] = useState(null);
  const [recipeIdeaProvider, setRecipeIdeaProvider] = useState('auto');
  const [recipeIdeaCount, setRecipeIdeaCount] = useState(3);
  const [recipeIdeasLoading, setRecipeIdeasLoading] = useState(false);
  const [recipeIdeasError, setRecipeIdeasError] = useState('');
  const [recipeIdeasResult, setRecipeIdeasResult] = useState(null);
  const [showAllMeals, setShowAllMeals] = useState(false);
  const [currentMealIndex, setCurrentMealIndex] = useState(0);
  const weekPollTimeoutRef = useRef(null);
  const [comboCoverage, setComboCoverage] = useState(null);
  const [coverageLoading, setCoverageLoading] = useState(true);

  const loadLatestDetail = useCallback(async (day, jobId = null) => {
    setLoadingDetail(true);
    setError('');
    try {
      const suffix = jobId ? `?job_id=${encodeURIComponent(jobId)}` : '';
      const res = await apiRequest(`/api/v1/users/client/app/meal-plan-days/${day}/detailed/${suffix}`, { auth: true });
      if (!res.ok) {
        setDetail(null);
        if (res.status === 401) {
          navigate('/client_login', { replace: true });
          return null;
        }
        if (res.status !== 404) {
          setError(res.data?.error?.message || 'Unable to load detailed meal plan.');
        }
        return null;
      }
      const payload = res.data?.meal_plan_day || null;
      setDetail(payload);
      setRecipeIdeasResult(null);
      setRecipeIdeasError('');
      return payload;
    } catch (err) {
      console.error(err);
      setDetail(null);
      setError('Network error while loading detailed meal plan.');
      return null;
    } finally {
      setLoadingDetail(false);
    }
  }, [navigate]);

  const loadJobSnapshot = useCallback(async (jobId) => {
    if (!jobId) return;
    try {
      const res = await apiRequest(`/api/v1/users/client/app/meal-plan-generation/jobs/${jobId}/`, { auth: true });
      if (res.ok) {
        const payload = res.data?.generation || null;
        setJobSnapshot(payload);
        return payload;
      }
    } catch (err) {
      console.error(err);
    }
    return null;
  }, []);

  useEffect(() => {
    loadLatestDetail(dayOfWeek).catch((err) => console.error(err));
  }, [dayOfWeek, loadLatestDetail]);

  const loadComboCoverage = useCallback(async () => {
    setCoverageLoading(true);
    try {
      const res = await apiRequest('/api/v1/users/client/app/food-preferences/', { auth: true });
      if (res.ok) {
        setComboCoverage(buildComboCoverage(res.data?.food_preferences || {}));
      } else {
        setComboCoverage(null);
      }
    } catch (err) {
      console.error(err);
      setComboCoverage(null);
    } finally {
      setCoverageLoading(false);
    }
  }, []);

  useEffect(() => {
    loadComboCoverage().catch((err) => console.error(err));
  }, [loadComboCoverage]);

  useEffect(() => () => {
    if (weekPollTimeoutRef.current) {
      clearTimeout(weekPollTimeoutRef.current);
      weekPollTimeoutRef.current = null;
    }
  }, []);

  useEffect(() => {
    const mealCount = detail?.meals?.length || 0;
    if (mealCount === 0) {
      if (currentMealIndex !== 0) setCurrentMealIndex(0);
      return;
    }
    if (currentMealIndex >= mealCount) setCurrentMealIndex(0);
  }, [detail?.meals?.length, currentMealIndex]);

  const handleRunGeneration = async () => {
    setRunning(true);
    setError('');
    setMessage('');
    setGenerationResult(null);
    setGenerationWeekResult(null);
    setJobSnapshot(null);
    setRecipeIdeasResult(null);
    setRecipeIdeasError('');
    try {
      const res = await apiRequest('/api/v1/users/client/app/meal-plan-generation/run/', {
        method: 'POST',
        auth: true,
        body: { day_of_week: dayOfWeek },
      });
      if (res.status === 401) {
        navigate('/client_login', { replace: true });
        return;
      }
      if (!res.ok) {
        setError(res.data?.error?.message || 'Meal generation failed.');
        return;
      }
      const generation = res.data?.generation || null;
      setGenerationResult(generation);
      setMessage(res.data?.message || 'Meal generation completed.');
      await Promise.all([
        loadJobSnapshot(generation?.job_id),
        loadLatestDetail(dayOfWeek, generation?.job_id),
        loadComboCoverage(),
      ]);
    } catch (err) {
      console.error(err);
      setError('Network error while running meal generation.');
    } finally {
      setRunning(false);
    }
  };

  const handleRunWholeWeek = async () => {
    let queued = false;
    setRunning(true);
    setError('');
    setMessage('');
    setGenerationResult(null);
    setGenerationWeekResult(null);
    setJobSnapshot(null);
    setRecipeIdeasResult(null);
    setRecipeIdeasError('');
    if (weekPollTimeoutRef.current) {
      clearTimeout(weekPollTimeoutRef.current);
      weekPollTimeoutRef.current = null;
    }
    try {
      const res = await apiRequest('/api/v1/users/client/app/meal-plan-generation/run-week/', {
        method: 'POST',
        auth: true,
        body: {},
      });
      if (res.status === 401) {
        navigate('/client_login', { replace: true });
        return;
      }
      if (!res.ok) {
        setError(res.data?.error?.message || 'Weekly meal generation failed.');
        return;
      }
      const payload = res.data?.generation_week || null;
      queued = true;
      setGenerationWeekResult(payload);
      setMessage(res.data?.message || 'Weekly meal generation queued.');

      const batchId = payload?.batch_id;
      const requestedDays = payload?.days_requested || WEEK_DAYS;
      if (!batchId) return;

      const pollBatch = async () => {
        try {
          const query = requestedDays.map((d) => `day=${encodeURIComponent(d)}`).join('&');
          const statusRes = await apiRequest(
            `/api/v1/users/client/app/meal-plan-generation/run-week/${batchId}/status/${query ? `?${query}` : ''}`,
            { auth: true }
          );
          if (statusRes.status === 401) {
            navigate('/client_login', { replace: true });
            return;
          }
          if (!statusRes.ok) {
            setError(statusRes.data?.error?.message || 'Unable to poll weekly generation status.');
            return;
          }

          const batch = statusRes.data?.generation_week || null;
          setGenerationWeekResult(batch);

          const currentDayJob = (batch?.jobs || []).find((row) => row.day_of_week === dayOfWeek && row.job_id) || (batch?.jobs || []).find((row) => row.job_id);
          if (currentDayJob?.job_id) {
            await loadJobSnapshot(currentDayJob.job_id);
            if (currentDayJob.status === 'completed') {
              await loadLatestDetail(currentDayJob.day_of_week || dayOfWeek, currentDayJob.job_id);
            }
          }

          if (batch?.status === 'completed' || batch?.status === 'failed') {
            setRunning(false);
            if (batch.status === 'completed') {
              setMessage('Weekly meal generation completed.');
            }
            await loadComboCoverage();
            return;
          }
          weekPollTimeoutRef.current = setTimeout(pollBatch, 2000);
        } catch (err) {
          console.error(err);
          setError('Network error while polling weekly generation status.');
          setRunning(false);
        }
      };

      weekPollTimeoutRef.current = setTimeout(pollBatch, 1000);
      return;
    } catch (err) {
      console.error(err);
      setError('Network error while running weekly meal generation.');
    } finally {
      // keep running=true while background week batch is being polled
      if (!queued) setRunning(false);
    }
  };

  const selectedDayCoverage = comboCoverage?.byDay?.[dayOfWeek] || null;
  const runDayDisabled = running || coverageLoading || !selectedDayCoverage?.isComplete;
  const runWeekDisabled = running || coverageLoading || !comboCoverage?.isWeekComplete;

  const handleGenerateRecipeIdeas = async () => {
    if (!detail?.meals?.length) {
      setRecipeIdeasError('Load a generated meal plan first.');
      return;
    }
    setRecipeIdeasLoading(true);
    setRecipeIdeasError('');
    try {
      const res = await apiRequest(`/api/v1/users/client/app/meal-plan-days/${dayOfWeek}/recipe-ideas/`, {
        method: 'POST',
        auth: true,
        body: {
          job_id: detail?.job_id,
          provider: recipeIdeaProvider,
          ideas_per_meal: recipeIdeaCount,
        },
      });
      if (res.status === 401) {
        navigate('/client_login', { replace: true });
        return;
      }
      if (!res.ok) {
        setRecipeIdeasResult(null);
        setRecipeIdeasError(res.data?.error?.message || 'Unable to generate recipe ideas.');
        return;
      }
      setRecipeIdeasResult(res.data?.recipe_ideas || null);
    } catch (err) {
      console.error(err);
      setRecipeIdeasResult(null);
      setRecipeIdeasError('Network error while generating recipe ideas.');
    } finally {
      setRecipeIdeasLoading(false);
    }
  };

  const openPdfOrSetError = (config) => {
    const opened = openPrintPdfWindow(config);
    if (!opened) {
      setError('Unable to open the print window. Allow pop-ups, then try again to save as PDF.');
    }
  };

  const getCurrentMacroSnapshot = async () => {
    if (jobSnapshot?.job?.id === detail?.job_id && jobSnapshot?.input_snapshot?.day_payload) {
      return jobSnapshot;
    }
    if (!detail?.job_id) return jobSnapshot;
    const fresh = await loadJobSnapshot(detail.job_id);
    return fresh || jobSnapshot;
  };

  const handleExportMacrosPdf = async () => {
    if (!detail) {
      setError('Load a generated meal plan first.');
      return;
    }
    const snapshot = await getCurrentMacroSnapshot();
    openPdfOrSetError({
      title: `${prettyDay(detail.day_of_week)} Macros`,
      subtitle: 'Use your browser print dialog and choose "Save as PDF".',
      sections: [buildMacrosSectionHtml(snapshot, detail)],
    });
  };

  const handleExportFoodPlanPdf = () => {
    if (!detail?.meals?.length) {
      setError('Load a generated meal plan first.');
      return;
    }
    openPdfOrSetError({
      title: `${prettyDay(detail.day_of_week)} Food Plan`,
      subtitle: 'Use your browser print dialog and choose "Save as PDF".',
      sections: [buildFoodPlanSectionHtml(detail, unitMode)],
    });
  };

  const handleExportRecipesPdf = () => {
    if (!detail?.meals?.length) {
      setError('Load a generated meal plan first.');
      return;
    }
    if (!recipeIdeasResult?.meals?.length) {
      setRecipeIdeasError('Generate recipe ideas first to save the recipes PDF.');
      return;
    }
    openPdfOrSetError({
      title: `${prettyDay(detail.day_of_week)} Recipes`,
      subtitle: 'Use your browser print dialog and choose "Save as PDF".',
      sections: [buildRecipesSectionHtml(detail, recipeIdeasResult)],
    });
  };

  const handleExportCombinedPdf = async () => {
    if (!detail?.meals?.length) {
      setError('Load a generated meal plan first.');
      return;
    }
    if (!recipeIdeasResult?.meals?.length) {
      setRecipeIdeasError('Generate recipe ideas first to save the combined PDF.');
      return;
    }
    const snapshot = await getCurrentMacroSnapshot();
    openPdfOrSetError({
      title: `${prettyDay(detail.day_of_week)} Macros + Food Plan + Recipes`,
      subtitle: 'Use your browser print dialog and choose "Save as PDF".',
      sections: [
        buildMacrosSectionHtml(snapshot, detail),
        buildFoodPlanSectionHtml(detail, unitMode),
        buildRecipesSectionHtml(detail, recipeIdeasResult),
      ],
    });
  };

  return (
    <div className="client-dashboard-page">
      <header className="client-dashboard-header">
        <div>
          <h1>Meal Plan Generation</h1>
          <p className="client-dash-muted">
            Run the 10-step food plan algorithm for a selected day and inspect the final detailed meal output.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <Link className="client-q-btn secondary" to="/client_dashboard">Back to Dashboard</Link>
          <Link className="client-q-btn secondary" to="/client_food_preferences">Food Preferences</Link>
          <button type="button" className="client-q-btn danger" onClick={() => logout('/client_login')}>
            Log Out
          </button>
        </div>
      </header>

      <section
        className="client-dashboard-card"
        style={{
          background: 'linear-gradient(135deg, rgba(20,40,74,0.98), rgba(28,103,160,0.92))',
          color: '#fff',
          border: '1px solid rgba(20,40,74,0.15)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <h2 style={{ margin: 0, color: '#fff' }}>Your Food Plan Engine</h2>
            <p style={{ margin: '0.45rem 0 0', color: 'rgba(255,255,255,0.85)' }}>
              Generate the day plan, review foods, create recipe ideas, and export your PDFs from this workflow.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button type="button" className="client-q-btn" onClick={() => navigate('/client_exports')}>
              Open Export Center
            </button>
            <button type="button" className="client-q-btn secondary" onClick={() => loadLatestDetail(dayOfWeek)}>
              Load Latest {prettyDay(dayOfWeek)}
            </button>
          </div>
        </div>
      </section>

      <section className="client-dashboard-card">
        <h2>Run Generation</h2>
        <div className="client-q-stack" style={{ marginTop: '0.75rem' }}>
          <div className="client-q-inline-grid">
            <label>
              Day
              <select value={dayOfWeek} onChange={(e) => setDayOfWeek(e.target.value)} disabled={running}>
                {WEEK_DAYS.map((day) => (
                  <option key={day} value={day}>{prettyDay(day)}</option>
                ))}
              </select>
            </label>
            <label>
              Display Units
              <select value={unitMode} onChange={(e) => setUnitMode(e.target.value)}>
                <option value="oz">Ounces</option>
                <option value="g">Grams</option>
              </select>
            </label>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button type="button" className="client-q-btn" onClick={handleRunGeneration} disabled={runDayDisabled}>
              {running ? 'Running Steps 1-10…' : `Run ${prettyDay(dayOfWeek)} Generation`}
            </button>
            <button type="button" className="client-q-btn" onClick={handleRunWholeWeek} disabled={runWeekDisabled}>
              {running ? 'Running Week…' : 'Run Whole Week'}
            </button>
            <button type="button" className="client-q-btn secondary" onClick={() => loadLatestDetail(dayOfWeek)} disabled={loadingDetail || running}>
              {loadingDetail ? 'Loading…' : 'Load Latest Detailed Plan'}
            </button>
          </div>
          {!coverageLoading && selectedDayCoverage && !selectedDayCoverage.isComplete ? (
            <p className="client-dash-muted" style={{ marginTop: '0.2rem' }}>
              {prettyDay(dayOfWeek)} is incomplete: {selectedDayCoverage.matched}/{selectedDayCoverage.expected} meals have combo IDs.
            </p>
          ) : null}
          {!coverageLoading && comboCoverage && !comboCoverage.isWeekComplete ? (
            <p className="client-dash-muted" style={{ marginTop: '0.2rem' }}>
              Whole-week run is locked until all days have full combo selections saved in Food Preferences.
            </p>
          ) : null}
          {message ? <p className="client-q-message">{message}</p> : null}
          {error ? <p className="client-q-error">{error}</p> : null}
        </div>
      </section>

      {(generationResult || jobSnapshot?.job) && (
        <section className="client-dashboard-card">
          <h2>Generation Status</h2>
          <div className="client-dash-chips" style={{ marginTop: '0.75rem' }}>
            {generationResult?.job_id ? <span>Job #{generationResult.job_id}</span> : null}
            {(jobSnapshot?.job?.status || generationResult?.status) ? <span>Status: {jobSnapshot?.job?.status || generationResult?.status}</span> : null}
            <span>Step: {jobSnapshot?.job?.current_step ?? generationResult?.current_step ?? '-'}/10</span>
            <span>Progress: {jobSnapshot?.job?.progress_percent ?? generationResult?.progress_percent ?? 0}%</span>
            {generationResult?.generated_meal_count != null ? <span>Meals: {generationResult.generated_meal_count}</span> : null}
          </div>
          {generationResult?.note ? (
            <p className="client-dash-muted" style={{ marginTop: '0.5rem' }}>{generationResult.note}</p>
          ) : null}
          {jobSnapshot?.input_snapshot?.parameter_settings ? (
            <p className="client-dash-muted" style={{ marginTop: '0.25rem' }}>
              Parameter source: {jobSnapshot.input_snapshot.parameter_settings.source} ({jobSnapshot.input_snapshot.parameter_settings.defaults_version || 'v1'})
            </p>
          ) : null}
        </section>
      )}

      {generationWeekResult?.jobs?.length ? (
        <section className="client-dashboard-card">
          <h2>Weekly Run Summary</h2>
          <div style={{ overflowX: 'auto', marginTop: '0.75rem' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 760 }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Day</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Job</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Status</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Step1 Rows</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Meals</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Open</th>
                </tr>
              </thead>
              <tbody>
                {generationWeekResult.jobs.map((row) => (
                  <tr key={`week-job-${row.day_of_week}-${row.job_id}`}>
                    <td style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>{prettyDay(row.day_of_week)}</td>
                    <td style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>#{row.job_id}</td>
                    <td style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>{row.status}</td>
                    <td style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>{row.step1_row_count}</td>
                    <td style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>{row.generated_meal_count}</td>
                    <td style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>
                      <button
                        type="button"
                        className="client-q-btn secondary"
                        onClick={async () => {
                          setDayOfWeek(row.day_of_week);
                          await Promise.all([loadJobSnapshot(row.job_id), loadLatestDetail(row.day_of_week, row.job_id)]);
                        }}
                      >
                        View Day
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {generationWeekResult?.batch_id ? (
            <div className="client-dash-chips" style={{ marginTop: '0.5rem' }}>
              <span>Batch: {generationWeekResult.batch_id}</span>
              <span>Batch Status: {generationWeekResult.status || '-'}</span>
              <span>{(generationWeekResult.days_completed || []).length}/{(generationWeekResult.days_requested || []).length} days completed</span>
            </div>
          ) : null}
          <p className="client-dash-muted" style={{ marginTop: '0.5rem' }}>
            {generationWeekResult.note}
          </p>
        </section>
      ) : null}

      <section className="client-dashboard-card">
        <h2>{prettyDay(dayOfWeek)} Detailed Meal Plan</h2>
        {!detail ? (
          <p className="client-dash-muted" style={{ marginTop: '0.75rem' }}>
            Run generation or load the latest detailed plan for this day.
          </p>
        ) : (
          <div className="client-q-stack" style={{ marginTop: '0.75rem' }}>
            <div className="client-dash-chips">
              <span>Job #{detail.job_id}</span>
              <span>Status: {detail.job_status || '-'}</span>
              <span>Progress: {detail.progress_percent ?? 0}%</span>
              <span>{detail.meals_per_day || detail.meals?.length || 0} meals</span>
              <span>{formatTrainingLabel(detail.training_time)}</span>
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'end' }}>
              <label>
                Recipe Provider
                <select value={recipeIdeaProvider} onChange={(e) => setRecipeIdeaProvider(e.target.value)} disabled={recipeIdeasLoading}>
                  <option value="auto">Auto (OpenAI if configured, otherwise mock)</option>
                  <option value="mock">Mock (free test mode)</option>
                  <option value="openai">OpenAI API (requires backend key)</option>
                </select>
              </label>
              <label>
                Ideas Per Meal
                <select value={recipeIdeaCount} onChange={(e) => setRecipeIdeaCount(Number(e.target.value) || 3)} disabled={recipeIdeasLoading}>
                  <option value={1}>1</option>
                  <option value={2}>2</option>
                  <option value={3}>3</option>
                  <option value={4}>4</option>
                  <option value={5}>5</option>
                </select>
              </label>
              <button type="button" className="client-q-btn secondary" onClick={handleGenerateRecipeIdeas} disabled={recipeIdeasLoading}>
                {recipeIdeasLoading ? 'Generating Recipe Ideas…' : 'Get Recipe Ideas'}
              </button>
              <button type="button" className="client-q-btn secondary" onClick={handleExportMacrosPdf} disabled={!detail}>
                Save Macros PDF
              </button>
              <button type="button" className="client-q-btn secondary" onClick={handleExportFoodPlanPdf} disabled={!detail?.meals?.length}>
                Save Food Plan PDF
              </button>
              <button
                type="button"
                className="client-q-btn secondary"
                onClick={handleExportRecipesPdf}
                disabled={!detail?.meals?.length || !recipeIdeasResult?.meals?.length}
              >
                Save Recipes PDF
              </button>
              <button
                type="button"
                className="client-q-btn"
                onClick={handleExportCombinedPdf}
                disabled={!detail?.meals?.length || !recipeIdeasResult?.meals?.length}
              >
                Save Combined PDF
              </button>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                <img
                  src={aiLogo}
                  alt="AI"
                  style={{ width: 22, height: 22, objectFit: 'contain' }}
                />
                <span className="client-dash-muted">AI-assisted</span>
              </span>
              {recipeIdeasResult?.provider_used ? (
                <span className="client-dash-muted">
                  Provider: {recipeIdeasResult.provider_used} ({recipeIdeasResult.model || 'n/a'})
                </span>
              ) : null}
              {recipeIdeasResult?.provider_requested === 'auto' && recipeIdeasResult?.provider_used === 'mock' ? (
                <span className="client-dash-muted">
                  OpenAI not configured/reachable, so mock mode was used.
                </span>
              ) : null}
            </div>
            {recipeIdeasError ? <p className="client-q-error">{recipeIdeasError}</p> : null}

            <div style={{ marginBottom: '0.7rem' }}>
              <button
                type="button"
                className="client-q-btn secondary"
                onClick={() => setShowAllMeals((prev) => !prev)}
                style={{ marginRight: 8 }}
              >
                {showAllMeals ? 'Show One Meal' : 'Show All Meals'}
              </button>
              {!showAllMeals && (detail.meals?.length > 1) && (
                <>
                  <button
                    type="button"
                    className="client-q-btn secondary"
                    onClick={() => setCurrentMealIndex((i) => Math.max(0, i - 1))}
                    disabled={currentMealIndex === 0}
                    style={{ marginRight: 4 }}
                  >
                    Previous Meal
                  </button>
                  <button
                    type="button"
                    className="client-q-btn secondary"
                    onClick={() => setCurrentMealIndex((i) => Math.min(detail.meals.length - 1, i + 1))}
                    disabled={currentMealIndex === detail.meals.length - 1}
                  >
                    Next Meal
                  </button>
                </>
              )}
              {!showAllMeals && (detail.meals?.length > 0) && (
                <span
                  className="client-dash-muted"
                  style={{ marginLeft: 10, fontWeight: 600 }}
                >
                  Viewing Meal {currentMealIndex + 1} of {detail.meals.length}
                  {detail.meals?.[currentMealIndex]?.meal_number != null
                    ? ` (Meal ${detail.meals[currentMealIndex].meal_number})`
                    : ''}
                </span>
              )}
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 980 }}>
                {showAllMeals && (
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Meal</th>
                      <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Combo ID</th>
                      <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Protein 1</th>
                      <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Protein 2</th>
                      <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Carbs 1</th>
                      <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Carbs 2</th>
                      <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Fats 1</th>
                      <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.12)' }}>Fats 2</th>
                    </tr>
                  </thead>
                )}
                <tbody>
                  {showAllMeals
                    ? (detail.meals || []).map((meal) => (
                        <tr key={`detail-${meal.meal_number}`}>
                          <td style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>Meal {meal.meal_number}</td>
                          <td style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>{meal.combo_id}</td>
                          {['protein_1', 'protein_2', 'carbs_1', 'carbs_2', 'fats_1', 'fats_2'].map((slotKey) => {
                            const slot = meal.slots?.[slotKey];
                            return (
                              <td key={`${meal.meal_number}-${slotKey}`} style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>
                                <FoodSlotCell slot={slot} unitMode={unitMode} />
                              </td>
                            );
                          })}
                        </tr>
                      ))
                    : (() => {
                        const meal = (detail.meals || [])[currentMealIndex] || null;
                        if (!meal) return null;
                        // Gather foods and measurements for each macro
                        const macroGroups = [
                          {
                            label: 'Protein',
                            slots: [meal.slots?.protein_1, meal.slots?.protein_2],
                          },
                          {
                            label: 'Carbs',
                            slots: [meal.slots?.carbs_1, meal.slots?.carbs_2],
                          },
                          {
                            label: 'Fats',
                            slots: [meal.slots?.fats_1, meal.slots?.fats_2],
                          },
                        ];
                        return (
                          <tr key={`detail-${meal.meal_number}`}>
                            <td colSpan={8} style={{ padding: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)' }}>
                              <div style={{ display: 'flex', flexDirection: 'row', gap: '2.5rem', alignItems: 'flex-start' }}>
                                {macroGroups.map((group) => {
                                  // Only show sources that are not empty, not named 'None', and have a nonzero amount
                                  const sources = group.slots.filter((slot) => {
                                    if (!slot) return false;
                                    if (!slot.name || slot.name.toLowerCase() === 'none') return false;
                                    // Check for zero amount (oz or g)
                                    const amount = slot.amount_oz ?? slot.amount_g ?? 0;
                                    if (!amount || amount === 0) return false;
                                    return true;
                                  });
                                  if (sources.length === 0) return null;
                                  return (
                                    <div key={group.label} style={{ minWidth: 120 }}>
                                      <div style={{ fontWeight: 600, marginBottom: 4 }}>{group.label}</div>
                                      {sources.map((slot, idx) => (
                                        <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                                          <FoodSlotCell slot={slot} unitMode={unitMode} />
                                          <span style={{ fontSize: '0.95em', color: '#444', marginLeft: 2 }}>{amountLabel(slot, unitMode)}</span>
                                        </div>
                                      ))}
                                    </div>
                                  );
                                })}
                              </div>
                            </td>
                          </tr>
                        );
                      })()
                  }
                  {(!detail.meals || detail.meals.length === 0) && (
                    <tr>
                      <td colSpan={8} style={{ padding: '0.75rem' }}>No generated rows found for this day.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {recipeIdeasResult?.meals?.length ? (
              <div style={{ display: 'grid', gap: '0.9rem' }}>
                <h3 style={{ margin: 0 }}>Recipe Ideas</h3>
                {(detail.meals || []).map((meal) => {
                  const recipeMeal = (recipeIdeasResult.meals || []).find((row) => row.meal_number === meal.meal_number);
                  return <RecipeIdeasMealCard key={`recipe-card-${meal.meal_number}`} meal={meal} recipeMeal={recipeMeal} />;
                })}
              </div>
            ) : null}
          </div>
        )}
      </section>

    </div>
  );
}
export default ClientMealPlanGenerationPage;
