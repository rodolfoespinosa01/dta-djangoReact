import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiRequest } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import './ClientDashboardPage.css';

function todayIsoDate() {
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const dd = String(now.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

function nowIsoTime() {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, '0');
  const mm = String(now.getMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

function ClientTrackingPage() {
  const { logout } = useAuth();
  const [activePanel, setActivePanel] = useState('both');
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [photos, setPhotos] = useState([]);
  const [tracking, setTracking] = useState(null);
  const [weightsLoading, setWeightsLoading] = useState(true);
  const [weightSaving, setWeightSaving] = useState(false);
  const [weightError, setWeightError] = useState('');
  const [weightMessage, setWeightMessage] = useState('');
  const [weights, setWeights] = useState([]);
  const [weightSummary, setWeightSummary] = useState(null);
  const [form, setForm] = useState({
    captured_for_date: todayIsoDate(),
    notes: '',
    same_position: true,
    same_lighting: true,
    same_time_of_day: true,
    photo: null,
    include_weight: false,
    measured_time: nowIsoTime(),
    weight_value: '',
    weight_unit: 'lbs',
    weight_notes: '',
  });
  const [weightForm, setWeightForm] = useState({
    measured_date: todayIsoDate(),
    measured_time: nowIsoTime(),
    weight_value: '',
    unit: 'lbs',
    notes: '',
  });

  const selectedFileLabel = useMemo(() => form.photo?.name || 'No file selected', [form.photo]);

  const loadTracking = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await apiRequest('/api/v1/users/client/app/tracking/photos/', { auth: true });
      if (!res.ok) {
        setError(res.data?.error?.message || 'Unable to load tracking data.');
        return;
      }
      setPhotos(Array.isArray(res.data?.photos) ? res.data.photos : []);
      setTracking(res.data?.tracking || null);
    } catch (err) {
      console.error(err);
      setError('Network error while loading tracking data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTracking();
    loadWeights();
  }, []);

  const loadWeights = async () => {
    setWeightsLoading(true);
    setWeightError('');
    try {
      const res = await apiRequest('/api/v1/users/client/app/tracking/weights/', { auth: true });
      if (!res.ok) {
        setWeightError(res.data?.error?.message || 'Unable to load weight entries.');
        return;
      }
      setWeights(Array.isArray(res.data?.weights) ? res.data.weights : []);
      setWeightSummary(res.data?.summary || null);
    } catch (err) {
      console.error(err);
      setWeightError('Network error while loading weights.');
    } finally {
      setWeightsLoading(false);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    if (!form.photo) {
      setError('Please choose a photo first.');
      return;
    }

    const body = new FormData();
    body.append('photo', form.photo);
    body.append('captured_for_date', form.captured_for_date);
    body.append('notes', form.notes);
    body.append('same_position', form.same_position ? '1' : '0');
    body.append('same_lighting', form.same_lighting ? '1' : '0');
    body.append('same_time_of_day', form.same_time_of_day ? '1' : '0');
    if (form.include_weight && form.weight_value) {
      body.append('weight_value', form.weight_value);
      body.append('weight_unit', form.weight_unit);
      body.append('measured_time', form.measured_time);
      body.append('weight_notes', form.weight_notes);
    }

    setUploading(true);
    try {
      const res = await apiRequest('/api/v1/users/client/app/tracking/photos/', {
        method: 'POST',
        auth: true,
        body,
      });
      if (!res.ok) {
        setError(res.data?.error?.message || 'Unable to upload photo.');
        return;
      }
      setMessage(res.data?.weight ? 'Photo and weight saved.' : 'Photo uploaded.');
      setForm((prev) => ({ ...prev, photo: null, notes: '', weight_value: '', weight_notes: '' }));
      await loadTracking();
      if (res.data?.weight) await loadWeights();
    } catch (err) {
      console.error(err);
      setError('Network error while uploading photo.');
    } finally {
      setUploading(false);
    }
  };

  const handleWeightSave = async (e) => {
    e.preventDefault();
    setWeightError('');
    setWeightMessage('');
    if (!weightForm.weight_value) {
      setWeightError('Please enter a weight value.');
      return;
    }
    setWeightSaving(true);
    try {
      const res = await apiRequest('/api/v1/users/client/app/tracking/weights/', {
        method: 'POST',
        auth: true,
        body: {
          measured_date: weightForm.measured_date,
          measured_time: weightForm.measured_time,
          weight_value: weightForm.weight_value,
          unit: weightForm.unit,
          notes: weightForm.notes,
        },
      });
      if (!res.ok) {
        setWeightError(res.data?.error?.message || 'Unable to save weight entry.');
        return;
      }
      setWeightMessage('Weight entry saved.');
      setWeightForm((prev) => ({ ...prev, weight_value: '', notes: '' }));
      await loadWeights();
    } catch (err) {
      console.error(err);
      setWeightError('Network error while saving weight entry.');
    } finally {
      setWeightSaving(false);
    }
  };

  return (
    <div className="client-dashboard-page">
      <header className="client-dashboard-header">
        <div>
          <h1>Tracking</h1>
          <p className="client-dash-muted">
            Upload progress photos once a week (recommended). Daily uploads are allowed, up to 30 photos per month.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <Link className="client-q-btn secondary" to="/client_dashboard">Back to Dashboard</Link>
          <button type="button" className="client-q-btn danger" onClick={() => logout('/client_login')}>
            Log Out
          </button>
        </div>
      </header>

      <section className="client-dashboard-card">
        <h2>Photo Tracking Rules</h2>
        <ul>
          <li>Take photos in the same position each time.</li>
          <li>Use similar lighting conditions.</li>
          <li>Take them around the same time of day.</li>
          <li>Recommended: once a week. Maximum: once per day, 30 per month.</li>
        </ul>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.75rem' }}>
          <button
            type="button"
            className={`client-q-btn ${activePanel === 'photo' ? '' : 'secondary'}`}
            onClick={() => setActivePanel('photo')}
          >
            Upload Photo
          </button>
          <button
            type="button"
            className={`client-q-btn ${activePanel === 'weight' ? '' : 'secondary'}`}
            onClick={() => setActivePanel('weight')}
          >
            Track Weight
          </button>
          <button
            type="button"
            className={`client-q-btn ${activePanel === 'both' ? '' : 'secondary'}`}
            onClick={() => setActivePanel('both')}
          >
            Both
          </button>
        </div>
      </section>

      {activePanel === 'weight' || activePanel === 'both' ? (
      <section className="client-dashboard-card">
        <h2>Weight Tracker</h2>
        <p className="client-dash-muted">
          Log body weight with date and time for better trend comparison.
        </p>
        {weightError ? <p className="client-auth-error">{weightError}</p> : null}
        {weightMessage ? <p style={{ color: '#0f766e', fontWeight: 600 }}>{weightMessage}</p> : null}
        {weightsLoading ? <p className="client-dash-muted">Loading weight entries…</p> : null}
        {!weightsLoading && weightSummary?.latest_weight ? (
          <p className="client-dash-muted">
            Latest: {weightSummary.latest_weight} {weightSummary.latest_unit} ({weightSummary.entry_count} entries)
          </p>
        ) : null}

        <form onSubmit={handleWeightSave} style={{ display: 'grid', gap: '0.75rem', marginTop: '0.5rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '0.6rem' }}>
            <label style={{ display: 'grid', gap: '0.35rem' }}>
              Date
              <input
                type="date"
                value={weightForm.measured_date}
                onChange={(e) => setWeightForm((prev) => ({ ...prev, measured_date: e.target.value }))}
                max={todayIsoDate()}
                required
              />
            </label>
            <label style={{ display: 'grid', gap: '0.35rem' }}>
              Time of day
              <input
                type="time"
                value={weightForm.measured_time}
                onChange={(e) => setWeightForm((prev) => ({ ...prev, measured_time: e.target.value }))}
                required
              />
            </label>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) minmax(0, 1fr)', gap: '0.6rem' }}>
            <label style={{ display: 'grid', gap: '0.35rem' }}>
              Weight
              <input
                type="number"
                step="0.1"
                min="1"
                value={weightForm.weight_value}
                onChange={(e) => setWeightForm((prev) => ({ ...prev, weight_value: e.target.value }))}
                placeholder="e.g. 185.4"
                required
              />
            </label>
            <label style={{ display: 'grid', gap: '0.35rem' }}>
              Unit
              <select
                value={weightForm.unit}
                onChange={(e) => setWeightForm((prev) => ({ ...prev, unit: e.target.value }))}
              >
                <option value="lbs">lbs</option>
                <option value="kg">kg</option>
              </select>
            </label>
          </div>
          <label style={{ display: 'grid', gap: '0.35rem' }}>
            Notes (optional)
            <input
              type="text"
              value={weightForm.notes}
              onChange={(e) => setWeightForm((prev) => ({ ...prev, notes: e.target.value }))}
              placeholder="Fasted, post-workout, etc."
              maxLength={160}
            />
          </label>
          <button type="submit" className="client-q-btn" disabled={weightSaving}>
            {weightSaving ? 'Saving…' : 'Save Weight'}
          </button>
        </form>

        {!weightsLoading && weights.length ? (
          <div style={{ marginTop: '0.85rem', display: 'grid', gap: '0.35rem' }}>
            {weights.slice(0, 30).map((row) => (
              <div key={row.id} style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem', borderBottom: '1px solid rgba(20,40,74,0.08)', paddingBottom: '0.35rem' }}>
                <strong>{row.weight_value} {row.unit}</strong>
                <span className="client-dash-muted">{row.measured_date} {row.measured_time}</span>
              </div>
            ))}
          </div>
        ) : null}
      </section>
      ) : null}

      {activePanel === 'photo' || activePanel === 'both' ? (
      <section className="client-dashboard-card">
        <h2>Upload Progress Photo</h2>
        {loading ? <p className="client-dash-muted">Loading tracking data…</p> : null}
        {!loading && tracking ? (
          <p className="client-dash-muted">
            {tracking.month}: {tracking.monthly_count}/{tracking.monthly_limit} uploaded ({tracking.monthly_remaining} remaining)
          </p>
        ) : null}
        {error ? <p className="client-auth-error">{error}</p> : null}
        {message ? <p style={{ color: '#0f766e', fontWeight: 600 }}>{message}</p> : null}

        <form onSubmit={handleUpload} style={{ display: 'grid', gap: '0.75rem', marginTop: '0.5rem' }}>
          <label style={{ display: 'grid', gap: '0.35rem' }}>
            Date
            <input
              type="date"
              value={form.captured_for_date}
              onChange={(e) => setForm((prev) => ({ ...prev, captured_for_date: e.target.value }))}
              max={todayIsoDate()}
              required
            />
          </label>
          <label style={{ display: 'grid', gap: '0.35rem' }}>
            Photo
            <input
              type="file"
              accept="image/*"
              capture="environment"
              onChange={(e) => setForm((prev) => ({ ...prev, photo: e.target.files?.[0] || null }))}
              required
            />
            <small className="client-dash-muted">{selectedFileLabel}</small>
          </label>
          <label style={{ display: 'grid', gap: '0.35rem' }}>
            Notes (optional)
            <input
              type="text"
              value={form.notes}
              onChange={(e) => setForm((prev) => ({ ...prev, notes: e.target.value }))}
              placeholder="Any context for this check-in"
              maxLength={300}
            />
          </label>
          <label>
            <input
              type="checkbox"
              checked={form.include_weight}
              onChange={(e) => setForm((prev) => ({ ...prev, include_weight: e.target.checked }))}
            />{' '}
            Log weight with this photo
          </label>
          {form.include_weight ? (
            <div style={{ display: 'grid', gap: '0.6rem', border: '1px solid rgba(20,40,74,0.1)', borderRadius: 10, padding: '0.6rem' }}>
              <strong>Weight with Photo</strong>
              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: '0.6rem' }}>
                <label style={{ display: 'grid', gap: '0.35rem' }}>
                  Time of day
                  <input
                    type="time"
                    value={form.measured_time}
                    onChange={(e) => setForm((prev) => ({ ...prev, measured_time: e.target.value }))}
                    required={form.include_weight}
                  />
                </label>
                <label style={{ display: 'grid', gap: '0.35rem' }}>
                  Unit
                  <select
                    value={form.weight_unit}
                    onChange={(e) => setForm((prev) => ({ ...prev, weight_unit: e.target.value }))}
                  >
                    <option value="lbs">lbs</option>
                    <option value="kg">kg</option>
                  </select>
                </label>
              </div>
              <label style={{ display: 'grid', gap: '0.35rem' }}>
                Weight value
                <input
                  type="number"
                  step="0.1"
                  min="1"
                  value={form.weight_value}
                  onChange={(e) => setForm((prev) => ({ ...prev, weight_value: e.target.value }))}
                  placeholder="e.g. 185.4"
                  required={form.include_weight}
                />
              </label>
              <label style={{ display: 'grid', gap: '0.35rem' }}>
                Weight notes (optional)
                <input
                  type="text"
                  value={form.weight_notes}
                  onChange={(e) => setForm((prev) => ({ ...prev, weight_notes: e.target.value }))}
                  maxLength={160}
                  placeholder="Fasted, post-workout, etc."
                />
              </label>
            </div>
          ) : null}
          <div style={{ display: 'grid', gap: '0.35rem' }}>
            <label><input type="checkbox" checked={form.same_position} onChange={(e) => setForm((prev) => ({ ...prev, same_position: e.target.checked }))} /> Same position</label>
            <label><input type="checkbox" checked={form.same_lighting} onChange={(e) => setForm((prev) => ({ ...prev, same_lighting: e.target.checked }))} /> Same lighting</label>
            <label><input type="checkbox" checked={form.same_time_of_day} onChange={(e) => setForm((prev) => ({ ...prev, same_time_of_day: e.target.checked }))} /> Same time of day</label>
          </div>
          <button type="submit" className="client-q-btn" disabled={uploading || loading}>
            {uploading ? 'Uploading…' : 'Upload Photo'}
          </button>
        </form>
      </section>
      ) : null}

      {activePanel === 'photo' || activePanel === 'both' ? (
      <section className="client-dashboard-card">
        <h2>Recent Uploads</h2>
        {!photos.length ? (
          <p className="client-dash-muted">No photos uploaded yet.</p>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: '0.75rem' }}>
            {photos.map((row) => (
              <article key={row.id} style={{ border: '1px solid rgba(20,40,74,0.12)', borderRadius: 10, padding: '0.5rem' }}>
                <img
                  src={row.file_url}
                  alt={`Progress ${row.captured_for_date}`}
                  style={{ width: '100%', aspectRatio: '3/4', objectFit: 'cover', borderRadius: 8, background: '#f4f7fb' }}
                />
                <div style={{ marginTop: '0.4rem', display: 'grid', gap: '0.15rem' }}>
                  <strong>{row.captured_for_date}</strong>
                  <small className="client-dash-muted">
                    {row.same_position ? 'Position' : 'Position*'} · {row.same_lighting ? 'Lighting' : 'Lighting*'} · {row.same_time_of_day ? 'Time' : 'Time*'}
                  </small>
                  {row.notes ? <small className="client-dash-muted">{row.notes}</small> : null}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
      ) : null}
    </div>
  );
}

export default ClientTrackingPage;
