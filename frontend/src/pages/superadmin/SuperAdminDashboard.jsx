import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useLanguage } from '../../context/LanguageContext';
import { apiRequest } from '../../api/client';
import './SuperAdminDashboard.css';

function SuperAdminDashboard() {
  const { user, isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [stats, setStats] = useState(null);
  const [page, setPage] = useState(1);
  const pageSize = 25;
  const [libraryMode, setLibraryMode] = useState('');
  const [libraryQuery, setLibraryQuery] = useState('');
  const [libraryPage, setLibraryPage] = useState(1);
  const [libraryData, setLibraryData] = useState(null);
  const [libraryLoading, setLibraryLoading] = useState(false);
  const [libraryError, setLibraryError] = useState('');
  const [selectedDirectClient, setSelectedDirectClient] = useState(null);
  const [directTracking, setDirectTracking] = useState(null);
  const [directTrackingLoading, setDirectTrackingLoading] = useState(false);
  const [directTrackingError, setDirectTrackingError] = useState('');

  const formatDateTime = (value) => {
    if (!value) return '—';
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return '—';
    return dt.toLocaleString();
  };

  const formatWeight = (value, unit) => {
    if (typeof value !== 'number' || Number.isNaN(value)) return '—';
    return `${value.toFixed(1)} ${String(unit || '').toUpperCase()}`;
  };

  const loadDirectClientTracking = async (client) => {
    if (!client?.client_user_id) return;
    setSelectedDirectClient(client);
    setDirectTrackingLoading(true);
    setDirectTrackingError('');
    try {
      const { ok, data } = await apiRequest(
        `/api/v1/users/superadmin/direct-clients/${client.client_user_id}/tracking/`,
        { auth: true },
      );
      if (!ok || data?.ok === false) {
        throw new Error(data?.error?.message || 'Unable to load client tracking.');
      }
      setDirectTracking(data);
    } catch (err) {
      console.error('Failed to load direct client tracking:', err);
      setDirectTracking(null);
      setDirectTrackingError(err.message || 'Unable to load client tracking.');
    } finally {
      setDirectTrackingLoading(false);
    }
  };

  useEffect(() => {
    if (loading) return;

    if (!isAuthenticated || !user?.is_superuser) {
      navigate('/superadmin_login');
      return;
    }

    apiRequest(`/api/v1/users/superadmin/dashboard/?page=${page}&page_size=${pageSize}`, { auth: true })
      .then(({ ok, data }) => {
        if (!ok || data?.ok === false) {
          throw new Error(data?.error?.message || 'Failed to fetch dashboard data');
        }
        return data;
      })
      .then(data => setStats(data))
      .catch(err => {
        console.error('Failed to fetch dashboard data:', err);
        navigate('/superadmin_login');
      });
  }, [loading, isAuthenticated, user, navigate, page]);

  useEffect(() => {
    if (loading) return;
    if (!isAuthenticated || !user?.is_superuser) return;
    if (!libraryMode) {
      setLibraryLoading(false);
      setLibraryError('');
      setLibraryData(null);
      return;
    }

    let ignore = false;
    setLibraryLoading(true);
    setLibraryError('');

    const params = new URLSearchParams({
      mode: libraryMode,
      page: String(libraryPage),
      page_size: '20',
    });
    if (libraryQuery.trim()) params.set('q', libraryQuery.trim());

    apiRequest(`/api/v1/users/superadmin/food-library/?${params.toString()}`, { auth: true })
      .then(({ ok, data }) => {
        if (!ok || data?.ok === false) {
          throw new Error(data?.error?.message || 'Failed to fetch food library');
        }
        if (!ignore) setLibraryData(data);
      })
      .catch((err) => {
        console.error('Failed to fetch food library:', err);
        if (!ignore) setLibraryError(err.message || 'Failed to fetch food library');
      })
      .finally(() => {
        if (!ignore) setLibraryLoading(false);
      });

    return () => { ignore = true; };
  }, [loading, isAuthenticated, user, libraryMode, libraryPage, libraryQuery]);

  useEffect(() => {
    setLibraryPage(1);
  }, [libraryMode]);

  if (loading || !stats) {
    return <p className="superadmin-loading">{t('superadmin_dashboard.loading')}</p>;
  }

  const dtaDirectClients = stats?.dta_direct_clients || {};
  const dtaDirectSummary = dtaDirectClients?.summary || {};
  const dtaDirectRegistered = Array.isArray(dtaDirectClients?.registered_clients) ? dtaDirectClients.registered_clients : [];
  const dtaDirectPending = Array.isArray(dtaDirectClients?.paid_not_registered) ? dtaDirectClients.paid_not_registered : [];

  return (
    <div className="superadmin-dashboard-page">
      <h2>{t('superadmin_dashboard.title')}</h2>

      <section className="superadmin-toolbar" aria-label="Food library sections">
        <button
          type="button"
          className={`superadmin-page-button ${libraryMode === 'foods' ? 'is-active' : ''}`}
          onClick={() => setLibraryMode('foods')}
        >
          Foods
        </button>
        <button
          type="button"
          className={`superadmin-page-button ${libraryMode === 'combos' ? 'is-active' : ''}`}
          onClick={() => setLibraryMode('combos')}
        >
          Meal Combos
        </button>
        <button
          type="button"
          className={`superadmin-page-button ${libraryMode === 'errors' ? 'is-active' : ''}`}
          onClick={() => setLibraryMode('errors')}
        >
          Error Table
        </button>
      </section>

      {!libraryMode && (
        <p className="superadmin-library-subtitle">
          Select a section above to view global food library data.
        </p>
      )}

      {libraryMode && (
      <section className="superadmin-library-panel">
        <div className="superadmin-library-header">
          <div>
            <h3 className="superadmin-section-title">Global Food Library</h3>
            <p className="superadmin-library-subtitle">
              Shared across all admins and direct-to-consumer plans. This is your master meal combo dataset.
            </p>
          </div>
          <div className="superadmin-library-counts">
            <span>Foods: {libraryData?.counts?.foods ?? '—'}</span>
            <span>Combos: {libraryData?.counts?.combos ?? '—'}</span>
            <span>Error Rows: {libraryData?.counts?.errors ?? '—'}</span>
          </div>
        </div>

        <div className="superadmin-library-controls">
          <input
            type="text"
            className="superadmin-library-search"
            placeholder={libraryMode === 'foods' ? 'Search foods...' : 'Search by ID or slot...'}
            value={libraryQuery}
            onChange={(e) => {
              setLibraryQuery(e.target.value);
              setLibraryPage(1);
            }}
          />
        </div>

        {libraryError && <p className="superadmin-library-error">{libraryError}</p>}
        {libraryLoading && <p className="superadmin-library-loading">Loading library data…</p>}

        {!libraryLoading && !libraryError && libraryMode === 'foods' && (
          <div className="superadmin-table-wrap">
            <table className="superadmin-library-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Category</th>
                  <th>Name</th>
                  <th>Unit</th>
                  <th>Protein</th>
                  <th>Carbs</th>
                  <th>Fats</th>
                </tr>
              </thead>
              <tbody>
                {(libraryData?.items || []).map((item) => (
                  <tr key={`food-${item.id}`} className={item.is_placeholder ? 'row-muted' : ''}>
                    <td>{item.id}</td>
                    <td>{item.category}</td>
                    <td>{item.name}</td>
                    <td>{item.measurement_unit}</td>
                    <td>{item.protein}</td>
                    <td>{item.carbs}</td>
                    <td>{item.fats}</td>
                  </tr>
                ))}
                {!libraryData?.items?.length && (
                  <tr><td colSpan="7">No food rows found.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {!libraryLoading && !libraryError && libraryMode === 'combos' && (
          <div className="superadmin-table-wrap">
            <table className="superadmin-library-table">
              <thead>
                <tr>
                  <th>Combo ID</th>
                  <th>P1</th>
                  <th>P2</th>
                  <th>C1</th>
                  <th>C2</th>
                  <th>F1</th>
                  <th>F2</th>
                </tr>
              </thead>
              <tbody>
                {(libraryData?.items || []).map((item) => (
                  <tr key={`combo-${item.id}`}>
                    <td>{item.id}</td>
                    <td>{item.protein_slot_1}</td>
                    <td>{item.protein_slot_2}</td>
                    <td>{item.carb_slot_1}</td>
                    <td>{item.carb_slot_2}</td>
                    <td>{item.fat_slot_1}</td>
                    <td>{item.fat_slot_2}</td>
                  </tr>
                ))}
                {!libraryData?.items?.length && (
                  <tr><td colSpan="7">No combo rows found.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {!libraryLoading && !libraryError && libraryMode === 'errors' && (
          <div className="superadmin-table-wrap">
            <table className="superadmin-library-table">
              <thead>
                <tr>
                  <th>Error ID</th>
                  <th>Protein Error</th>
                  <th>Carbs Error</th>
                  <th>Fats Error</th>
                </tr>
              </thead>
              <tbody>
                {(libraryData?.items || []).map((item) => (
                  <tr key={`err-${item.id}`}>
                    <td>{item.id}</td>
                    <td>{item.protein_error}</td>
                    <td>{item.carbs_error}</td>
                    <td>{item.fats_error}</td>
                  </tr>
                ))}
                {!libraryData?.items?.length && (
                  <tr><td colSpan="4">No error rows found.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        <div className="superadmin-library-footer">
          <div className="superadmin-library-hint">
            Next step: create platform meal-plan templates (super-admin defaults), then allow admins to clone/customize their own.
          </div>
          <div className="superadmin-pagination">
            <button
              type="button"
              className="superadmin-page-button"
              disabled={!libraryData?.pagination?.has_previous}
              onClick={() => setLibraryPage((prev) => Math.max(1, prev - 1))}
            >
              Previous
            </button>
            <span className="superadmin-page-meta">
              Page {libraryData?.pagination?.page || 1} of {libraryData?.pagination?.total_pages || 1}
            </span>
            <button
              type="button"
              className="superadmin-page-button"
              disabled={!libraryData?.pagination?.has_next}
              onClick={() => setLibraryPage((prev) => prev + 1)}
            >
              Next
            </button>
          </div>
        </div>
      </section>
      )}

      <h3 className="superadmin-section-title">{t('superadmin_dashboard.all_admins')}</h3>
      <div className="superadmin-toolbar">
        <button
          type="button"
          className="superadmin-analytics-button"
          onClick={() => navigate('/superadmin_analytics')}
        >
          Analytics
        </button>
      </div>
      <table className="superadmin-admins-table">
        <thead>
          <tr>
            <th>{t('superadmin_dashboard.email')}</th>
            <th>{t('superadmin_dashboard.plan')}</th>
            <th>{t('superadmin_dashboard.price')}</th>
            <th>Amount Spent</th>
            <th>{t('superadmin_dashboard.next_billing')}</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {stats.admins.map((admin, idx) => {
            const isInactive = admin.plan === 'admin_inactive';

            return (
              <tr key={idx} className={isInactive ? 'row-inactive' : ''}>
                <td>{admin.email}</td>
                <td>
                  {admin.plan}
                  {admin.plan === 'admin_trial' && admin.cancelled && (
                    <span className="superadmin-cancelled-tag">
                      {t('superadmin_dashboard.cancelled')}
                    </span>
                  )}
                </td>
                <td>{admin.price || ''}</td>
                <td>
                  {typeof admin.amount_spent === 'number'
                    ? `$${admin.amount_spent.toFixed(2)}`
                    : '$0.00'}
                </td>
                <td>{admin.next_billing || ''}</td>
                <td>
                  <button
                    type="button"
                    className="superadmin-page-button"
                    onClick={() => navigate(`/admin_login?email=${encodeURIComponent(admin.email || '')}`)}
                  >
                    Admin Login
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>

      </table>

      <h3 className="superadmin-section-title">DTA Direct Clients (Main Site)</h3>
      <div className="superadmin-toolbar">
        <span className="superadmin-page-meta">
          Registered: {dtaDirectSummary.registered_count ?? 0} | Paid Not Registered: {dtaDirectSummary.paid_not_registered_count ?? 0}
        </span>
      </div>

      <h4 className="superadmin-section-title">Registered</h4>
      <table className="superadmin-admins-table">
        <thead>
          <tr>
            <th>Email</th>
            <th>Offer</th>
            <th>Billing</th>
            <th>Questionnaire</th>
            <th>Active</th>
            <th>Signed Up</th>
            <th>Tracking</th>
          </tr>
        </thead>
        <tbody>
          {dtaDirectRegistered.map((client, idx) => (
            <tr key={`dta-reg-${idx}`}>
              <td>{client.email || '—'}</td>
              <td>{client.offer_code || '—'}</td>
              <td>{client.billing_cycle || '—'}</td>
              <td>{client.questionnaire_status || 'not_started'}</td>
              <td>{client.is_active ? 'Yes' : 'No'}</td>
              <td>{client.created_at ? String(client.created_at).slice(0, 10) : '—'}</td>
              <td>
                <button
                  type="button"
                  className="superadmin-page-button"
                  onClick={() => loadDirectClientTracking(client)}
                >
                  View Tracking
                </button>
              </td>
            </tr>
          ))}
          {!dtaDirectRegistered.length && (
            <tr>
              <td colSpan="7">No direct clients registered yet.</td>
            </tr>
          )}
        </tbody>
      </table>

      {(selectedDirectClient || directTrackingLoading || directTrackingError || directTracking) && (
        <>
          <h4 className="superadmin-section-title">
            Client Tracking Detail{selectedDirectClient?.email ? `: ${selectedDirectClient.email}` : ''}
          </h4>
          {directTrackingLoading && <p className="superadmin-library-loading">Loading tracking data…</p>}
          {!!directTrackingError && <p className="superadmin-library-error">{directTrackingError}</p>}
          {!directTrackingLoading && !directTrackingError && directTracking && (
            <>
              <div className="superadmin-toolbar">
                <span className="superadmin-page-meta">
                  Photos: {directTracking?.tracking?.summary?.photo_count ?? 0} | Weights: {directTracking?.tracking?.summary?.weight_count ?? 0}
                </span>
              </div>

              <h4 className="superadmin-section-title">Progress Photos</h4>
              <table className="superadmin-admins-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Uploaded</th>
                    <th>Notes</th>
                    <th>File</th>
                  </tr>
                </thead>
                <tbody>
                  {(directTracking?.tracking?.photos || []).map((photo) => (
                    <tr key={`photo-${photo.id}`}>
                      <td>{photo.captured_for_date || '—'}</td>
                      <td>{formatDateTime(photo.created_at)}</td>
                      <td>{photo.notes || '—'}</td>
                      <td>
                        {photo.file_url ? (
                          <a href={photo.file_url} target="_blank" rel="noreferrer">Open</a>
                        ) : '—'}
                      </td>
                    </tr>
                  ))}
                  {!(directTracking?.tracking?.photos || []).length && (
                    <tr><td colSpan="4">No photos uploaded yet.</td></tr>
                  )}
                </tbody>
              </table>

              <h4 className="superadmin-section-title">Weight Entries</h4>
              <table className="superadmin-admins-table">
                <thead>
                  <tr>
                    <th>Date/Time</th>
                    <th>Weight</th>
                    <th>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {(directTracking?.tracking?.weights || []).map((weight) => (
                    <tr key={`weight-${weight.id}`}>
                      <td>{formatDateTime(weight.measured_at)}</td>
                      <td>{formatWeight(weight.weight_value, weight.unit)}</td>
                      <td>{weight.notes || '—'}</td>
                    </tr>
                  ))}
                  {!(directTracking?.tracking?.weights || []).length && (
                    <tr><td colSpan="3">No weight entries yet.</td></tr>
                  )}
                </tbody>
              </table>
            </>
          )}
        </>
      )}

      <h4 className="superadmin-section-title">Paid But Not Registered</h4>
      <table className="superadmin-admins-table">
        <thead>
          <tr>
            <th>Email</th>
            <th>Offer</th>
            <th>Billing</th>
            <th>Amount</th>
            <th>Link Sent</th>
            <th>Paid At</th>
          </tr>
        </thead>
        <tbody>
          {dtaDirectPending.map((client, idx) => (
            <tr key={`dta-pending-${idx}`}>
              <td>{client.email || '—'}</td>
              <td>{client.offer_code || '—'}</td>
              <td>{client.billing_cycle || '—'}</td>
              <td>{typeof client.amount_cents === 'number' ? `$${(client.amount_cents / 100).toFixed(2)}` : '—'}</td>
              <td>{client.registration_link_printed_at ? 'Yes' : 'No'}</td>
              <td>{client.created_at ? String(client.created_at).slice(0, 10) : '—'}</td>
            </tr>
          ))}
          {!dtaDirectPending.length && (
            <tr>
              <td colSpan="6">No paid direct signups pending registration.</td>
            </tr>
          )}
        </tbody>
      </table>

      <div className="superadmin-pagination">
        <button
          type="button"
          className="superadmin-page-button"
          disabled={!stats?.pagination?.has_previous}
          onClick={() => setPage((prev) => Math.max(prev - 1, 1))}
        >
          Previous
        </button>
        <span className="superadmin-page-meta">
          Page {stats?.pagination?.page || 1} of {stats?.pagination?.total_pages || 1}
        </span>
        <button
          type="button"
          className="superadmin-page-button"
          disabled={!stats?.pagination?.has_next}
          onClick={() => setPage((prev) => prev + 1)}
        >
          Next
        </button>
      </div>

      <button
        onClick={() => {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          navigate('/superadmin_login');
        }}
        className="superadmin-logout-button"
      >
        {t('superadmin_dashboard.logout')}
      </button>
    </div>
  );
}

export default SuperAdminDashboard;
