import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { apiRequest } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import './ClientDashboardPage.css';

function normalizeSubdomainLabel(slug) {
  return slug ? `${slug}.dtameals.com` : 'DTA Direct';
}

function portalLabel(settings) {
  if (!settings) return 'Client Portal';
  return settings.sale_channel === 'admin_white_label' ? 'Coach Portal' : 'DTA Direct Portal';
}

function isPremiumOffer(offerCode) {
  return String(offerCode || '').includes('_premium');
}

function QuoteSummary({ quote }) {
  if (!quote) return null;
  const amounts = quote.amounts || {};
  const entitlements = quote.entitlements_preview || {};
  return (
    <div style={{ border: '1px solid rgba(20,40,74,0.1)', borderRadius: 10, padding: '0.75rem', marginTop: '0.65rem' }}>
      <div className="client-dash-chips">
        <span>{quote.offer_display_name || quote.offer_code}</span>
        <span>{quote.billing_cycle}</span>
        <span>Total: ${((amounts.total_cents || 0) / 100).toFixed(2)}</span>
        {quote.trial_days ? <span>{quote.trial_days}-day trial</span> : null}
      </div>
      <ul style={{ marginTop: '0.5rem' }}>
        <li>Plan amount: ${((amounts.plan_final_cents || 0) / 100).toFixed(2)}</li>
        {(amounts.coaching_addon_final_cents || 0) > 0 ? (
          <li>Coaching add-on: ${((amounts.coaching_addon_final_cents || 0) / 100).toFixed(2)}</li>
        ) : null}
        <li>Discount: -${((amounts.discount_cents || 0) / 100).toFixed(2)} {quote.discount?.code ? `(${quote.discount.code})` : ''}</li>
        <li>Premium dashboard: {entitlements.has_premium_dashboard ? 'Included' : 'Not included'}</li>
      </ul>
    </div>
  );
}

