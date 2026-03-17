import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../../../api/client';
import './AdminParameterSettingsPage.css';

const SUBDOMAIN_RE = /^[a-z]+(?:-[a-z]+)*$/;

function normalizeSubdomain(value) {
  return String(value || '').trim().toLowerCase().replace(/\s+/g, '');
}

function validateSubdomainSlug(value, { required = true } = {}) {
  const slug = normalizeSubdomain(value);
  if (!slug && !required) return '';
  if (!slug) return 'Subdomain is required.';
  if (slug.length < 3 || slug.length > 40) return 'Subdomain must be between 3 and 40 characters.';
  if (!SUBDOMAIN_RE.test(slug)) return 'Use only letters and hyphens (no spaces, numbers, or underscores).';
  return '';
}

function setNestedValue(obj, path, value) {
  const next = JSON.parse(JSON.stringify(obj || {}));
  let cursor = next;
  for (let i = 0; i < path.length - 1; i += 1) {
    const key = path[i];
    if (!cursor[key] || typeof cursor[key] !== 'object') cursor[key] = {};
    cursor = cursor[key];
  }
  cursor[path[path.length - 1]] = value;
  return next;
}

function AdminParameterSettingsPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState('loading');
  const [saveStatus, setSaveStatus] = useState('idle');
  const [message, setMessage] = useState('');
  const [selectedMealCount, setSelectedMealCount] = useState('meals_3');
  const [mealEditorPlanType, setMealEditorPlanType] = useState('standard');
  const [carbCyclingVariant, setCarbCyclingVariant] = useState('low_carbs');
  const [selectedScenario, setSelectedScenario] = useState('no_training');
  const [selectedTdeeLifestyle, setSelectedTdeeLifestyle] = useState('low_active');
  const [selectedTdeeTrainingDays, setSelectedTdeeTrainingDays] = useState('1');
  const [selectedCorePlanType, setSelectedCorePlanType] = useState('standard');
  const [selectedCoreGoal, setSelectedCoreGoal] = useState('lose');
  const [metadata, setMetadata] = useState(null);
  const [parsedSettings, setParsedSettings] = useState(null);
  const [savedSettingsSnapshot, setSavedSettingsSnapshot] = useState(null);
  const [subdomainInfo, setSubdomainInfo] = useState(null);
  const [savedSubdomainSlug, setSavedSubdomainSlug] = useState('');
  const [subdomainInput, setSubdomainInput] = useState('');
  const [subdomainError, setSubdomainError] = useState('');

  const syncSettings = (nextSettings) => {
    setParsedSettings(nextSettings);
  };

  const updateNumberField = (path, rawValue) => {
    const parsed = Number(rawValue);
    if (!Number.isFinite(parsed)) return;
    const next = setNestedValue(parsedSettings || {}, path, parsed);
    syncSettings(next);
  };

  const updateLockedPercentPair = ({ carbPath, fatPath, changedKey, rawValue }) => {
    const parsed = Number(rawValue);
    if (!Number.isFinite(parsed)) return;

    const clamped = Math.min(100, Math.max(0, parsed));
    const roundedPrimary = Number(clamped.toFixed(3));
    const roundedOther = Number((100 - clamped).toFixed(3));

    const next = JSON.parse(JSON.stringify(parsedSettings || {}));
    let cursor = next;

    const applyAtPath = (path, value) => {
      let node = cursor;
      for (let i = 0; i < path.length - 1; i += 1) {
        const key = path[i];
        if (!node[key] || typeof node[key] !== 'object') node[key] = {};
        node = node[key];
      }
      node[path[path.length - 1]] = value;
    };

    if (changedKey === 'carb') {
      applyAtPath(carbPath, roundedPrimary);
      applyAtPath(fatPath, roundedOther);
    } else {
      applyAtPath(fatPath, roundedPrimary);
      applyAtPath(carbPath, roundedOther);
    }

    syncSettings(next);
  };

  useEffect(() => {
    let ignore = false;

    const load = async () => {
      try {
        const res = await apiRequest('/api/v1/users/admin/parameter_settings/', { auth: true });
        if (ignore) return;
        if (res.status === 401) {
          navigate('/admin_login');
          return;
        }
        if (!res.ok) {
          setStatus('error');
          setMessage(res.data?.error?.message || 'Unable to load admin parameter settings.');
          return;
        }

        const payload = res.data?.parameter_settings || {};
        setMetadata({
          initialized: Boolean(payload.initialized),
          setupCompleted: Boolean(payload.setup_completed),
          defaultsVersionApplied: payload.defaults_version_applied || 'v1',
          updatedAt: payload.updated_at || null,
        });
        const fetchedSubdomain = res.data?.subdomain || null;
        const slugValue = fetchedSubdomain?.slug || '';
        setSubdomainInfo(fetchedSubdomain);
        setSavedSubdomainSlug(fetchedSubdomain?.slug || '');
        setSubdomainInput(slugValue);
        setSubdomainError('');
        const loadedSettings = payload.parameters_json || {};
        setParsedSettings(loadedSettings);
        setSavedSettingsSnapshot(loadedSettings);
        setStatus('ready');
      } catch (err) {
        console.error('parameter settings load error', err);
        if (!ignore) {
          setStatus('error');
          setMessage('Network error while loading admin parameter settings.');
        }
      }
    };

    load();
    return () => { ignore = true; };
  }, [navigate]);

  const goalAdjustments = parsedSettings?.goal_calorie_adjustments || {};
  const mealPlans = parsedSettings?.meal_plans || {};
  const standardMacroRules = mealPlans.standard?.macro_rules_by_goal || {};
  const ketoMacroRules = mealPlans.keto?.macro_rules_by_goal || {};
  const carbCyclingMacroRules = mealPlans.carb_cycling?.macro_rules_by_goal || {};
  const tdee = parsedSettings?.tdee || {};
  const categoryMultipliers = tdee.category_multipliers || {};
  const categoryMapping = tdee.category_mapping_by_lifestyle_and_training_days || {};
  const weeklySplits = tdee.weekly_day_multiplier_splits || {};

  const tdeeLifestyleOptions = ['low_active', 'middle_active', 'high_active'];
  const trainingDayOptions = ['1', '2', '3', '4', '5', '6', '7'];

  const selectedWeeklyTable = (
    weeklySplits?.[selectedTdeeLifestyle]?.tables_by_training_days_per_week?.[selectedTdeeTrainingDays]
    || {}
  );
  const selectedWeeklyDayMultipliers = Array.isArray(selectedWeeklyTable.day_multipliers)
    ? selectedWeeklyTable.day_multipliers
    : [];
  const selectedTrainingDayCount = Number(selectedTdeeTrainingDays || 0);
  const selectedWeeklyAverage = selectedWeeklyDayMultipliers.length
    ? (selectedWeeklyDayMultipliers.reduce((sum, value) => sum + Number(value || 0), 0) / selectedWeeklyDayMultipliers.length)
    : 0;
  const selectedWeeklyCategoryKey = String(selectedWeeklyTable.category ?? '');
  const selectedWeeklyTargetMultiplier = Number(categoryMultipliers[selectedWeeklyCategoryKey] || 0);
  const weeklyDayRoleLabels = useMemo(() => {
    const values = (selectedWeeklyDayMultipliers || []).map((value, index) => ({
      index,
      value: Number(value || 0),
    }));
    if (!values.length) return [];

    const workoutCount = Math.max(0, Math.min(7, Math.round(selectedTrainingDayCount || 0)));
    if (workoutCount === 0) {
      return values.map(() => 'off');
    }

    // Highest multipliers represent workout days. We select the top N based on the chosen training-day count.
    const ranked = [...values].sort((a, b) => {
      if (b.value !== a.value) return b.value - a.value;
      return a.index - b.index;
    });
    const workoutIndexes = new Set(ranked.slice(0, workoutCount).map((entry) => entry.index));
    return values.map(({ index }) => (workoutIndexes.has(index) ? 'workout' : 'off'));
  }, [selectedWeeklyDayMultipliers, selectedTrainingDayCount]);

  const mealEditorScenarios = useMemo(() => {
    if (!parsedSettings) return {};
    const root = parsedSettings?.meal_plans || {};
    if (mealEditorPlanType === 'carb_cycling') {
      return root.carb_cycling?.meal_macro_distribution?.[selectedMealCount]?.[carbCyclingVariant] || {};
    }
    return root?.[mealEditorPlanType]?.meal_macro_distribution?.[selectedMealCount] || {};
  }, [parsedSettings, mealEditorPlanType, selectedMealCount, carbCyclingVariant]);

  const mealEditorScenarioKeys = useMemo(
    () => Object.keys(mealEditorScenarios || {}),
    [mealEditorScenarios]
  );

  useEffect(() => {
    if (!mealEditorScenarioKeys.length) return;
    if (!mealEditorScenarioKeys.includes(selectedScenario)) {
      setSelectedScenario(mealEditorScenarioKeys.includes('no_training') ? 'no_training' : mealEditorScenarioKeys[0]);
    }
  }, [mealEditorScenarioKeys, selectedScenario]);

  const mealEditorCurrentScenario = mealEditorScenarios?.[selectedScenario] || {};
  const mealEditorMealKeys = Object.keys(mealEditorCurrentScenario || {}).sort((a, b) => {
    const aNum = Number(String(a).replace('meal_', ''));
    const bNum = Number(String(b).replace('meal_', ''));
    return aNum - bNum;
  });

  const mealEditorPathPrefix = useMemo(() => {
    if (mealEditorPlanType === 'carb_cycling') {
      return ['meal_plans', 'carb_cycling', 'meal_macro_distribution', selectedMealCount, carbCyclingVariant, selectedScenario];
    }
    return ['meal_plans', mealEditorPlanType, 'meal_macro_distribution', selectedMealCount, selectedScenario];
  }, [mealEditorPlanType, selectedMealCount, carbCyclingVariant, selectedScenario]);

  const mealColumnTotals = useMemo(() => {
    const totals = { protein: 0, carbs: 0, fats: 0 };
    mealEditorMealKeys.forEach((mealKey) => {
      const row = mealEditorCurrentScenario?.[mealKey] || {};
      totals.protein += Number(row.protein || 0);
      totals.carbs += Number(row.carbs || 0);
      totals.fats += Number(row.fats || 0);
    });
    return totals;
  }, [mealEditorCurrentScenario, mealEditorMealKeys]);

  const normalizedSubdomain = normalizeSubdomain(subdomainInput);
  const currentSubdomainLocked = Boolean(subdomainInfo?.locked);
  const isSubdomainRequired = subdomainInfo?.required !== false;

  const handleUseDefaults = async () => {
    const clientSubdomainError = currentSubdomainLocked
      ? ''
      : validateSubdomainSlug(subdomainInput, { required: isSubdomainRequired });
    if (clientSubdomainError) {
      setSaveStatus('error');
      setSubdomainError(clientSubdomainError);
      setMessage(clientSubdomainError);
      return;
    }

    try {
      setSaveStatus('saving');
      setMessage('');
      const res = await apiRequest('/api/v1/users/admin/parameter_settings/use_defaults/', {
        method: 'POST',
        auth: true,
        body: {
          subdomain_slug: normalizedSubdomain || null,
        },
      });
      if (res.status === 401) {
        navigate('/admin_login');
        return;
      }
      if (!res.ok) {
        setSaveStatus('error');
        const apiMessage = res.data?.error?.message || 'Unable to apply DTA defaults.';
        setMessage(apiMessage);
        if ((res.data?.error?.code || '') === 'INVALID_SUBDOMAIN_SLUG') {
          setSubdomainError(apiMessage);
        }
        return;
      }

      const reload = await apiRequest('/api/v1/users/admin/parameter_settings/', { auth: true });
      if (reload.ok) {
        const payload = reload.data?.parameter_settings || {};
        setMetadata({
          initialized: Boolean(payload.initialized),
          setupCompleted: Boolean(payload.setup_completed),
          defaultsVersionApplied: payload.defaults_version_applied || 'v1',
          updatedAt: payload.updated_at || null,
        });
        const nextSubdomain = reload.data?.subdomain || null;
        setSubdomainInfo(nextSubdomain);
        setSavedSubdomainSlug(nextSubdomain?.slug || '');
        setSubdomainInput(nextSubdomain?.slug || '');
        setSubdomainError('');
        const loadedSettings = payload.parameters_json || {};
        setParsedSettings(loadedSettings);
        setSavedSettingsSnapshot(loadedSettings);
      }
      setSaveStatus('success');
      setMessage('DTA v1 defaults applied.');
    } catch (err) {
      console.error('apply defaults error', err);
      setSaveStatus('error');
      setMessage('Network error while applying defaults.');
    }
  };

  const handleSave = async () => {
    const wasInitialized = Boolean(metadata?.initialized);
    const parsed = parsedSettings;
    if (!parsed || typeof parsed !== 'object') {
      setSaveStatus('error');
      setMessage('Nothing to save.');
      return;
    }

    const clientSubdomainError = currentSubdomainLocked
      ? ''
      : validateSubdomainSlug(subdomainInput, { required: isSubdomainRequired });
    if (clientSubdomainError) {
      setSaveStatus('error');
      setSubdomainError(clientSubdomainError);
      setMessage(clientSubdomainError);
      return;
    }

    try {
      setSaveStatus('saving');
      setMessage('');
      const res = await apiRequest('/api/v1/users/admin/parameter_settings/', {
        method: 'PUT',
        auth: true,
        body: {
          parameters_json: parsed,
          initialized: true,
          subdomain_slug: normalizedSubdomain || null,
        },
      });
      if (res.status === 401) {
        navigate('/admin_login');
        return;
      }
      if (!res.ok) {
        setSaveStatus('error');
        const apiMessage = res.data?.error?.message || 'Unable to save admin parameter settings.';
        setMessage(apiMessage);
        if ((res.data?.error?.code || '') === 'INVALID_SUBDOMAIN_SLUG') {
          setSubdomainError(apiMessage);
        }
        return;
      }

      const payload = res.data?.parameter_settings || {};
      const savedSettings = payload.parameters_json || parsed;
      setParsedSettings(savedSettings);
      setSavedSettingsSnapshot(savedSettings);
      setMetadata((prev) => ({
        initialized: Boolean(payload.initialized ?? prev?.initialized),
        setupCompleted: Boolean(payload.setup_completed ?? prev?.setupCompleted),
        defaultsVersionApplied: payload.defaults_version_applied || prev?.defaultsVersionApplied || 'v1',
        updatedAt: payload.updated_at || prev?.updatedAt || null,
      }));
      const returnedSubdomain = res.data?.subdomain || null;
      setSubdomainInfo(returnedSubdomain);
      setSavedSubdomainSlug(returnedSubdomain?.slug || normalizedSubdomain);
      setSubdomainInput(returnedSubdomain?.slug || normalizedSubdomain);
      setSubdomainError('');
      setSaveStatus('success');
      const changedCount = typeof payload.changed_paths_count === 'number' ? payload.changed_paths_count : null;
      if (wasInitialized) {
        setMessage(
          changedCount == null
            ? 'Admin parameter settings updated.'
            : `Admin parameter settings updated. ${changedCount} change(s) recorded.`
        );
      } else {
        setMessage(
          changedCount == null
            ? 'Admin parameter settings approved.'
            : `Admin parameter settings approved. ${changedCount} change(s) recorded.`
        );
      }
    } catch (err) {
      console.error('save parameter settings error', err);
      setSaveStatus('error');
      setMessage('Network error while saving admin parameter settings.');
    }
  };

  const hasUnsavedChanges = useMemo(() => {
    const normalizedCurrentSubdomain = normalizeSubdomain(subdomainInput);
    const normalizedSavedSubdomain = normalizeSubdomain(savedSubdomainSlug);
    const subdomainDirty = !subdomainInfo?.locked && normalizedCurrentSubdomain !== normalizedSavedSubdomain;

    if (!parsedSettings || !savedSettingsSnapshot) return subdomainDirty;
    try {
      return subdomainDirty || JSON.stringify(parsedSettings) !== JSON.stringify(savedSettingsSnapshot);
    } catch {
      return subdomainDirty;
    }
  }, [parsedSettings, savedSettingsSnapshot, subdomainInput, savedSubdomainSlug, subdomainInfo]);
  const requiresInitialApproval = Boolean(metadata && !metadata.setupCompleted);
  const hasPendingAction = requiresInitialApproval || hasUnsavedChanges;
  const clientSubdomainValidationError = currentSubdomainLocked
    ? ''
    : validateSubdomainSlug(subdomainInput, { required: isSubdomainRequired });
  const effectiveSubdomainError = subdomainError || clientSubdomainValidationError;
  const saveButtonDisabled = saveStatus === 'saving' || !hasPendingAction || Boolean(effectiveSubdomainError);

  const handleMealBreakdownCellChange = (mealKey, macroKey, rawValue) => {
    const parsed = Number(rawValue);
    if (!Number.isFinite(parsed)) return;
    const next = setNestedValue(parsedSettings || {}, [...mealEditorPathPrefix, mealKey, macroKey], parsed);
    syncSettings(next);
  };

  const handleCategoryMultiplierChange = (categoryKey, rawValue) => {
    updateNumberField(['tdee', 'category_multipliers', categoryKey], rawValue);
  };

  const handleCategoryMappingChange = (lifestyleKey, trainingDaysKey, rawValue) => {
    const parsed = Number(rawValue);
    if (!Number.isFinite(parsed)) return;
    const clamped = Math.min(7, Math.max(1, Math.round(parsed)));
    const next = setNestedValue(
      parsedSettings || {},
      ['tdee', 'category_mapping_by_lifestyle_and_training_days', lifestyleKey, trainingDaysKey],
      clamped
    );
    syncSettings(next);
  };

  const handleWeeklyTableCategoryChange = (rawValue) => {
    const parsed = Number(rawValue);
    if (!Number.isFinite(parsed)) return;
    const clamped = Math.min(7, Math.max(1, Math.round(parsed)));
    const next = setNestedValue(
      parsedSettings || {},
      ['tdee', 'weekly_day_multiplier_splits', selectedTdeeLifestyle, 'tables_by_training_days_per_week', selectedTdeeTrainingDays, 'category'],
      clamped
    );
    syncSettings(next);
  };

  const handleWeeklyDayMultiplierChange = (dayIndex, rawValue) => {
    const parsed = Number(rawValue);
    if (!Number.isFinite(parsed)) return;
    const next = setNestedValue(
      parsedSettings || {},
      ['tdee', 'weekly_day_multiplier_splits', selectedTdeeLifestyle, 'tables_by_training_days_per_week', selectedTdeeTrainingDays, 'day_multipliers', dayIndex],
      parsed
    );
    syncSettings(next);
  };

  const corePlanLabel = selectedCorePlanType === 'carb_cycling'
    ? 'Carb Cycling'
    : selectedCorePlanType.charAt(0).toUpperCase() + selectedCorePlanType.slice(1);
  const coreGoalLabel = selectedCoreGoal.replace('_', ' ');
  const selectedStandardRule = standardMacroRules[selectedCoreGoal] || {};
  const selectedKetoRule = ketoMacroRules[selectedCoreGoal] || {};
  const selectedCarbCyclingRule = carbCyclingMacroRules[selectedCoreGoal] || {};
  const selectedCarbCyclingLow = selectedCarbCyclingRule.low_day || {};
  const selectedCarbCyclingHigh = selectedCarbCyclingRule.high_day || {};
  const selectedStandardTotal = Number(selectedStandardRule.carb_percent || 0) + Number(selectedStandardRule.fat_percent || 0);
  const selectedKetoTotal = Number(selectedKetoRule.carb_percent || 0) + Number(selectedKetoRule.fat_percent || 0);
  const selectedCarbLowTotal = Number(selectedCarbCyclingLow.carb_percent || 0) + Number(selectedCarbCyclingLow.fat_percent || 0);
  const selectedCarbHighTotal = Number(selectedCarbCyclingHigh.carb_percent || 0) + Number(selectedCarbCyclingHigh.fat_percent || 0);

  if (status === 'loading') {
    return <div className="admin-params-page"><p className="admin-params-muted">Loading admin parameter settings…</p></div>;
  }

  if (status === 'error') {
    return (
      <div className="admin-params-page">
        <p className="admin-params-error">{message || 'Unable to load admin parameter settings.'}</p>
        <button className="admin-params-btn" onClick={() => navigate('/admin_dashboard')} type="button">Back to Dashboard</button>
      </div>
    );
  }

  return (
    <div className="admin-params-page">
      <header className="admin-params-header">
        <div>
          <h1 className="admin-params-title">Admin Parameter Settings</h1>
          <p className="admin-params-muted">
            Edit your default macro/TDEE logic. These values are used as your admin-level defaults.
          </p>
        </div>
        <div className="admin-params-meta">
          <span>Initialized: {metadata?.initialized ? 'Yes' : 'No'}</span>
          <span>Setup Complete: {metadata?.setupCompleted ? 'Yes' : 'No'}</span>
          <span>Defaults: {metadata?.defaultsVersionApplied || 'v1'}</span>
          <span>Updated: {metadata?.updatedAt ? new Date(metadata.updatedAt).toLocaleString() : '—'}</span>
        </div>
      </header>

      <section className="admin-params-card">
        <div className="admin-params-actions">
          <button
            className="admin-params-btn"
            onClick={handleUseDefaults}
            disabled={saveStatus === 'saving'}
            type="button"
          >
            Use DTA Defaults
          </button>
          <button className="admin-params-btn" onClick={() => navigate('/admin_dashboard')} type="button">
            Back to Dashboard
          </button>
          <button
            className="admin-params-btn admin-params-btn-primary"
            onClick={handleSave}
            disabled={saveButtonDisabled}
            type="button"
          >
            {saveStatus === 'saving'
              ? (requiresInitialApproval ? 'Approving…' : 'Updating…')
              : (hasPendingAction
                  ? (requiresInitialApproval ? 'Approve Parameters' : 'Update Parameters')
                  : 'No Pending Changes')}
          </button>
        </div>
        {message && (
          <p className={saveStatus === 'error' ? 'admin-params-error' : 'admin-params-success'}>
            {message}
          </p>
        )}
      </section>

      <section className="admin-params-card">
        <h2 className="admin-params-section-title">Subdomain</h2>
        <p className="admin-params-muted">
          {isSubdomainRequired
            ? 'Your branded subdomain is required and locks after it is first saved.'
            : 'Subdomain is optional for this admin account type.'}
        </p>
        <div className="admin-params-form-panel admin-params-form-panel-wide">
          {!currentSubdomainLocked && (
            <label>
              Subdomain slug {isSubdomainRequired ? '(required)' : '(optional)'}
              <div className="admin-params-subdomain-row">
                <input
                  type="text"
                  value={subdomainInput}
                  onChange={(e) => {
                    setSubdomainInput(e.target.value);
                    setSubdomainError('');
                  }}
                  placeholder={isSubdomainRequired ? 'your-brand' : 'optional'}
                  autoComplete="off"
                  spellCheck={false}
                  maxLength={40}
                />
                <span className="admin-params-subdomain-suffix">.dtameals.com</span>
              </div>
            </label>
          )}
          <p className="admin-params-muted">Subdomain slug: {normalizedSubdomain || '—'}</p>
          <p className="admin-params-muted">Dev preview: {normalizedSubdomain ? `${normalizedSubdomain}.lvh.me:3000` : '—'}</p>
          <p className="admin-params-muted">Production: {normalizedSubdomain ? `${normalizedSubdomain}.dtameals.com` : '—'}</p>
          {!currentSubdomainLocked && effectiveSubdomainError && (
            <p className="admin-params-error">{effectiveSubdomainError}</p>
          )}
          {currentSubdomainLocked && (
            <p className="admin-params-success">
              Subdomain locked on {subdomainInfo?.locked_at ? new Date(subdomainInfo.locked_at).toLocaleString() : 'setup'}.
            </p>
          )}
        </div>
      </section>

      <section className="admin-params-card">
        <h2 className="admin-params-section-title">Core Editable Parameters (v1)</h2>
        <p className="admin-params-muted">
          Start here: goal adjustments and macro defaults. Pick one meal plan type and one goal at a time to reduce clutter.
        </p>

        <div className="admin-params-form-grid">
          <div className="admin-params-form-panel">
            <h3>Goal Calorie Adjustments (%)</h3>
            <label>
              Lose weight %
              <input
                type="number"
                step="0.01"
                value={goalAdjustments.lose_weight_percent ?? ''}
                onChange={(e) => updateNumberField(['goal_calorie_adjustments', 'lose_weight_percent'], e.target.value)}
              />
            </label>
            <label>
              Maintain weight %
              <input
                type="number"
                step="0.01"
                value={goalAdjustments.maintain_weight_percent ?? ''}
                onChange={(e) => updateNumberField(['goal_calorie_adjustments', 'maintain_weight_percent'], e.target.value)}
              />
            </label>
            <label>
              Gain weight %
              <input
                type="number"
                step="0.01"
                value={goalAdjustments.gain_weight_percent ?? ''}
                onChange={(e) => updateNumberField(['goal_calorie_adjustments', 'gain_weight_percent'], e.target.value)}
              />
            </label>
          </div>
        </div>

        <div className="admin-params-form-panel admin-params-form-panel-wide">
          <h3>Macro Rules by Goal</h3>
          <div className="admin-params-editor-controls">
            <div className="admin-params-editor-group">
              <span className="admin-params-editor-label">Meal Plan Type</span>
              <div className="admin-params-tabs">
                {['standard', 'keto', 'carb_cycling'].map((key) => (
                  <button
                    key={`core-plan-${key}`}
                    type="button"
                    className={`admin-params-tab ${selectedCorePlanType === key ? 'is-active' : ''}`}
                    onClick={() => setSelectedCorePlanType(key)}
                  >
                    {key === 'carb_cycling' ? 'Carb Cycling' : key.charAt(0).toUpperCase() + key.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            <div className="admin-params-editor-group">
              <span className="admin-params-editor-label">Goal</span>
              <div className="admin-params-tabs">
                {['lose', 'maintain', 'gain'].map((key) => (
                  <button
                    key={`core-goal-${key}`}
                    type="button"
                    className={`admin-params-tab ${selectedCoreGoal === key ? 'is-active' : ''}`}
                    onClick={() => setSelectedCoreGoal(key)}
                  >
                    {key === 'lose' ? 'Lose Weight' : key === 'maintain' ? 'Maintain' : 'Gain Weight'}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="admin-params-rule-block">
            <div className="admin-params-rule-head">
              <strong>{corePlanLabel} - {coreGoalLabel}</strong>
              {selectedCorePlanType === 'standard' && (
                <span className={Math.abs(selectedStandardTotal - 100) < 0.11 ? 'sum-ok' : 'sum-warn'}>
                  carbs + fats = {selectedStandardTotal}
                </span>
              )}
              {selectedCorePlanType === 'keto' && (
                <span className={Math.abs(selectedKetoTotal - 100) < 0.11 ? 'sum-ok' : 'sum-warn'}>
                  carbs + fats = {selectedKetoTotal}
                </span>
              )}
              {selectedCorePlanType === 'carb_cycling' && (
                <>
                  <span className={Math.abs(selectedCarbLowTotal - 100) < 0.11 ? 'sum-ok' : 'sum-warn'}>
                    low day total = {selectedCarbLowTotal}
                  </span>
                  <span className={Math.abs(selectedCarbHighTotal - 100) < 0.11 ? 'sum-ok' : 'sum-warn'}>
                    high day total = {selectedCarbHighTotal}
                  </span>
                </>
              )}
            </div>

            {selectedCorePlanType !== 'carb_cycling' && (
              <div className="admin-params-rule-grid">
                <label>
                  Protein g/lb
                  <input
                    type="number"
                    step="0.01"
                    value={(selectedCorePlanType === 'standard' ? selectedStandardRule : selectedKetoRule).protein_factor_value ?? ''}
                    onChange={(e) => updateNumberField(['meal_plans', selectedCorePlanType, 'macro_rules_by_goal', selectedCoreGoal, 'protein_factor_value'], e.target.value)}
                  />
                </label>
                <label>
                  Carb %
                  <input
                    type="number"
                    step="0.01"
                    value={(selectedCorePlanType === 'standard' ? selectedStandardRule : selectedKetoRule).carb_percent ?? ''}
                    onChange={(e) => updateLockedPercentPair({
                      carbPath: ['meal_plans', selectedCorePlanType, 'macro_rules_by_goal', selectedCoreGoal, 'carb_percent'],
                      fatPath: ['meal_plans', selectedCorePlanType, 'macro_rules_by_goal', selectedCoreGoal, 'fat_percent'],
                      changedKey: 'carb',
                      rawValue: e.target.value,
                    })}
                  />
                </label>
                <label>
                  Fat %
                  <input
                    type="number"
                    step="0.01"
                    value={(selectedCorePlanType === 'standard' ? selectedStandardRule : selectedKetoRule).fat_percent ?? ''}
                    onChange={(e) => updateLockedPercentPair({
                      carbPath: ['meal_plans', selectedCorePlanType, 'macro_rules_by_goal', selectedCoreGoal, 'carb_percent'],
                      fatPath: ['meal_plans', selectedCorePlanType, 'macro_rules_by_goal', selectedCoreGoal, 'fat_percent'],
                      changedKey: 'fat',
                      rawValue: e.target.value,
                    })}
                  />
                </label>
              </div>
            )}

            {selectedCorePlanType === 'carb_cycling' && (
              <div className="admin-params-rule-grid">
                <label>
                  Protein g/lb
                  <input
                    type="number"
                    step="0.01"
                    value={selectedCarbCyclingRule.protein_factor_value ?? ''}
                    onChange={(e) => updateNumberField(['meal_plans', 'carb_cycling', 'macro_rules_by_goal', selectedCoreGoal, 'protein_factor_value'], e.target.value)}
                  />
                </label>
                <label>
                  Low Day Carb %
                  <input
                    type="number"
                    step="0.01"
                    value={selectedCarbCyclingLow.carb_percent ?? ''}
                    onChange={(e) => updateLockedPercentPair({
                      carbPath: ['meal_plans', 'carb_cycling', 'macro_rules_by_goal', selectedCoreGoal, 'low_day', 'carb_percent'],
                      fatPath: ['meal_plans', 'carb_cycling', 'macro_rules_by_goal', selectedCoreGoal, 'low_day', 'fat_percent'],
                      changedKey: 'carb',
                      rawValue: e.target.value,
                    })}
                  />
                </label>
                <label>
                  Low Day Fat %
                  <input
                    type="number"
                    step="0.01"
                    value={selectedCarbCyclingLow.fat_percent ?? ''}
                    onChange={(e) => updateLockedPercentPair({
                      carbPath: ['meal_plans', 'carb_cycling', 'macro_rules_by_goal', selectedCoreGoal, 'low_day', 'carb_percent'],
                      fatPath: ['meal_plans', 'carb_cycling', 'macro_rules_by_goal', selectedCoreGoal, 'low_day', 'fat_percent'],
                      changedKey: 'fat',
                      rawValue: e.target.value,
                    })}
                  />
                </label>
                <label>
                  High Day Carb %
                  <input
                    type="number"
                    step="0.01"
                    value={selectedCarbCyclingHigh.carb_percent ?? ''}
                    onChange={(e) => updateLockedPercentPair({
                      carbPath: ['meal_plans', 'carb_cycling', 'macro_rules_by_goal', selectedCoreGoal, 'high_day', 'carb_percent'],
                      fatPath: ['meal_plans', 'carb_cycling', 'macro_rules_by_goal', selectedCoreGoal, 'high_day', 'fat_percent'],
                      changedKey: 'carb',
                      rawValue: e.target.value,
                    })}
                  />
                </label>
                <label>
                  High Day Fat %
                  <input
                    type="number"
                    step="0.01"
                    value={selectedCarbCyclingHigh.fat_percent ?? ''}
                    onChange={(e) => updateLockedPercentPair({
                      carbPath: ['meal_plans', 'carb_cycling', 'macro_rules_by_goal', selectedCoreGoal, 'high_day', 'carb_percent'],
                      fatPath: ['meal_plans', 'carb_cycling', 'macro_rules_by_goal', selectedCoreGoal, 'high_day', 'fat_percent'],
                      changedKey: 'fat',
                      rawValue: e.target.value,
                    })}
                  />
                </label>
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="admin-params-card">
        <h2 className="admin-params-section-title">Meal Breakdown Editor (v1)</h2>
        <p className="admin-params-muted">
          Edit meal split percentages by meal count, plan type, and training timing scenario.
        </p>

        <div className="admin-params-editor-controls">
          <div className="admin-params-editor-group">
            <span className="admin-params-editor-label">Meal Count</span>
            <div className="admin-params-tabs">
              {['meals_3', 'meals_4', 'meals_5', 'meals_6'].map((key) => (
                <button
                  key={`editor-${key}`}
                  type="button"
                  className={`admin-params-tab ${selectedMealCount === key ? 'is-active' : ''}`}
                  onClick={() => setSelectedMealCount(key)}
                >
                  {key.replace('meals_', '')} Meals
                </button>
              ))}
            </div>
          </div>

          <div className="admin-params-editor-group">
            <span className="admin-params-editor-label">Plan Type</span>
            <div className="admin-params-tabs">
              {['standard', 'keto', 'carb_cycling'].map((key) => (
                <button
                  key={`plan-${key}`}
                  type="button"
                  className={`admin-params-tab ${mealEditorPlanType === key ? 'is-active' : ''}`}
                  onClick={() => setMealEditorPlanType(key)}
                >
                  {key === 'carb_cycling' ? 'Carb Cycling' : key.charAt(0).toUpperCase() + key.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {mealEditorPlanType === 'carb_cycling' && (
            <div className="admin-params-editor-group">
              <span className="admin-params-editor-label">Carb Cycling Day Type</span>
              <div className="admin-params-tabs">
                {['low_carbs', 'high_carbs'].map((key) => (
                  <button
                    key={`variant-${key}`}
                    type="button"
                    className={`admin-params-tab ${carbCyclingVariant === key ? 'is-active' : ''}`}
                    onClick={() => setCarbCyclingVariant(key)}
                  >
                    {key === 'low_carbs' ? 'Low Carbs' : 'High Carbs'}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="admin-params-editor-group">
            <label className="admin-params-editor-select-wrap">
              <span className="admin-params-editor-label">Training Scenario</span>
              <select
                className="admin-params-editor-select"
                value={selectedScenario}
                onChange={(e) => setSelectedScenario(e.target.value)}
              >
                {mealEditorScenarioKeys.map((key) => (
                  <option key={key} value={key}>
                    {key.replaceAll('_', ' ')}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        <div className="admin-params-meal-table-wrap">
          <table className="admin-params-meal-table">
            <thead>
              <tr>
                <th>Meal</th>
                <th>Protein %</th>
                <th>Carbs %</th>
                <th>Fats %</th>
              </tr>
            </thead>
            <tbody>
              {mealEditorMealKeys.map((mealKey) => {
                const row = mealEditorCurrentScenario?.[mealKey] || {};
                return (
                  <tr key={`${selectedMealCount}-${mealEditorPlanType}-${carbCyclingVariant}-${selectedScenario}-${mealKey}`}>
                    <td className="meal-key-cell">{mealKey.replace('_', ' ')}</td>
                    {['protein', 'carbs', 'fats'].map((macroKey) => (
                      <td key={`${mealKey}-${macroKey}`}>
                        <input
                          type="number"
                          step="0.001"
                          value={row[macroKey] ?? ''}
                          onChange={(e) => handleMealBreakdownCellChange(mealKey, macroKey, e.target.value)}
                        />
                      </td>
                    ))}
                  </tr>
                );
              })}
              {!mealEditorMealKeys.length && (
                <tr>
                  <td colSpan="4" className="meal-empty-cell">
                    No meal breakdown data found for this selection.
                  </td>
                </tr>
              )}
            </tbody>
            <tfoot>
              <tr>
                <th>Column Totals</th>
                <th>
                  <span className={Math.abs(mealColumnTotals.protein - 100) < 0.11 ? 'sum-ok' : 'sum-warn'}>
                    {mealColumnTotals.protein.toFixed(3)}
                  </span>
                </th>
                <th>
                  <span className={Math.abs(mealColumnTotals.carbs - 100) < 0.11 ? 'sum-ok' : 'sum-warn'}>
                    {mealColumnTotals.carbs.toFixed(3)}
                  </span>
                </th>
                <th>
                  <span className={Math.abs(mealColumnTotals.fats - 100) < 0.11 ? 'sum-ok' : 'sum-warn'}>
                    {mealColumnTotals.fats.toFixed(3)}
                  </span>
                </th>
              </tr>
            </tfoot>
          </table>
        </div>
      </section>

      <section className="admin-params-card">
        <h2 className="admin-params-section-title">TDEE Editor (v1)</h2>
        <p className="admin-params-muted">
          Edit category multipliers, lifestyle/training-day category mapping, and weekly day multiplier split tables. These are admin TDEE multipliers (BMR calculation remains standard and is not edited here).
        </p>

        <div className="admin-params-form-panel admin-params-form-panel-wide">
          <h3>Category Multipliers (1-7)</h3>
          <div className="admin-params-category-grid">
            {trainingDayOptions.map((categoryKey) => (
              <label key={`category-multiplier-${categoryKey}`}>
                Category {categoryKey}
                <input
                  type="number"
                  step="0.000001"
                  value={categoryMultipliers[categoryKey] ?? ''}
                  onChange={(e) => handleCategoryMultiplierChange(categoryKey, e.target.value)}
                />
              </label>
            ))}
          </div>
        </div>

        <div className="admin-params-form-panel admin-params-form-panel-wide">
          <h3>Category Mapping by Lifestyle + Training Days</h3>
          <p className="admin-params-muted">Each cell maps to a category (1-7).</p>
          <div className="admin-params-tdee-table-wrap">
            <table className="admin-params-tdee-table">
              <thead>
                <tr>
                  <th>Lifestyle</th>
                  {trainingDayOptions.map((dayKey) => (
                    <th key={`mapping-head-${dayKey}`}>{dayKey} day{dayKey === '1' ? '' : 's'}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {tdeeLifestyleOptions.map((lifestyleKey) => (
                  <tr key={`mapping-row-${lifestyleKey}`}>
                    <td className="tdee-row-label">{lifestyleKey.replace('_', ' ')}</td>
                    {trainingDayOptions.map((dayKey) => (
                      <td key={`mapping-cell-${lifestyleKey}-${dayKey}`}>
                        <input
                          type="number"
                          step="1"
                          min="1"
                          max="7"
                          value={categoryMapping?.[lifestyleKey]?.[dayKey] ?? ''}
                          onChange={(e) => handleCategoryMappingChange(lifestyleKey, dayKey, e.target.value)}
                        />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="admin-params-form-panel admin-params-form-panel-wide">
          <h3>Weekly Day Multiplier Splits</h3>
          <div className="admin-params-editor-controls">
            <div className="admin-params-editor-group">
              <span className="admin-params-editor-label">Lifestyle</span>
              <div className="admin-params-tabs">
                {tdeeLifestyleOptions.map((key) => (
                  <button
                    key={`tdee-life-${key}`}
                    type="button"
                    className={`admin-params-tab ${selectedTdeeLifestyle === key ? 'is-active' : ''}`}
                    onClick={() => setSelectedTdeeLifestyle(key)}
                  >
                    {key.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>

            <div className="admin-params-editor-group">
              <span className="admin-params-editor-label">Training Days / Week</span>
              <div className="admin-params-tabs">
                {trainingDayOptions.map((key) => (
                  <button
                    key={`tdee-days-${key}`}
                    type="button"
                    className={`admin-params-tab ${selectedTdeeTrainingDays === key ? 'is-active' : ''}`}
                    onClick={() => setSelectedTdeeTrainingDays(key)}
                  >
                    {key}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="admin-params-tdee-summary">
            <label>
              Category
              <input
                type="number"
                min="1"
                max="7"
                step="1"
                value={selectedWeeklyTable.category ?? ''}
                onChange={(e) => handleWeeklyTableCategoryChange(e.target.value)}
              />
            </label>
            <div className="admin-params-tdee-metrics">
              <span className="tdee-role-chip">
                Workout days: {selectedTrainingDayCount} / Off days: {Math.max(0, 7 - selectedTrainingDayCount)}
              </span>
              <span className={Math.abs(selectedWeeklyAverage - selectedWeeklyTargetMultiplier) < 0.011 ? 'sum-ok' : 'sum-warn'}>
                Avg = {selectedWeeklyAverage.toFixed(6)}
              </span>
              <span className="tdee-target-chip">
                Category {selectedWeeklyCategoryKey || '—'} target = {selectedWeeklyTargetMultiplier ? selectedWeeklyTargetMultiplier.toFixed(6) : '—'}
              </span>
            </div>
          </div>

          <div className="admin-params-tdee-table-wrap">
            <table className="admin-params-tdee-table">
              <thead>
                <tr>
                  {['Day1', 'Day2', 'Day3', 'Day4', 'Day5', 'Day6', 'Day7'].map((dayLabel) => (
                    <th key={`weekly-day-head-${dayLabel}`}>{dayLabel}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  {Array.from({ length: 7 }).map((_, dayIndex) => (
                    <td
                      key={`weekly-day-cell-${dayIndex}`}
                      className={
                        weeklyDayRoleLabels?.[dayIndex] === 'workout'
                          ? 'tdee-day-cell tdee-day-cell-workout'
                          : 'tdee-day-cell tdee-day-cell-off'
                      }
                    >
                      <input
                        type="number"
                        step="0.000001"
                        className={
                          weeklyDayRoleLabels?.[dayIndex] === 'workout'
                            ? 'tdee-day-input tdee-day-input-workout'
                            : 'tdee-day-input tdee-day-input-off'
                        }
                        value={selectedWeeklyDayMultipliers?.[dayIndex] ?? ''}
                        onChange={(e) => handleWeeklyDayMultiplierChange(dayIndex, e.target.value)}
                      />
                    </td>
                  ))}
                </tr>
                <tr>
                  {Array.from({ length: 7 }).map((_, dayIndex) => {
                    const role = weeklyDayRoleLabels?.[dayIndex] || 'off';
                    return (
                      <td key={`weekly-day-role-${dayIndex}`}>
                        <span className={role === 'workout' ? 'tdee-day-role role-workout' : 'tdee-day-role role-off'}>
                          {role === 'workout' ? 'Workout Day' : 'Off Day'}
                        </span>
                      </td>
                    );
                  })}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

    </div>
  );
}

export default AdminParameterSettingsPage;
