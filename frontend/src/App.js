import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import AdminHomePage from './pages/AdminHomePage';
import AdminPlanSelectionPage from './pages/AdminPlanSelectionPage'; // 👈 NEW

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<AdminHomePage />} />
        <Route path="/adminplans" element={<AdminPlanSelectionPage />} />
      </Routes>
    </Router>
  );
}

export default App;
