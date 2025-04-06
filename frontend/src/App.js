import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';

import MainHomePage from './pages/MainHomePage';

import SuperAdminDashboard from './pages/superadmin/SuperAdminDashboard';
import SuperAdminLoginPage from './pages/superadmin/SuperAdminLoginPage';

import AdminHomePage from './pages/admin/AdminHomePage';
import AdminThankYou from './pages/admin/AdminThankYou';
import AdminPlanSelectionPage from './pages/admin/AdminPlanSelectionPage';
import AdminRegisterPage from './pages/admin/AdminRegisterPage';
import AdminDashboard from './pages/admin/AdminDashboard';
import AdminSettings from './pages/admin/AdminSettings';
import AdminLoginPage from './pages/admin/AdminLoginPage';
import AdminForgotPasswordPage from './pages/admin/AdminForgotPasswordPage';
import AdminResetPasswordPage from './pages/admin/AdminResetPasswordPage';

import UserHomePage from './pages/user/UserHomePage';
import UserPlanSelectionPage from './pages/user/UserPlanSelectionPage';

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<MainHomePage />} />

          <Route path="/superadmindashboard" element={<SuperAdminDashboard />} />
          <Route path="/superadminlogin" element={<SuperAdminLoginPage />} />

          <Route path="/adminthankyou" element={<AdminThankYou />} />
          <Route path="/adminlogin" element={<AdminLoginPage />} />
          <Route path="/adminhomepage" element={<AdminHomePage />} />
          <Route path="/adminplans" element={<AdminPlanSelectionPage />} />
          <Route path="/adminregister" element={<AdminRegisterPage />} />
          <Route path="/adminforgotpassword" element={<AdminForgotPasswordPage />} />
          <Route path="/adminresetpassword" element={<AdminResetPasswordPage />} />

          <Route path="/userhomepage" element={<UserHomePage />} />
          <Route path="/userplans" element={<UserPlanSelectionPage />} />

          {/* Protected Admin Routes */}
          <Route path="/admindashboard" element={<AdminDashboard />} />
          <Route path="/adminsettings" element={<AdminSettings />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}

export default App;
