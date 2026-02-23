import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiRequest } from '../../api/client';
import MealComboBuilderStep from '../../components/MealComboBuilderStep';
import { useAuth } from '../../context/AuthContext';
import './ClientDashboardPage.css';

function ClientFoodPreferencesPage() {
  const { logout } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  const [builderValue, setBuilderValue] = useState({});
  const [mealScheduleDays, setMealScheduleDays] = useState({});
  const [weeklyResults, setWeeklyResults] = useState([]);

  const load = async () => {
    setLoading(true);
    setError('');
    const res = await apiRequest('/api/v1/users/client/app/food-preferences/', { auth: true });
    if (!res.ok) {
      setError(res.data?.error?.message || 'Unable to load food preferences form.');
      setLoading(false);
      return;
    }
    const payload = res.data?.food_preferences || {};
    setBuilderValue(payload.builder_value || {});
    setMealScheduleDays(payload.meal_schedule_days || {});
    setWeeklyResults(payload.results?.weekly_days || []);
    setLoading(false);
  };

  useEffect(() => {
    load().catch((err) => {
      console.error(err);
      setError('Unable to load food preferences form.');
      setLoading(false);
    });
  }, []);

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
          <h1>Food Preferences & Meal Combos</h1>
          <p className="client-dash-muted">
            Choose your meal combos for the week using templates or custom combinations. We save combo IDs for your Sunday-Saturday plan.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <Link className="client-q-btn secondary" to="/client_dashboard">Back to Dashboard</Link>
          <Link className="client-q-btn secondary" to="/client_settings">Settings</Link>
          <button type="button" className="client-q-btn" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save Food Preferences'}
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
            />
          </section>
        </>
      )}
    </div>
  );
}

export default ClientFoodPreferencesPage;
