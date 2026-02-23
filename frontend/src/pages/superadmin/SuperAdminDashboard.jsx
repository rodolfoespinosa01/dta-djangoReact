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
  const [libraryMode, setLibraryMode] = useState('foods');
  const [libraryQuery, setLibraryQuery] = useState('');
  const [libraryPage, setLibraryPage] = useState(1);
  const [libraryData, setLibraryData] = useState(null);
  const [libraryLoading, setLibraryLoading] = useState(false);
  const [libraryError, setLibraryError] = useState('');

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

  return (
    <div className="superadmin-dashboard-page">
      <h2>{t('superadmin_dashboard.title')}</h2>

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
          <div className="superadmin-library-tabs">
            {[
              { key: 'foods', label: 'Foods' },
              { key: 'combos', label: 'Meal Combos' },
              { key: 'errors', label: 'Error Table' },
            ].map((tab) => (
              <button
                key={tab.key}
                type="button"
                className={`superadmin-library-tab ${libraryMode === tab.key ? 'is-active' : ''}`}
                onClick={() => setLibraryMode(tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </div>
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
              </tr>
            );
          })}
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
