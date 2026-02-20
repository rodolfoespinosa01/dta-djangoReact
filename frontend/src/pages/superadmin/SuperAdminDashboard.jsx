import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useLanguage } from '../../context/LanguageContext';
import './SuperAdminDashboard.css';

function SuperAdminDashboard() {
  const { user, isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (loading) return;

    if (!isAuthenticated || !user?.is_superuser) {
      navigate('/superadmin_login');
      return;
    }

    const token = localStorage.getItem('access_token');
    if (!token) {
      navigate('/superadmin_login');
      return;
    }

    fetch('http://localhost:8000/api/users/superadmin/dashboard/', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then(res => res.json())
      .then(data => setStats(data))
      .catch(err => {
        console.error('Failed to fetch dashboard data:', err);
        navigate('/superadmin_login');
      });
  }, [loading, isAuthenticated, user, navigate]);

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
