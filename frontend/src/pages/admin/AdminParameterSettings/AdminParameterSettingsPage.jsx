import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../../../api/client';
import './AdminParameterSettingsPage.css';

function prettyJson(value) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return '';
  }
}

function AdminParameterSettingsPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState('loading');
  const [saveStatus, setSaveStatus] = useState('idle');
  const [message, setMessage] = useState('');
  const [selectedMealCount, setSelectedMealCount] = useState('meals_3');
  const [rawText, setRawText] = useState('');
  const [metadata, setMetadata] = useState(null);
  const [parsedSettings, setParsedSettings] = useState(null);

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
          defaultsVersionApplied: payload.defaults_version_applied || 'v1',
          updatedAt: payload.updated_at || null,
        });
        setParsedSettings(payload.parameters_json || {});
        setRawText(prettyJson(payload.parameters_json || {}));
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

  const mealViews = useMemo(() => {
    if (!parsedSettings) return null;
    const mealPlans = parsedSettings.meal_plans || {};
    return {
      standard: mealPlans.standard?.meal_macro_distribution?.[selectedMealCount] || null,
      keto: mealPlans.keto?.meal_macro_distribution?.[selectedMealCount] || null,
      carbCycling: mealPlans.carb_cycling?.meal_macro_distribution?.[selectedMealCount] || null,
    };
  }, [parsedSettings, selectedMealCount]);

  const handleUseDefaults = async () => {
    try {
      setSaveStatus('saving');
      setMessage('');
      const res = await apiRequest('/api/v1/users/admin/parameter_settings/use_defaults/', {
        method: 'POST',
        auth: true,
      });
      if (res.status === 401) {
        navigate('/admin_login');
        return;
      }
      if (!res.ok) {
        setSaveStatus('error');
        setMessage(res.data?.error?.message || 'Unable to apply DTA defaults.');
        return;
      }

      const reload = await apiRequest('/api/v1/users/admin/parameter_settings/', { auth: true });
      if (reload.ok) {
        const payload = reload.data?.parameter_settings || {};
        setMetadata({
          initialized: Boolean(payload.initialized),
          defaultsVersionApplied: payload.defaults_version_applied || 'v1',
          updatedAt: payload.updated_at || null,
        });
        setParsedSettings(payload.parameters_json || {});
        setRawText(prettyJson(payload.parameters_json || {}));
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
    let parsed;
    try {
      parsed = JSON.parse(rawText);
    } catch (err) {
      setSaveStatus('error');
      setMessage(`JSON error: ${err.message}`);
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
        },
      });
      if (res.status === 401) {
        navigate('/admin_login');
        return;
      }
      if (!res.ok) {
        setSaveStatus('error');
        setMessage(res.data?.error?.message || 'Unable to save admin parameter settings.');
        return;
      }

      const payload = res.data?.parameter_settings || {};
      setParsedSettings(payload.parameters_json || parsed);
      setRawText(prettyJson(payload.parameters_json || parsed));
      setMetadata((prev) => ({
        initialized: Boolean(payload.initialized ?? prev?.initialized),
        defaultsVersionApplied: payload.defaults_version_applied || prev?.defaultsVersionApplied || 'v1',
        updatedAt: payload.updated_at || prev?.updatedAt || null,
      }));
      setSaveStatus('success');
      setMessage('Admin parameter settings saved.');
    } catch (err) {
      console.error('save parameter settings error', err);
      setSaveStatus('error');
      setMessage('Network error while saving admin parameter settings.');
    }
  };

  if (status === 'loading') {
    return <div className="admin-params-page"><p className="admin-params-muted">Loading admin parameter settings…</p></div>;
  }

  if (status === 'error') {
    return (
      <div className="admin-params-page">
        <p className="admin-params-error">{message || 'Unable to load admin parameter settings.'}</p>
        <button className="admin-params-btn" onClick={() => navigate('/admin_dashboard')}>Back to Dashboard</button>
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
          <span>Defaults: {metadata?.defaultsVersionApplied || 'v1'}</span>
          <span>Updated: {metadata?.updatedAt ? new Date(metadata.updatedAt).toLocaleString() : '—'}</span>
        </div>
      </header>

      <section className="admin-params-card">
        <div className="admin-params-actions">
          <button className="admin-params-btn" onClick={handleUseDefaults} disabled={saveStatus === 'saving'}>
            Use DTA Defaults
          </button>
          <button className="admin-params-btn admin-params-btn-primary" onClick={handleSave} disabled={saveStatus === 'saving'}>
            {saveStatus === 'saving' ? 'Saving…' : 'Save Changes'}
          </button>
          <button className="admin-params-btn" onClick={() => navigate('/admin_dashboard')}>
            Back to Dashboard
          </button>
        </div>
        {message && (
          <p className={saveStatus === 'error' ? 'admin-params-error' : 'admin-params-success'}>
            {message}
          </p>
        )}
      </section>

      <section className="admin-params-card">
        <h2 className="admin-params-section-title">Meal Split Quick View</h2>
        <p className="admin-params-muted">
          Compare Standard, Keto, and Carb Cycling distributions for one meal count at a time.
        </p>
        <div className="admin-params-tabs">
          {['meals_3', 'meals_4', 'meals_5', 'meals_6'].map((key) => (
            <button
              key={key}
              className={`admin-params-tab ${selectedMealCount === key ? 'is-active' : ''}`}
              onClick={() => setSelectedMealCount(key)}
              type="button"
            >
              {key.replace('meals_', '')} Meals
            </button>
          ))}
        </div>

        <div className="admin-params-grid">
          <div className="admin-params-panel">
            <h3>Standard</h3>
            <pre>{prettyJson(mealViews?.standard || {})}</pre>
          </div>
          <div className="admin-params-panel">
            <h3>Keto</h3>
            <pre>{prettyJson(mealViews?.keto || {})}</pre>
          </div>
          <div className="admin-params-panel">
            <h3>Carb Cycling ({selectedMealCount})</h3>
            <pre>{prettyJson(mealViews?.carbCycling || {})}</pre>
          </div>
        </div>
      </section>

      <section className="admin-params-card">
        <h2 className="admin-params-section-title">Global (Goal + TDEE) Quick View</h2>
        <pre className="admin-params-inline-pre">
          {prettyJson({
            version: parsedSettings?.version,
            goal_calorie_adjustments: parsedSettings?.goal_calorie_adjustments,
            tdee: parsedSettings?.tdee,
          })}
        </pre>
      </section>

      <section className="admin-params-card">
        <h2 className="admin-params-section-title">Full JSON Editor (v1)</h2>
        <p className="admin-params-muted">
          First implementation: raw JSON editing with quick viewers above. We can replace this with a table editor next.
        </p>
        <textarea
          className="admin-params-textarea"
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          spellCheck={false}
        />
      </section>
    </div>
  );
}

export default AdminParameterSettingsPage;

