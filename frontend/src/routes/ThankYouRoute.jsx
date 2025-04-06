import React from 'react';
import { Navigate } from 'react-router-dom';

function ThankYouRoute({ children, role = 'admin' }) {
  const flag = localStorage.getItem(`${role}_recent_stripe_session`);
  if (!flag) {
    return <Navigate to={`/${role}login`} />;
  }

  return children;
}

export default ThankYouRoute;
