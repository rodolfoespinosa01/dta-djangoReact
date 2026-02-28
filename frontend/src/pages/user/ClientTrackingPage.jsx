import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import './ClientDashboardPage.css';

function ClientTrackingPage() {
  const { logout } = useAuth();

  return (
    <div className="client-dashboard-page">
      <header className="client-dashboard-header">
        <div>
          <h1>Tracking</h1>
          <p className="client-dash-muted">
            This is the tracking landing page. We will expand this section with progress tracking workflows.
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
        <h2>Coming Next</h2>
        <ul>
          <li>Weekly check-ins</li>
          <li>Weight and measurement tracking</li>
          <li>Progress notes and trends</li>
          <li>Coach-to-client tracking workflows</li>
        </ul>
      </section>
    </div>
  );
}

export default ClientTrackingPage;
