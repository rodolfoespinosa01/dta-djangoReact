import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MainHomePage from './pages/MainHomePage';

import AdminHomePage from './pages/admin/AdminHomePage';
import AdminPlanSelectionPage from './pages/admin/AdminPlanSelectionPage';
import AdminRegisterPage from './pages/admin/AdminRegisterPage';

import UserHomePage from './pages/user/UserHomePage';
import UserPlanSelectionPage from './pages/user/UserPlanSelectionPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MainHomePage />} />
        <Route path="/adminhomepage" element={<AdminHomePage />} />
        <Route path="/adminplans" element={<AdminPlanSelectionPage />} />
        <Route path="/adminregister" element={<AdminRegisterPage />} />

        <Route path="/userhomepage" element={<UserHomePage />} />
        <Route path="/userplans" element={<UserPlanSelectionPage />} />
      </Routes>
    </Router>
  );
}

export default App;
