import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import AdminPlanSelectionPage from './pages/AdminPlanSelectionPage'; // 👈 NEW

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/adminplans" element={<AdminPlanSelectionPage />} /> {/* 👈 NEW */}
      </Routes>
    </Router>
  );
}

export default App;
