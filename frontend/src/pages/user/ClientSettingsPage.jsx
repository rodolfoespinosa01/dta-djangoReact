import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiRequest } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import './ClientDashboardPage.css';

function ClientSettingsPage() {
  const { logout } = useAuth();
  const [loading, setLoading] = useState(true);
  const [settings, setSettings] = useState(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busyAction, setBusyAction] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    const res = await apiRequest('/api/v1/users/client/app/settings/', { auth: true });
    if (!res.ok) {
      setError(res.data?.error?.message || 'Unable to load client settings.');
      setLoading(false);
      return;
    }
    setSettings(res.data?.settings || null);
    setLoading(false);
  };

  useEffect(() => {
    load().catch((err) => {
      console.error(err);
      setError('Unable to load client settings.');
      setLoading(false);
    });
  }, []);

  const runAction = async (action) => {
    setBusyAction(action);
    setError('');
    setMessage('');
    try {
      const res = await apiRequest('/api/v1/users/client/app/settings/plan-action/', {
        method: 'POST',
        auth: true,
        body: { action },
      });
      if (!res.ok) {
        setError(res.data?.error?.message || 'Unable to update plan.');
        return;
      }
      setSettings(res.data?.settings || settings);
      setMessage(res.data?.message || 'Plan updated.');
    } catch (err) {
      console.error(err);
      setError('Network error while updating plan.');
    } finally {
      setBusyAction('');
    }
  };

  if (loading) return <div className="client-dashboard-page"><p>Loading settings…</p></div>;
  if (error && !settings) return <div className="client-dashboard-page"><p className="client-dash-error">{error}</p></div>;

  return (
    <div className="client-dashboard-page">
      <header className="client-dashboard-header">
        <div>
          <h1>Client Settings</h1>
          <p className="client-dash-muted">Manage your plan access and subscription state (DEV flow).</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <Link className="client-q-btn secondary" to="/client_dashboard">Back to Dashboard</Link>
          {settings?.includes_food_plan ? <Link className="client-q-btn" to="/client_food_preferences">Food Preferences</Link> : null}
          <button type="button" className="client-q-btn danger" onClick={() => logout('/client_login')}>
            Log Out
          </button>
        </div>
      </header>

      {message ? <p className="client-q-message">{message}</p> : null}
      {error ? <p className="client-q-error">{error}</p> : null}

      <section className="client-dashboard-card">
        <h2>Plan Overview</h2>
        <div className="client-dash-chips">
          <span>{settings?.offer_code || '-'}</span>
          <span>{settings?.billing_cycle || '-'}</span>
          <span>{settings?.is_active ? 'active' : 'canceled'}</span>
          {settings?.trial_days ? <span>{settings.trial_days}-day trial</span> : null}
        </div>
        <ul>
          <li>Food plan access: {settings?.includes_food_plan ? 'Enabled' : 'Not included'}</li>
          <li>Coaching messaging: {settings?.includes_coaching ? 'Enabled' : 'Not included'}</li>
          <li>Current charge: ${((settings?.amount_cents || 0) / 100).toFixed(2)}</li>
        </ul>
      </section>

      <section className="client-dashboard-card">
        <h2>Plan Actions</h2>
        <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
          {settings?.available_actions?.start_free_trial ? (
            <button type="button" className="client-q-btn" onClick={() => runAction('start_free_trial')} disabled={busyAction !== ''}>
              {busyAction === 'start_free_trial' ? 'Starting…' : 'Start 5-Day Free Trial (Weekly)'}
            </button>
          ) : null}
          {settings?.available_actions?.switch_weekly ? (
            <button type="button" className="client-q-btn secondary" onClick={() => runAction('switch_weekly')} disabled={busyAction !== ''}>
              {busyAction === 'switch_weekly' ? 'Updating…' : 'Switch to Weekly ($5)'}
            </button>
          ) : null}
          {settings?.available_actions?.switch_monthly ? (
            <button type="button" className="client-q-btn secondary" onClick={() => runAction('switch_monthly')} disabled={busyAction !== ''}>
              {busyAction === 'switch_monthly' ? 'Updating…' : 'Switch to Monthly ($15)'}
            </button>
          ) : null}
          {settings?.available_actions?.cancel ? (
            <button type="button" className="client-q-btn danger" onClick={() => runAction('cancel_subscription')} disabled={busyAction !== ''}>
              {busyAction === 'cancel_subscription' ? 'Canceling…' : 'Cancel Subscription'}
            </button>
          ) : null}
          {settings?.available_actions?.reactivate ? (
            <button type="button" className="client-q-btn secondary" onClick={() => runAction('reactivate_subscription')} disabled={busyAction !== ''}>
              {busyAction === 'reactivate_subscription' ? 'Reactivating…' : 'Reactivate Subscription'}
            </button>
          ) : null}
        </div>
      </section>
    </div>
  );
}

export default ClientSettingsPage;
