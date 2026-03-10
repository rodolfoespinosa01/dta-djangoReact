import React from 'react';
import AdminMessagingPage from './pages/admin/AdminMessagingPage';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { LanguageProvider } from './context/LanguageContext';
import { ThemeProvider, useTheme } from './context/ThemeContext';
import './App.css';

// component
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import LanguageToggle from './components/language/LanguageToggle';
import AppErrorBoundary from './components/AppErrorBoundary';
import { getAdminSlugFromHostname } from './utils/branding';

// public pages
import MainWelcomeScreen from './pages/MainWelcomeScreen/MainWelcomeScreen';
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

import UserHomePage from './pages/user/UserHomePage/page';
// ...existing code...
import UserPlanSelectionPage from './pages/user/UserPlanSelectionPage/page';
import ClientRegisterPage from './pages/user/ClientRegisterPage/page';
import ClientSignupSuccessPage from './pages/user/ClientSignupSuccessPage/page';
import ClientLoginPage from './pages/user/ClientLoginPage/page';
import ClientDashboardPage from './pages/user/ClientDashboardPage/page';
import ClientMacroCalculatorPage from './pages/user/ClientMacroCalculatorPage/page';
import ClientSettingsPage from './pages/user/ClientSettingsPage/page';
import ClientFoodPreferencesPage from './pages/user/ClientFoodPreferencesPage/page';
import ClientMealPlanGenerationPage from './pages/user/ClientMealPlanGenerationPage/page';
import ClientExportsPage from './pages/user/ClientExportsPage/page';
import ClientTrackingPage from './pages/user/ClientTrackingPage/page';
import ClientCoachingPage from './pages/user/ClientCoachingPage/page';

// protected pages
import AdminDashboard from './pages/admin/AdminDashboard/AdminDashboard';
import AdminSettings from './pages/admin/AdminSettings/AdminSettings';
import AdminParameterSettingsPage from './pages/admin/AdminParameterSettings/AdminParameterSettingsPage';
import SuperAdminDashboard from './pages/superadmin/SuperAdminDashboard';
import SuperAdminAnalyticsPage from './pages/superadmin/SuperAdminAnalyticsPage';


// Route Guards
import AdminProtectedRoute from './routes/AdminProtectedRoute';
import SuperAdminProtectedRoute from './routes/SuperAdminProtectedRoute';
import ClientProtectedRoute from './routes/ClientProtectedRoute';

function AppLayout() {
  const location = useLocation();
  const { getTheme } = useTheme();
  const hostAdminSlug = getAdminSlugFromHostname();
  const isAdminRoute = location.pathname.startsWith('/admin');
  const isClientRoute = location.pathname.startsWith('/client');
  const adminTheme = getTheme('admin');
  const clientTheme = getTheme('client');
  const showNavbar =
    isAdminRoute ||
    location.pathname.startsWith('/superadmin');
  const shellThemeClass = isAdminRoute
    ? `admin-theme-${adminTheme}`
    : isClientRoute
      ? `client-theme-${clientTheme}`
      : '';
  const activeTheme = isAdminRoute ? adminTheme : isClientRoute ? clientTheme : null;

  return (
    <div className={`app-shell ${shellThemeClass}`}>
      <LanguageToggle />
      {showNavbar && <Navbar adminTheme={isAdminRoute ? adminTheme : null} />}
      <main className="app-content">
        <Routes>
          <Route
            path="/admin_messaging"
            element={
              <AdminProtectedRoute>
                <AdminMessagingPage />
              </AdminProtectedRoute>
            }
          />
          {/* Public Routes */}
          <Route path="/" element={<Navigate to={hostAdminSlug ? `/start/${hostAdminSlug}` : '/welcome'} replace />} />
          <Route path="/welcome" element={<MainWelcomeScreen />} />
          <Route path="/admin_homepage" element={<AdminHomePage />} />
          <Route path="/admin_plans" element={<AdminPlanSelectionPage />} />
          <Route path="/admin_register" element={<AdminRegisterPage />} />
          <Route path="/admin_login" element={<AdminLoginPage />} />
          <Route path="/admin_forgot_password" element={<AdminForgotPasswordPage />} />
          <Route path="/admin_reset_password" element={<AdminResetPasswordPage />} />
          <Route path="/admin_thank_you" element={<AdminThankYou />} />
          <Route path="/admin_confirm_trial" element={<AdminConfirmTrialPage />} />
          <Route path="/superadmin_login" element={<SuperAdminLoginPage />} />
          <Route path="/user_homepage" element={<UserHomePage />} />
          <Route path="/user_plans" element={<UserPlanSelectionPage />} />
          <Route path="/client_register" element={<ClientRegisterPage />} />
          <Route path="/client_signup_success" element={<ClientSignupSuccessPage />} />
          <Route path="/client_login" element={<Navigate to="/user_login" replace />} />
          <Route path="/user_login" element={<ClientLoginPage />} />
          <Route path="/macro_calculator" element={<ClientMacroCalculatorPage />} />
          <Route path="/start/:adminSlug" element={<UserPlanSelectionPage />} />
          <Route path="/start/:adminSlug/plans" element={<UserPlanSelectionPage />} />
          <Route path="/start/:adminSlug/login" element={<ClientLoginPage />} />
          <Route
            path="/client_dashboard"
            element={
              <ClientProtectedRoute>
                <ClientDashboardPage />
              </ClientProtectedRoute>
            }
          />
          <Route
            path="/client_settings"
            element={
              <ClientProtectedRoute>
                <ClientSettingsPage />
              </ClientProtectedRoute>
            }
          />
          <Route
            path="/client_food_preferences"
            element={
              <ClientProtectedRoute>
                <ClientFoodPreferencesPage />
              </ClientProtectedRoute>
            }
          />
          <Route
            path="/client_meal_generation"
            element={
              <ClientProtectedRoute>
                <ClientMealPlanGenerationPage />
              </ClientProtectedRoute>
            }
          />
          <Route
            path="/client_exports"
            element={
              <ClientProtectedRoute>
                <ClientExportsPage />
              </ClientProtectedRoute>
            }
          />
          <Route
            path="/client_tracking"
            element={
              <ClientProtectedRoute>
                <ClientTrackingPage />
              </ClientProtectedRoute>
            }
          />
          <Route
            path="/client_coaching"
            element={
              <ClientProtectedRoute>
                <ClientCoachingPage />
              </ClientProtectedRoute>
            }
          />

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
            path="/admin_parameter_settings"
            element={
              <AdminProtectedRoute>
                <AdminParameterSettingsPage />
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
          <Route
            path="/superadmin_analytics"
            element={
              <SuperAdminProtectedRoute>
                <SuperAdminAnalyticsPage />
              </SuperAdminProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/welcome" replace />} />
        </Routes>
      </main>
      <Footer theme={activeTheme} adminTheme={isAdminRoute ? adminTheme : null} />
    </div>
  );
}

function App() {
  return (
    <Router>
      <LanguageProvider>
        <AuthProvider>
          <ThemeProvider>
            <AppErrorBoundary>
              <AppLayout />
            </AppErrorBoundary>
          </ThemeProvider>
        </AuthProvider>
      </LanguageProvider>
    </Router>
  );
}

export default App;
