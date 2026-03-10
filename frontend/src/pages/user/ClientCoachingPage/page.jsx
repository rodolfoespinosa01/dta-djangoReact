import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import { apiRequest } from '../../../api/client';
import '../../../styles/shared/client-app-shell.css';
import './css.css';
import MessagingPortal from '../../../components/MessagingPortal';

function ClientCoachingPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [includesCoaching, setIncludesCoaching] = useState(false);
  const [adminUserId, setAdminUserId] = useState(null);

  const goToDashboard = () => navigate('/client_dashboard');
  const handleLogout = () => logout('/client_login');

  const actions = (
    <div className="client-coaching-actions">
      <button type="button" className="client-coaching-btn" onClick={goToDashboard}>
        ← Back to Dashboard
      </button>
      <button type="button" className="client-coaching-btn danger" onClick={handleLogout}>
        Log out
      </button>
    </div>
  );

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
        setAdminUserId(res.data?.client?.associated_admin_user_id || null);
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

  if (loading) return <div className="client-coaching-page">{actions}<p>Loading…</p></div>;
  if (error) return <div className="client-coaching-page">{actions}<p className="client-dash-error">{error}</p></div>;
  if (!includesCoaching) return <div className="client-coaching-page">{actions}<p>You do not have access to coaching messaging.</p></div>;
  if (!adminUserId) return <div className="client-coaching-page">{actions}<p>No coach is assigned to your account.</p></div>;

  return (
    <div className="client-coaching-page" style={{ padding: 32 }}>
      {actions}
      <h1>Coaching Messaging</h1>
      <MessagingPortal adminUserId={adminUserId} />
    </div>
  );
}

export default ClientCoachingPage;
