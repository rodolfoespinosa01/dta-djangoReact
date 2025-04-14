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
import ThankYouRoute from './routes/ThankYouRoute';

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<MainHomePage />} />
          <Route path="/adminhomepage" element={<AdminHomePage />} />
          <Route path="/adminplans" element={<AdminPlanSelectionPage />} />
          <Route path="/adminregister" element={<AdminRegisterPage />} />
          <Route path="/adminlogin" element={<AdminLoginPage />} />
          <Route path="/adminforgotpassword" element={<AdminForgotPasswordPage />} />
          <Route path="/adminthankyou" element={<AdminThankYou />} />
          <Route path="/adminresetpassword" element={<AdminResetPasswordPage />} />
          <Route path="/superadminlogin" element={<SuperAdminLoginPage />} />
          <Route path="/userhomepage" element={<UserHomePage />} />
          <Route path="/userplans" element={<UserPlanSelectionPage />} />

          {/* Protected Admin Routes */}
          <Route
            path="/admindashboard"
            element={
              <AdminProtectedRoute>
                <AdminDashboard />
              </AdminProtectedRoute>
            }
          />
          <Route
            path="/adminsettings"
            element={
              <AdminProtectedRoute>
                <AdminSettings />
              </AdminProtectedRoute>
            }
          />
          <Route
            path="/admintrialended"
            element={
              <AdminProtectedRoute>
                <AdminTrialEnded />
              </AdminProtectedRoute>
            }
          />

          {/* Protected Super Admin Routes */}
          <Route
            path="/superadmindashboard"
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
