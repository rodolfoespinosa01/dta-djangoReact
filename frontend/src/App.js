import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';

// Public Pages
import MainHomePage from './pages/MainHomePage';
import SuperAdminLoginPage from './pages/superadmin/SuperAdminLoginPage';
import AdminHomePage from './pages/admin/AdminHomePage';
import AdminPlanSelectionPage from './pages/admin/AdminPlanSelectionPage';
import AdminRegisterPage from './pages/admin/AdminRegisterPage';
import AdminLoginPage from './pages/admin/AdminLoginPage';
import AdminForgotPasswordPage from './pages/admin/AdminForgotPasswordPage';
import AdminResetPasswordPage from './pages/admin/AdminResetPasswordPage';
import AdminTrialEnded from './pages/admin/AdminTrialEnded';

import UserHomePage from './pages/user/UserHomePage';
import UserPlanSelectionPage from './pages/user/UserPlanSelectionPage';

// Protected Pages
import AdminDashboard from './pages/admin/AdminDashboard';
import AdminSettings from './pages/admin/AdminSettings';
import SuperAdminDashboard from './pages/superadmin/SuperAdminDashboard';
import AdminThankYou from './pages/admin/AdminThankYou';

// Route Guards
import AdminProtectedRoute from './routes/AdminProtectedRoute';
import SuperAdminProtectedRoute from './routes/SuperAdminProtectedRoute';

function App() {
  return (
    <Router>
      <AuthProvider>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<MainHomePage />} />
        <Route path="/admin-homepage" element={<AdminHomePage />} />
        <Route path="/admin-plans" element={<AdminPlanSelectionPage />} />
        <Route path="/admin-register" element={<AdminRegisterPage />} />
        <Route path="/admin-login" element={<AdminLoginPage />} />
        <Route path="/admin-forgot-password" element={<AdminForgotPasswordPage />} />
        <Route path="/admin-thank-you" element={<AdminThankYou />} />
        <Route path="/admin-reset-password" element={<AdminResetPasswordPage />} />
        <Route path="/superadmin-login" element={<SuperAdminLoginPage />} />
        <Route path="/user-homepage" element={<UserHomePage />} />
        <Route path="/user-plans" element={<UserPlanSelectionPage />} />

        {/* Protected Admin Routes */}
        <Route
          path="/admin-dashboard"
          element={
            <AdminProtectedRoute>
              <AdminDashboard />
            </AdminProtectedRoute>
          }
        />
        <Route
          path="/admin-settings"
          element={
            <AdminProtectedRoute>
              <AdminSettings />
            </AdminProtectedRoute>
          }
        />
        <Route
          path="/admin-trial-ended"
          element={
            <AdminProtectedRoute>
              <AdminTrialEnded />
            </AdminProtectedRoute>
          }
        />

        {/* Protected Super Admin Routes */}
        <Route
          path="/superadmin-dashboard"
          element={
            <SuperAdminProtectedRoute>
              <SuperAdminDashboard />
            </SuperAdminProtectedRoute>
          }
        />
      </Routes>

      </AuthProvider>
    </Router>
  );
}

export default App;
