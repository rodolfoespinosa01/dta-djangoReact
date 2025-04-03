import React from 'react';
import { useNavigate } from 'react-router-dom';

const adminPlans = [
  {
    id: 'adminTrial',
    name: 'Free Admin Trial',
    price: 'Free for 14 days',
    description: 'Start with up to 10 end users. No charge until trial ends.',
  },
  {
    id: 'adminMonthly',
    name: 'Monthly Admin Plan',
    price: '$29 / month',
    description: 'Unlimited users. Billed monthly.',
  },
  {
    id: 'adminAnnual',
    name: 'Annual Admin Plan',
    price: '$299 / year',
    description: 'Unlimited users. Save 14% compared to monthly.',
  },
];



function AdminPlanSelectionPage() {
  const navigate = useNavigate();

  const handleHomeCTA = () => {
    navigate('/');
  };
  const handleSelectAdminPlan = async (adminPlanId) => {
    try {
      const response = await fetch('http://localhost:8000/api/create-checkout-session/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ plan_name: adminPlanId }),
      });
  
      const data = await response.json();
  
      if (data.url) {
        window.location.href = data.url;
      } else {
        console.error('Checkout session error:', data.error);
      }
    } catch (error) {
      console.error('Error creating checkout session:', error);
    }
  };
  

  return (
    <div style={{ padding: '2rem', textAlign: 'center' }}>
      <h2>Select a Plan</h2>
      <div style={{ display: 'flex', justifyContent: 'center', gap: '2rem', marginTop: '2rem' }}>
        {adminPlans.map((adminPlan) => (
          <div
            key={adminPlan.id}
            style={{
              border: '1px solid #ccc',
              borderRadius: '8px',
              padding: '1.5rem',
              width: '250px',
              textAlign: 'left',
            }}
          >
            <h3>{adminPlan.name}</h3>
            <p><strong>{adminPlan.price}</strong></p>
            <p>{adminPlan.description}</p>
            <button
              onClick={() => handleSelectAdminPlan(adminPlan.id)}
              style={{ marginTop: '1rem', width: '100%' }}
            >
              Continue to Checkout
            </button>
          </div>
        ))}
      </div>

      <button onClick={handleHomeCTA} style={{ marginTop: '1rem', padding: '1rem 2rem', fontSize: '1rem' }}>
        Back to Main Page
      </button>
    </div>
  );
}

export default AdminPlanSelectionPage;
