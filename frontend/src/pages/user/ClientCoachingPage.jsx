import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { apiRequest } from '../../api/client';
import './ClientDashboardPage.css';

function ClientCoachingPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [includesCoaching, setIncludesCoaching] = useState(false);

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
          setError(res.data?.error?.message || 'Unable to load coaching dashboard.');
          return;
        }
        setIncludesCoaching(Boolean(res.data?.client?.includes_coaching));
      } catch (err) {
        console.error(err);
        if (!ignore) setError('Network error while loading coaching dashboard.');
      } finally {
        if (!ignore) setLoading(false);
      }
    };
    load();
    return () => { ignore = true; };
  }, [navigate]);

  return (
    <div className="client-dashboard-page">
      <header className="client-dashboard-header">
        <div>
          <h1>Coaching Dashboard</h1>
          <p className="client-dash-muted">
            Stay in touch with your coach from one place.
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
        <h2>Status</h2>
        {loading ? <p className="client-dash-muted">Loading coaching status…</p> : null}
        {!loading && error ? <p className="client-q-error">{error}</p> : null}
        {!loading && !error ? (
          includesCoaching ? (
            <p className="client-dash-muted">
              Coaching access is active. Messaging and coach workflow modules will appear here next.
            </p>
          ) : (
            <p className="client-dash-muted">
              Coaching is not enabled on your current plan yet.
            </p>
          )
        ) : null}
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button type="button" className="client-q-btn secondary" onClick={() => navigate('/client_settings')}>
            Manage Plan
          </button>
        </div>
      </section>

      <section className="client-dashboard-card">
        <h2>Coming Soon</h2>
        <ul>
          <li>Coach-client direct messaging</li>
          <li>Shared weekly check-ins</li>
          <li>Progress updates and feedback loops</li>
          <li>Coach action history</li>
        </ul>
      </section>
    </div>
  );
}

export default ClientCoachingPage;
