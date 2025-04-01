import React from 'react';

const adminPlans = [
  {
    id: 'trial',
    name: 'Free Trial',
    price: 'Free for 14 days',
    description: 'Start with up to 10 end users. No charge until trial ends.',
  },
  {
    id: 'monthly',
    name: 'Monthly Plan',
    price: '$29 / month',
    description: 'Unlimited users. Billed monthly.',
  },
  {
    id: 'annual',
    name: 'Annual Plan',
    price: '$299 / year',
    description: 'Unlimited users. Save 14% compared to monthly.',
  },
];

function AdminPlanSelectionPage() {
  const handleSelectAdminPlan = (adminPlanId) => {
    console.log(`Selected plan: ${adminPlanId}`);
    // Later we’ll redirect to checkout here
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
    </div>
  );
}

export default AdminPlanSelectionPage;
