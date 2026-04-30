import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { apiRequest } from '../../../api/client';
import MealComboBuilderStep from '../../../components/MealComboBuilderStep';
import { useAuth } from '../../../context/AuthContext';
import '../../../styles/shared/client-app-shell.css';
import './css.css';

function normalizeSubdomainLabel(slug) {
  return slug ? `${slug}.dtameals.com` : 'DTA Direct';
}

function portalLabel(settings) {
  if (!settings) return 'Client Portal';
  return settings.sale_channel === 'admin_white_label' ? 'Coach Portal' : 'DTA Direct Portal';
}

const WEEK_DAYS = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];

function normalizeDay(value) {
  const day = String(value || '').trim().toLowerCase();
  return WEEK_DAYS.includes(day) ? day : null;
}

function ClientFoodPreferencesPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { logout } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  const [builderValue, setBuilderValue] = useState({});
  const [mealScheduleDays, setMealScheduleDays] = useState({});
  const [proteinShake, setProteinShake] = useState({ enabled: false, counts_as_meal: true });
  const [weeklyResults, setWeeklyResults] = useState([]);
  const [settingsMeta, setSettingsMeta] = useState(null);
  const requestedDay = normalizeDay(searchParams.get('day'));
  const returnTo = searchParams.get('return') || '';
  const safeReturnTo = returnTo.startsWith('/client_') ? returnTo : '';

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    const res = await apiRequest('/api/v1/users/client/app/food-preferences/', { auth: true });
    if (!res.ok) {
      setError(res.data?.error?.message || 'Unable to load food preferences form.');
      setLoading(false);
      return;
    }
    const payload = res.data?.food_preferences || {};
    setBuilderValue({
      ...(payload.builder_value || {}),
      ...(requestedDay ? { active_day: requestedDay } : {}),
    });
    setMealScheduleDays(payload.meal_schedule_days || {});
    setProteinShake(payload.protein_shake || { enabled: false, counts_as_meal: true });
    setWeeklyResults(payload.results?.weekly_days || []);
    const settingsRes = await apiRequest('/api/v1/users/client/app/settings/', { auth: true });
    if (settingsRes.ok) {
      setSettingsMeta(settingsRes.data?.settings || null);
    }
    setLoading(false);
  }, [requestedDay]);

  useEffect(() => {
    load().catch((err) => {
      console.error(err);
      setError('Unable to load food preferences form.');
      setLoading(false);
    });
  }, [load]);

  const handleSave = async () => {
    setSaving(true);
    setError('');
    setMessage('');
    try {
      const res = await apiRequest('/api/v1/users/client/app/food-preferences/', {
        method: 'PUT',
        auth: true,
        body: { builder_value: builderValue },
      });
      if (!res.ok) {
        setError(res.data?.error?.message || 'Unable to save food preferences.');
        return;
      }
      setMessage(`${res.data?.message || 'Food preferences saved.'} ${res.data?.saved_meal_combo_selections ? `(${res.data.saved_meal_combo_selections} meals)` : ''}`);
      navigate(safeReturnTo || '/client_dashboard', { replace: true });
    } catch (err) {
      console.error(err);
      setError('Network error while saving food preferences.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="client-dashboard-page"><p>Loading food preferences…</p></div>;

  return (
    <div className="client-dashboard-page">
      <header className="client-dashboard-header">
        <div>
          <h1>Choose your meal preferences</h1>
          <div className="client-dash-chips" style={{ marginTop: '0.35rem' }}>
            <span>{portalLabel(settingsMeta)}</span>
            <span>Source: {normalizeSubdomainLabel(settingsMeta?.associated_admin_slug)}</span>
          </div>
          <p className="client-dash-muted">
            Pick visual meal templates for each day, then customize foods only when needed.
            {requestedDay ? ` Editing ${requestedDay.charAt(0).toUpperCase() + requestedDay.slice(1)}.` : ''}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <Link className="client-q-btn secondary" to="/client_dashboard">Back to Dashboard</Link>
          <Link className="client-q-btn secondary" to="/client_settings">Settings</Link>
          <Link className="client-q-btn secondary" to={requestedDay ? `/client_meal_generation?day=${requestedDay}` : '/client_meal_generation'}>Run Meal Generation</Link>
          <button type="button" className="client-q-btn" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : safeReturnTo ? 'Save And Return' : 'Save Food Preferences'}
          </button>
          <button type="button" className="client-q-btn danger" onClick={() => logout('/client_login')} disabled={saving}>
            Log Out
          </button>
        </div>
      </header>

      {error ? (
        <section className="client-dashboard-card">
          <p className="client-q-error">{error}</p>
          <p className="client-dash-muted">
            If you are on the free macro plan, upgrade first in <Link to="/client_settings">Client Settings</Link>.
          </p>
        </section>
      ) : (
        <>
          {message ? <p className="client-q-message">{message}</p> : null}
          <section className="client-dashboard-card">
            <MealComboBuilderStep
              value={builderValue}
              onChange={setBuilderValue}
              mealScheduleDays={mealScheduleDays}
              weeklyMacroResults={weeklyResults}
              proteinShake={proteinShake}
            />
          </section>
        </>
      )}
    </div>
  );
}

export default ClientFoodPreferencesPage;
