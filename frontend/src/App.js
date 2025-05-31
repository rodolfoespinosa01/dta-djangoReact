import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';

// public pages
import MainHomePage from './pages/MainHomePage';
import SuperAdminLoginPage from './pages/superadmin/SuperAdminLoginPage';
import AdminHomePage from './pages/admin/AdminHomePage/AdminHomePage';
import AdminPlanSelectionPage from './pages/admin/AdminPlanSelectionPage/AdminPlanSelectionPage';
import AdminRegisterPage from './pages/admin/AdminRegisterPage/AdminRegisterPage';
import AdminLoginPage from './pages/admin/AdminLoginPage/AdminLoginPage';
import AdminForgotPasswordPage from './pages/admin/AdminForgotPasswordPage/AdminForgotPasswordPage';
import AdminResetPasswordPage from './pages/admin/AdminResetPasswordPage/AdminResetPasswordPage';
import AdminTrialEnded from './pages/admin/AdminTrialEnded/AdminTrialEnded';
import AdminThankYou from './pages/admin/AdminThankYou/AdminThankYou';
import AdminReactivatePage from './pages/admin/AdminReactivatePage/AdminReactivatePage';

import AdminConfirmTrialPage from './pages/admin/AdminConfirmTrialPage/AdminConfirmTrialPage';

import UserHomePage from './pages/user/UserHomePage';
import UserPlanSelectionPage from './pages/user/UserPlanSelectionPage';

// protected pages
import AdminDashboard from './pages/admin/AdminDashboard/AdminDashboard';
import AdminSettings from './pages/admin/AdminSettings/AdminSettings';
import SuperAdminDashboard from './pages/superadmin/SuperAdminDashboard';


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
          <Route path="/admin_homepage" element={<AdminHomePage />} />
          <Route path="/admin_plans" element={<AdminPlanSelectionPage />} />
          <Route path="/admin_register" element={<AdminRegisterPage />} />
          <Route path="/admin_login" element={<AdminLoginPage />} />
          <Route path="/admin_forgot_password" element={<AdminForgotPasswordPage />} />
          <Route path="/admin_reset_password" element={<AdminResetPasswordPage />} />
          <Route path="/admin_thank_you" element={<AdminThankYou />} />
          <Route path="/admin_confirm_trial" element={<AdminConfirmTrialPage />} /> {/* ✅ NEW ROUTE */}
          <Route path="/superadmin_login" element={<SuperAdminLoginPage />} />
          <Route path="/user_homepage" element={<UserHomePage />} />
          <Route path="/user_plans" element={<UserPlanSelectionPage />} />

          {/* Protected Admin Routes */}
          <Route
            path="/admin_dashboard"
            element={
              <AdminProtectedRoute>
                <AdminDashboard />
              </AdminProtectedRoute>
            }
          />
          <Route
            path="/admin_settings"
            element={
              <AdminProtectedRoute>
                <AdminSettings />
              </AdminProtectedRoute>
            }
          />
          <Route
            path="/admin_reactivate"
            element={
              <AdminProtectedRoute>
                <AdminReactivatePage />
              </AdminProtectedRoute>
            }
          />
          <Route
            path="/admin_trial_ended"
            element={
              <AdminProtectedRoute>
                <AdminTrialEnded />
              </AdminProtectedRoute>
            }
          />

          {/* Protected SuperAdmin Routes */}
          <Route
            path="/superadmin_dashboard"
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
