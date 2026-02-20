import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { apiRequest } from '../../api/client';
import './SuperAdminAnalyticsPage.css';

const PERIODS = ['day', 'week', 'month'];

function SuperAdminAnalyticsPage() {
  const { user, isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();
  const [period, setPeriod] = useState('day');
  const [analytics, setAnalytics] = useState(null);
  const [error, setError] = useState('');
  const [isFetching, setIsFetching] = useState(true);

  useEffect(() => {
    if (loading) return;
    if (!isAuthenticated || !user?.is_superuser) {
      navigate('/superadmin_login');
    }
  }, [loading, isAuthenticated, user, navigate]);

  useEffect(() => {
    setError('');
    setAnalytics(null);
    setIsFetching(true);
    const query = new URLSearchParams({ period }).toString();

    apiRequest(`/api/v1/users/superadmin/analytics/?${query}`, { auth: true })
      .then(({ ok, data }) => {
        if (!ok || data?.ok === false) throw new Error(data?.error?.message || 'Failed to load analytics');
        return data;
      })
      .then((data) => setAnalytics(data))
      .catch((err) => {
        setError(err.message || 'Failed to load analytics');
      })
      .finally(() => setIsFetching(false));
  }, [period, navigate]);

  const maxPoint = useMemo(() => {
    if (!analytics?.points?.length) return 1;
    return Math.max(...analytics.points.map((point) => point.amount_cents), 1);
  }, [analytics]);

  const currencyFormatter = useMemo(() => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: analytics?.currency || 'USD',
      minimumFractionDigits: 2,
    });
  }, [analytics?.currency]);

  const windowLabel = useMemo(() => {
    if (!analytics?.window?.started_at || !analytics?.window?.ended_at) return '';
    const started = new Date(analytics.window.started_at);
    const ended = new Date(analytics.window.ended_at);
    return `${started.toLocaleString()} - ${ended.toLocaleString()}`;
  }, [analytics?.window?.started_at, analytics?.window?.ended_at]);

  if (loading || isFetching) {
    return <p className="superadmin-loading">Loading analytics...</p>;
  }

  return (
    <div className="superadmin-analytics-page">
      <div className="superadmin-analytics-header">
        <h2>Sales Analytics</h2>
        <button
          type="button"
          className="superadmin-back-button"
          onClick={() => navigate('/superadmin_dashboard')}
        >
          Back to Dashboard
        </button>
      </div>

      <div className="superadmin-period-filters">
        {PERIODS.map((value) => (
          <button
            key={value}
            type="button"
            className={`superadmin-period-button ${period === value ? 'active' : ''}`}
            onClick={() => setPeriod(value)}
          >
            {value}
          </button>
        ))}
      </div>

      {error && <p className="superadmin-analytics-error">{error}</p>}
      {!error && !analytics && <p className="superadmin-analytics-error">No analytics available yet.</p>}

      <section className="superadmin-metrics-grid">
        <article className="superadmin-metric-card">
          <p>Total Revenue</p>
          <h3>{currencyFormatter.format(Number(analytics?.total_revenue || 0))}</h3>
        </article>
        <article className="superadmin-metric-card">
          <p>Transactions</p>
          <h3>{analytics?.transactions || 0}</h3>
        </article>
      </section>
      {windowLabel && <p className="superadmin-window-label">Window: {windowLabel}</p>}

      <section className="superadmin-chart-card" aria-label="Revenue chart">
        <div className="superadmin-chart">
          {(analytics?.points || []).map((point) => {
            const height = Math.max((point.amount_cents / maxPoint) * 100, point.amount_cents > 0 ? 6 : 2);

            return (
              <div className="superadmin-chart-item" key={point.label}>
                <div className="superadmin-chart-value">${point.amount.toFixed(0)}</div>
                <div className="superadmin-chart-bar-wrap">
                  <div className="superadmin-chart-bar" style={{ height: `${height}%` }} />
                </div>
                <div className="superadmin-chart-label">{point.label}</div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

export default SuperAdminAnalyticsPage;
