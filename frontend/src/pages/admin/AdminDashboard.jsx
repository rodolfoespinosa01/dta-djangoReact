import React, { useEffect, useState } from 'react';
import { jwtDecode } from 'jwt-decode';
import { useNavigate } from 'react-router-dom';

function AdminDashboard() {
  const [userData, setUserData] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('access_token');

    if (!token) {
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
        return;
      }

      // Token is valid → Fetch user info
      fetch('http://localhost:8000/api/users/admindashboard/', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
        .then((res) => res.json())
        .then((data) => {
          setUserData(data);
        })
        .catch((err) => {
          console.error('Failed to fetch dashboard data:', err);
          navigate('/adminlogin');
        });

    } catch (err) {
      console.error('Token decode error:', err);
      navigate('/adminlogin');
    }
  }, [navigate]);

  if (!userData) {
    return <p style={{ padding: '2rem' }}>Loading your dashboard...</p>;
  }
  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    navigate('/adminlogin');
  };
  
  return (
    <div style={{ padding: '2rem', textAlign: 'center' }}>
      <h1>Welcome to your dashboard</h1>
      <p>Your all-in-one platform for creating personalized diet plans for your clients.</p>

      <div style={{ marginTop: '2rem' }}>
        <p><strong>Email:</strong> {userData.message.replace('Welcome, ', '')}</p>
        <p><strong>Role:</strong> {userData.role}</p>
        <p><strong>Subscription Status:</strong> {userData.subscription_status}</p>
      </div>
      <button
  onClick={handleLogout}
  style={{
    marginTop: '2rem',
    padding: '0.75rem 1.5rem',
    backgroundColor: '#dc2626',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer'
  }}
>
  Logout
</button>

    </div>
  );
}

export default AdminDashboard;
