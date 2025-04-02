import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MainHomePage from './pages/MainHomePage';
import AdminHomePage from './pages/admin/AdminHomePage';
import UserHomePage from './pages/user/UserHomePage';
import AdminPlanSelectionPage from './pages/admin/AdminPlanSelectionPage';
import UserPlanSelectionPage from './pages/user/UserPlanSelectionPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MainHomePage />} />
        <Route path="/adminhomepage" element={<AdminHomePage />} />
        <Route path="/userhomepage" element={<UserHomePage />} />
        <Route path="/adminplans" element={<AdminPlanSelectionPage />} />
        <Route path="/userplans" element={<UserPlanSelectionPage />} />
      </Routes>
    </Router>
  );
}

export default App;
