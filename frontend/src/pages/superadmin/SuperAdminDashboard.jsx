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

  if (loading || !stats) {
    return <p className="superadmin-loading">{t('superadmin_dashboard.loading')}</p>;
  }

  return (
    <div className="superadmin-dashboard-page">
      <h2>{t('superadmin_dashboard.title')}</h2>

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
