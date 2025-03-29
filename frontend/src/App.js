import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import PlanSelectionPage from './pages/PlanSelectionPage'; // 👈 NEW

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/plans" element={<PlanSelectionPage />} /> {/* 👈 NEW */}
      </Routes>
    </Router>
  );
}

export default App;
