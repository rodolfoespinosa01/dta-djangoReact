import React, { useEffect, useState } from 'react';
import { jwtDecode } from 'jwt-decode';
import { useNavigate } from 'react-router-dom';



function AdminDashboard() {
  const [userId, setUserId] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    
    if (!token) {
      // If no token, redirect to login
      navigate('/adminlogin');
      return;
    }

    try {
      const decoded = jwtDecode(token);
      const isExpired = decoded.exp * 1000 < Date.now();

      if (isExpired) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        navigate('/adminlogin');
      } else {
        setUserId(decoded.user_id);
      }

    } catch (err) {
      console.error('Invalid token:', err);
      navigate('/adminlogin');
    }
  }, [navigate]);

  return (
    <div style={{ padding: '2rem', textAlign: 'center' }}>
      <h1>Welcome to your dashboard</h1>
      <p>Your all-in-one platform for creating personalized diet plans for your clients.</p>
      {userId && <p style={{ marginTop: '1rem', fontStyle: 'italic' }}>Logged in as user #{userId}</p>}
    </div>
  );
}

export default AdminDashboard;