function ClientSettingsPage() {
  const { logout } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [settings, setSettings] = useState(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busyAction, setBusyAction] = useState('');
  const [checkoutBusy, setCheckoutBusy] = useState(false);
  const [checkoutOfferCode, setCheckoutOfferCode] = useState('food_plan_monthly');
  const [checkoutCoachingTerm, setCheckoutCoachingTerm] = useState('none');
  const [checkoutDiscountCode, setCheckoutDiscountCode] = useState('');
  const [checkoutQuoteBusy, setCheckoutQuoteBusy] = useState(false);
  const [checkoutQuote, setCheckoutQuote] = useState(null);
  const [queuedCheckoutBusy, setQueuedCheckoutBusy] = useState(false);
  const [queuedCheckoutOfferCode, setQueuedCheckoutOfferCode] = useState('food_plan_monthly');
  const [queuedCheckoutCoachingTerm, setQueuedCheckoutCoachingTerm] = useState('none');
  const [queuedCheckoutDiscountCode, setQueuedCheckoutDiscountCode] = useState('');
  const [queuedCheckoutQuoteBusy, setQueuedCheckoutQuoteBusy] = useState(false);
  const [queuedCheckoutQuote, setQueuedCheckoutQuote] = useState(null);

  const load = async () => {
    setLoading(true);
    setError('');
    const res = await apiRequest('/api/v1/users/client/app/settings/', { auth: true });
    if (!res.ok) {
      setError(res.data?.error?.message || 'Unable to load client settings.');
      setLoading(false);
      return null;
    }
    const nextSettings = res.data?.settings || null;
    setSettings(nextSettings);
    setLoading(false);
    return nextSettings;
  };

  useEffect(() => {
    load().catch((err) => {
      console.error(err);
      setError('Unable to load client settings.');
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    const checkoutState = searchParams.get('checkout') || searchParams.get('queued_checkout');
    const sessionId = searchParams.get('session_id');
    if (checkoutState !== 'success') return undefined;

    let canceled = false;
    let attempts = 0;
    setMessage('Checkout completed. Updating your plan access…');

    const run = async () => {
      attempts += 1;
      try {
        if (sessionId) {
          await apiRequest('/api/v1/users/client/app/settings/checkout-sync/', {
            method: 'POST',
            auth: true,
            body: { session_id: sessionId },
          });
        }
        const latestSettings = await load();
        if (canceled) return;
        // Stop polling once food plan access is present or after a few attempts.
        if ((latestSettings?.includes_food_plan || attempts >= 6)) {
          setSearchParams((prev) => {
            const next = new URLSearchParams(prev);
            next.delete('checkout');
            next.delete('queued_checkout');
            next.delete('session_id');
            return next;
          }, { replace: true });
          if (attempts >= 6 && !latestSettings?.includes_food_plan) {
            setMessage('Checkout returned successfully. If access has not updated yet, refresh in a few seconds.');
          }
          return;
        }
      } catch (err) {
        console.error(err);
      }
      if (!canceled && attempts < 6) {
        setTimeout(run, 1500);
      }
    };

    // Start a short polling window to wait for Stripe webhook processing.
    run();
    return () => { canceled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, setSearchParams]);

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

  useEffect(() => {
    if (isPremiumOffer(checkoutOfferCode) && checkoutCoachingTerm !== 'none') {
      setCheckoutCoachingTerm('none');
    }
  }, [checkoutOfferCode, checkoutCoachingTerm]);

  useEffect(() => {
    if (isPremiumOffer(queuedCheckoutOfferCode) && queuedCheckoutCoachingTerm !== 'none') {
      setQueuedCheckoutCoachingTerm('none');
    }
  }, [queuedCheckoutOfferCode, queuedCheckoutCoachingTerm]);

  const fetchCheckoutQuote = async (purchaseMode) => {
    const isQueued = purchaseMode === 'payment';
    const offerCode = isQueued ? queuedCheckoutOfferCode : checkoutOfferCode;
    const coachingTerm = isQueued ? queuedCheckoutCoachingTerm : checkoutCoachingTerm;
    const discountCode = isQueued ? queuedCheckoutDiscountCode : checkoutDiscountCode;
    const setBusy = isQueued ? setQueuedCheckoutQuoteBusy : setCheckoutQuoteBusy;
    const setQuote = isQueued ? setQueuedCheckoutQuote : setCheckoutQuote;

    setBusy(true);
    setError('');
    try {
      const res = await apiRequest('/api/v1/users/client/app/settings/checkout-quote/', {
        method: 'POST',
        auth: true,
        body: {
          offer_code: offerCode,
          coaching_term: coachingTerm,
          discount_code: discountCode,
          purchase_mode: purchaseMode,
        },
      });
      if (!res.ok) {
        setQuote(null);
        setError(res.data?.error?.message || 'Unable to preview checkout price.');
        return null;
      }
      const quotePayload = res.data?.quote || null;
      setQuote(quotePayload);
      return quotePayload;
    } catch (err) {
      console.error(err);
      setQuote(null);
      setError('Network error while previewing checkout price.');
      return null;
    } finally {
      setBusy(false);
    }
  };

  const startStripeCheckout = async () => {
    setCheckoutBusy(true);
    setError('');
    setMessage('');
    try {
      const res = await apiRequest('/api/v1/users/client/app/settings/start-checkout/', {
        method: 'POST',
        auth: true,
        body: {
          offer_code: checkoutOfferCode,
          coaching_term: checkoutCoachingTerm,
          discount_code: checkoutDiscountCode.trim(),
        },
      });
      if (!res.ok) {
        setError(res.data?.error?.message || 'Unable to start checkout.');
        return;
      }
      if (res.data?.checkout_url) {
        window.location.href = res.data.checkout_url;
        return;
      }
      setError('Checkout URL was not returned.');
    } catch (err) {
      console.error(err);
      setError('Network error while starting checkout.');
    } finally {
      setCheckoutBusy(false);
    }
  };

  const startQueuedStripeCheckout = async () => {
    setQueuedCheckoutBusy(true);
    setError('');
    setMessage('');
    try {
      const res = await apiRequest('/api/v1/users/client/app/settings/start-queued-checkout/', {
        method: 'POST',
        auth: true,
        body: {
          offer_code: queuedCheckoutOfferCode,
          coaching_term: queuedCheckoutCoachingTerm,
          discount_code: queuedCheckoutDiscountCode.trim(),
        },
      });
      if (!res.ok) {
        setError(res.data?.error?.message || 'Unable to start queued checkout.');
        return;
      }
      if (res.data?.checkout_url) {
        window.location.href = res.data.checkout_url;
        return;
      }
      setError('Queued checkout URL was not returned.');
    } catch (err) {
      console.error(err);
      setError('Network error while starting queued checkout.');
    } finally {
      setQueuedCheckoutBusy(false);
    }
  };

  if (loading) return <div className="client-dashboard-page"><p>Loading settings…</p></div>;
  if (error && !settings) return <div className="client-dashboard-page"><p className="client-dash-error">{error}</p></div>;

  const hasActivePaidAccess = Boolean(
    settings
    && settings.is_active
    && settings.includes_food_plan
    && settings.offer_code !== 'macro_calculator_free'
  );

  return (
    <div className="client-dashboard-page">
      <header className="client-dashboard-header">
        <div>
          <h1>Client Settings</h1>
          <div className="client-dash-chips" style={{ marginTop: '0.35rem' }}>
            <span>{portalLabel(settings)}</span>
            <span>Source: {normalizeSubdomainLabel(settings?.associated_admin_slug)}</span>
          </div>
          <p className="client-dash-muted">Manage your plan access and subscription state.</p>
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
          <li>Coaching term: {settings?.coaching_term || 'none'}</li>
          <li>Coaching access until: {settings?.coaching_expires_at ? new Date(settings.coaching_expires_at).toLocaleString() : 'N/A'}</li>
          <li>Auto-renew: {settings?.cancel_at_period_end ? 'Off (cancels at period end)' : 'On'}</li>
          <li>Current charge: ${((settings?.amount_cents || 0) / 100).toFixed(2)}</li>
        </ul>
      </section>

      {!hasActivePaidAccess ? (
        <section className="client-dashboard-card">
          <h2>Secure Checkout (Stripe)</h2>
          <p className="client-dash-muted">
            Start your 3-day free trial by entering a card in Stripe. Trial access includes 1 meal plan generation per day.
          </p>
          <div className="client-q-inline-grid">
            <label>
              1-Month Plan
              <select value={checkoutOfferCode} onChange={(e) => setCheckoutOfferCode(e.target.value)} disabled={checkoutBusy}>
                <option value="food_plan_monthly">Monthly ($15/month)</option>
                <option value="food_plan_monthly_premium">Monthly Premium Coaching ($35/month)</option>
              </select>
            </label>
            <label>
              Discount Code
              <input
                type="text"
                value={checkoutDiscountCode}
                onChange={(e) => setCheckoutDiscountCode(e.target.value.toUpperCase())}
                placeholder="Optional code"
                disabled={checkoutBusy}
              />
            </label>
          </div>
          <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
            <button type="button" className="client-q-btn secondary" onClick={() => fetchCheckoutQuote('subscription')} disabled={checkoutQuoteBusy || checkoutBusy}>
              {checkoutQuoteBusy ? 'Previewing…' : 'Preview Price'}
            </button>
            <button type="button" className="client-q-btn" onClick={startStripeCheckout} disabled={checkoutBusy}>
              {checkoutBusy ? 'Redirecting…' : 'Go To Secure Checkout'}
            </button>
          </div>
          {isPremiumOffer(checkoutOfferCode) ? (
            <p className="client-dash-muted" style={{ marginTop: '0.5rem' }}>
              This plan includes coaching and premium dashboard access.
            </p>
          ) : null}
          <QuoteSummary quote={checkoutQuote} />
        </section>
      ) : (
        <section className="client-dashboard-card">
          <h2>Queue a Paid Plan Change (No Proration)</h2>
          <p className="client-dash-muted">
            Your paid access stays active. Use secure checkout to pay now and queue the next 1-month plan for your next billing period.
          </p>
          <div className="client-q-inline-grid">
            <label>
              Next 1-Month Plan
              <select value={queuedCheckoutOfferCode} onChange={(e) => setQueuedCheckoutOfferCode(e.target.value)} disabled={queuedCheckoutBusy}>
                <option value="food_plan_monthly">Monthly ($15/month)</option>
                <option value="food_plan_monthly_premium">Monthly Premium Coaching ($35/month)</option>
              </select>
            </label>
            <label>
              Discount Code
              <input
                type="text"
                value={queuedCheckoutDiscountCode}
                onChange={(e) => setQueuedCheckoutDiscountCode(e.target.value.toUpperCase())}
                placeholder="Optional code"
                disabled={queuedCheckoutBusy}
              />
            </label>
          </div>
          <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
            <button type="button" className="client-q-btn secondary" onClick={() => fetchCheckoutQuote('payment')} disabled={queuedCheckoutQuoteBusy || queuedCheckoutBusy}>
              {queuedCheckoutQuoteBusy ? 'Previewing…' : 'Preview Queued Price'}
            </button>
            <button type="button" className="client-q-btn" onClick={startQueuedStripeCheckout} disabled={queuedCheckoutBusy}>
              {queuedCheckoutBusy ? 'Redirecting…' : 'Queue Next Plan (Secure Checkout)'}
            </button>
          </div>
          {isPremiumOffer(queuedCheckoutOfferCode) ? (
            <p className="client-dash-muted" style={{ marginTop: '0.5rem' }}>
              This queued plan includes coaching and premium dashboard access.
            </p>
          ) : null}
          <QuoteSummary quote={queuedCheckoutQuote} />
          {(settings?.queued_changes || []).length ? (
            <div style={{ marginTop: '0.75rem' }}>
              <h3 style={{ marginBottom: '0.5rem' }}>Queued Purchases</h3>
              <div className="client-q-stack">
                {settings.queued_changes.map((q) => (
                  <div key={`queued-${q.id}`} style={{ border: '1px solid rgba(20,40,74,0.1)', borderRadius: 10, padding: '0.65rem' }}>
                    <div className="client-dash-chips">
                      <span>{q.target_offer_code}</span>
                      <span>{q.target_coaching_term || 'none'}</span>
                      <span>${((q.amount_cents || 0) / 100).toFixed(2)}</span>
                      <span>{q.status}</span>
                    </div>
                    <p className="client-dash-muted" style={{ marginTop: '0.4rem' }}>
                      Queued for period end: {q.queued_for_period_end_at ? new Date(q.queued_for_period_end_at).toLocaleString() : 'TBD'}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </section>
      )}

      <section className="client-dashboard-card">
        <h2>Subscription Controls</h2>
        <p className="client-dash-muted">Manage auto-renew for your active subscription.</p>
        <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
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
          {!settings?.available_actions?.cancel && !settings?.available_actions?.reactivate ? (
            <span className="client-dash-muted">No subscription controls available for this plan yet.</span>
          ) : null}
        </div>
      </section>
    </div>
  );
}

export default ClientSettingsPage;
