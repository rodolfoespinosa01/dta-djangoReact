import React from 'react';
import { useNavigate } from 'react-router-dom';
import './AdminHomePage.css';

function AdminHomePage() {
  const navigate = useNavigate();

  const handleCTA = () => {
    navigate('/admin_plans');
  };

  const handleHomeCTA = () => {
    navigate('/');
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: '#f3f4f6',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
      }}
    >
      <div
        style={{
          backgroundColor: 'white',
          padding: '3rem',
          borderRadius: '12px',
          maxWidth: '500px',
          width: '100%',
          textAlign: 'center',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
        }}
      >
        <h1 style={{ marginBottom: '1rem', fontSize: '2rem', color: '#111827' }}>Welcome to DTA</h1>
        <p style={{ marginBottom: '2rem', color: '#4b5563', fontSize: '1.1rem' }}>
          Your all-in-one platform for creating personalized diet plans for your clients.
        </p>

        <button
          onClick={handleCTA}
          style={{
            width: '100%',
            padding: '0.75rem',
            fontSize: '1rem',
            backgroundColor: '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 'bold',
            marginBottom: '1rem',
          }}
        >
          🚀 Start Free Trial
        </button>

        <button
          onClick={handleHomeCTA}
          style={{
            width: '100%',
            padding: '0.75rem',
            fontSize: '1rem',
            backgroundColor: '#6b7280',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 'bold',
          }}
        >
          ← Back to Main Page
        </button>
      </div>
    </div>
  );
}

export default AdminHomePage;

// admin home page
// this is the public landing page shown to admins before registration or login.
// it offers two cta buttons: one to start the admin free trial by navigating to /admin_plans, and another to return to the main public homepage (/).
// this page uses react-router's useNavigate hook to programmatically route users based on their selection.