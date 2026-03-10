import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import { apiRequest } from '../../../api/client';
import { openPrintPdfWindow, renderPrintTable, escapeHtml } from '../../../utils/printPdf';
import '../../../styles/shared/client-app-shell.css';
import './css.css';

const WEEK_DAYS = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];

function prettyDay(day) {
  return day ? day.charAt(0).toUpperCase() + day.slice(1) : 'Day';
}

function formatTrainingLabel(value) {
  if (!value) return 'No training';
  return String(value).replace('before_meal_', 'Before Meal ');
}

function getTodayWeekdayKey() {
  return WEEK_DAYS[new Date().getDay()] || 'sunday';
}

function renderPrintSection(title, innerHtml) {
  return `<section class="section"><h2>${escapeHtml(title)}</h2>${innerHtml}</section>`;
}

function renderChipList(items = []) {
  const list = items.filter(Boolean);
  if (!list.length) return '';
  return `<div class="chips">${list.map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join('')}</div>`;
}

function ClientExportsPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dashboard, setDashboard] = useState(null);
  const [selectedMacroDay, setSelectedMacroDay] = useState(getTodayWeekdayKey());

  useEffect(() => {
    let ignore = false;
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const res = await apiRequest('/api/v1/users/client/app/dashboard/', { auth: true });
        if (ignore) return;
        if (res.status === 401) {
          navigate('/client_login', { replace: true });
          return;
        }
        if (!res.ok) {
          setError(res.data?.error?.message || 'Unable to load export data.');
          return;
        }
        setDashboard(res.data || null);
      } catch (err) {
        console.error(err);
        if (!ignore) setError('Network error while loading export data.');
      } finally {
        if (!ignore) setLoading(false);
      }
    };
    load();
    return () => { ignore = true; };
  }, [navigate]);

  const resultDays = useMemo(() => (Array.isArray(dashboard?.results?.weekly_days) ? dashboard.results.weekly_days : []), [dashboard?.results?.weekly_days]);
  const resultDayMap = useMemo(() => Object.fromEntries(resultDays.map((d) => [d.day, d])), [resultDays]);
  const todayKey = getTodayWeekdayKey();
  const selectedDay = resultDayMap[selectedMacroDay] || resultDayMap[todayKey] || resultDays[0] || null;
  const isQuestionnaireComplete = dashboard?.questionnaire?.status === 'completed';
  const hasPaidExportAccess = Boolean(dashboard?.client?.includes_food_plan);

  useEffect(() => {
    if (!resultDays.length) return;
    if (!resultDayMap[selectedMacroDay]) {
      setSelectedMacroDay(resultDayMap[todayKey] ? todayKey : resultDays[0].day);
    }
  }, [resultDays, resultDayMap, selectedMacroDay, todayKey]);

  const handleExportMacrosPdf = () => {
    if (!selectedDay) {
      setError('No macro results available yet. Complete your questionnaire first.');
      return;
    }
    if (!hasPaidExportAccess) {
      setError('PDF exports are available only for paid monthly plans.');
      return;
    }
    const opened = openPrintPdfWindow({
      title: `${prettyDay(selectedDay.day)} Daily Macros`,
      subtitle: 'Exported from Export Center. Use your browser print dialog and choose "Save as PDF".',
      sections: [
        renderPrintSection(
          'Daily Macro Results',
          [
            renderChipList([
              selectedDay.is_workout_day ? 'Workout Day' : 'Off Day',
              `Meals: ${selectedDay.meals_per_day ?? '-'}`,
              `Training: ${formatTrainingLabel(selectedDay.training_before_meal)}`,
              `TDEE: ${selectedDay.tdee_calories ?? '-'} kcal`,
              `Target: ${selectedDay.calories_target ?? '-'} kcal`,
              `Protein: ${selectedDay.daily_macros?.protein_g ?? '-'} g`,
              `Carbs: ${selectedDay.daily_macros?.carbs_g ?? '-'} g`,
              `Fats: ${selectedDay.daily_macros?.fats_g ?? '-'} g`,
            ]),
            renderPrintTable(
              ['Meal', 'Protein', 'Carbs', 'Fats'],
              (selectedDay.meal_macro_splits || []).map((meal) => ([
                `Meal ${meal.meal_number ?? '-'}`,
                `${meal.grams?.protein_g ?? '-'} g (${meal.percentages?.protein ?? '-'}%)`,
                `${meal.grams?.carbs_g ?? '-'} g (${meal.percentages?.carbs ?? '-'}%)`,
                `${meal.grams?.fats_g ?? '-'} g (${meal.percentages?.fats ?? '-'}%)`,
              ]))
            ),
          ].join('')
        ),
      ],
    });
    if (!opened) {
      setError('Unable to open PDF print window. Allow pop-ups and try again.');
    }
  };

  return (
    <div className="client-dashboard-page">
      <header className="client-dashboard-header">
        <div>
          <h1>Export Center</h1>
          <p className="client-dash-muted">Save your macros, food plan, and recipe PDFs from one place.</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <Link className="client-q-btn secondary" to="/client_dashboard">Back to Dashboard</Link>
          <button type="button" className="client-q-btn danger" onClick={() => logout('/client_login')}>
            Log Out
          </button>
        </div>
      </header>

      <section className="client-dashboard-card" style={{ border: '2px solid rgba(20,40,74,0.12)', background: 'linear-gradient(180deg, #ffffff 0%, #f7fbff 100%)' }}>
        <h2>Macros PDF</h2>
        <p className="client-dash-muted">
          Export directly from here, or open the dashboard/macros page if you want to review the numbers first.
        </p>
        {loading ? <p className="client-dash-muted">Loading macro export data…</p> : null}
        {!loading && !hasPaidExportAccess ? (
          <p className="client-dash-muted">
            Exports are locked on the free macro plan. Upgrade to a paid monthly plan to export PDFs.
          </p>
        ) : null}
        {!loading && !isQuestionnaireComplete ? (
          <p className="client-dash-muted">Complete the questionnaire first so daily macro results are available.</p>
        ) : null}
        {!loading && hasPaidExportAccess && isQuestionnaireComplete && resultDays.length > 0 ? (
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'end', marginBottom: '0.6rem' }}>
            <label>
              Day
              <select value={selectedDay?.day || selectedMacroDay} onChange={(e) => setSelectedMacroDay(e.target.value)}>
                {resultDays.map((day) => (
                  <option key={`exports-macro-${day.day}`} value={day.day}>{prettyDay(day.day)}</option>
                ))}
              </select>
            </label>
            <button type="button" className="client-q-btn secondary" onClick={() => setSelectedMacroDay(todayKey)}>
              Today
            </button>
            <button type="button" className="client-q-btn" onClick={handleExportMacrosPdf} disabled={!selectedDay}>
              Save Macros PDF
            </button>
          </div>
        ) : null}
        {hasPaidExportAccess && selectedDay ? (
          <div className="client-dash-chips" style={{ marginBottom: '0.6rem' }}>
            <span>{prettyDay(selectedDay.day)}</span>
            <span>{selectedDay.is_workout_day ? 'Workout Day' : 'Off Day'}</span>
            <span>Target: {selectedDay.calories_target ?? '-'} kcal</span>
            <span>Protein: {selectedDay.daily_macros?.protein_g ?? '-'} g</span>
            <span>Carbs: {selectedDay.daily_macros?.carbs_g ?? '-'} g</span>
            <span>Fats: {selectedDay.daily_macros?.fats_g ?? '-'} g</span>
          </div>
        ) : null}
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button type="button" className="client-q-btn" onClick={() => navigate('/client_dashboard')}>
            Go to Dashboard Macros Export
          </button>
          <button type="button" className="client-q-btn secondary" onClick={() => navigate('/macro_calculator')}>
            Open Macro Calculator Page
          </button>
        </div>
      </section>

      <section className="client-dashboard-card" style={{ border: '2px solid rgba(20,40,74,0.12)', background: 'linear-gradient(180deg, #ffffff 0%, #f7fbff 100%)' }}>
        <h2>Meal Plan Export Actions</h2>
        <p className="client-dash-muted">
          Use the Meal Generation page for the paid feature exports. Load a generated day first. Recipes and Combined require recipe ideas to be generated.
        </p>
        <div style={{ display: 'grid', gap: '0.6rem' }}>
          <button type="button" className="client-q-btn" onClick={() => navigate('/client_meal_generation')} disabled={!hasPaidExportAccess}>
            Open Food Plan PDF Export (Meal Generation)
          </button>
          <button type="button" className="client-q-btn secondary" onClick={() => navigate('/client_meal_generation')} disabled={!hasPaidExportAccess}>
            Open Recipes PDF Export (Meal Generation)
          </button>
          <button type="button" className="client-q-btn secondary" onClick={() => navigate('/client_meal_generation')} disabled={!hasPaidExportAccess}>
            Open Combined PDF Export (Meal Generation)
          </button>
        </div>
      </section>

      <section className="client-dashboard-card">
        <h2>Troubleshooting</h2>
        {error ? <p className="client-q-error">{error}</p> : null}
        <ul>
          <li>Allow pop-ups for your local domain if the PDF print window is blocked.</li>
          <li>If the print window opens blank, refresh the page and retry after loading the data section again.</li>
          <li>For meal exports, generate or load the day first before using the PDF buttons.</li>
        </ul>
      </section>
    </div>
  );
}

export default ClientExportsPage;
