import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiRequest } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { getFoodImageUrl } from '../../utils/foodImageLookup';
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

function amountLabel(slot, unitMode) {
  if (!slot) return '-';
  if (unitMode === 'g') return `${Number(slot.amount_g || 0).toFixed(2)} g`;
  return `${Number(slot.amount_oz || 0).toFixed(2)} oz`;
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
  const weekPollTimeoutRef = useRef(null);

  const loadLatestDetail = async (day, jobId = null) => {
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
      return payload;
    } catch (err) {
      console.error(err);
      setDetail(null);
      setError('Network error while loading detailed meal plan.');
      return null;
    } finally {
      setLoadingDetail(false);
    }
  };

  const loadJobSnapshot = async (jobId) => {
    if (!jobId) return;
    try {
      const res = await apiRequest(`/api/v1/users/client/app/meal-plan-generation/jobs/${jobId}/`, { auth: true });
      if (res.ok) {
        setJobSnapshot(res.data?.generation || null);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadLatestDetail(dayOfWeek).catch((err) => console.error(err));
  }, [dayOfWeek]);

  useEffect(() => () => {
    if (weekPollTimeoutRef.current) {
      clearTimeout(weekPollTimeoutRef.current);
      weekPollTimeoutRef.current = null;
    }
  }, []);

  const handleRunGeneration = async () => {
    setRunning(true);
    setError('');
    setMessage('');
    setGenerationResult(null);
    setGenerationWeekResult(null);
    setJobSnapshot(null);
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
            <button type="button" className="client-q-btn" onClick={handleRunGeneration} disabled={running}>
              {running ? 'Running Steps 1-10…' : `Run ${prettyDay(dayOfWeek)} Generation`}
            </button>
            <button type="button" className="client-q-btn" onClick={handleRunWholeWeek} disabled={running}>
              {running ? 'Running Week…' : 'Run Whole Week'}
            </button>
            <button type="button" className="client-q-btn secondary" onClick={() => loadLatestDetail(dayOfWeek)} disabled={loadingDetail || running}>
              {loadingDetail ? 'Loading…' : 'Load Latest Detailed Plan'}
            </button>
          </div>
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

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 980 }}>
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
                <tbody>
                  {(detail.meals || []).map((meal) => (
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
                  ))}
                  {(!detail.meals || detail.meals.length === 0) && (
                    <tr>
                      <td colSpan={8} style={{ padding: '0.75rem' }}>No generated rows found for this day.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

export default ClientMealPlanGenerationPage;
