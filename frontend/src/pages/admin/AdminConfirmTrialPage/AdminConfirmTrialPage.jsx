import React, { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useLanguage } from '../../../context/LanguageContext';
import './AdminConfirmTrialPage.css';

function AdminConfirmTrialPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { t } = useLanguage();

  useEffect(() => {
    const subscriptionId = searchParams.get('subscription_id');
    const customerId = searchParams.get('customer_id');

    // 👉 You can later POST this to the backend if needed
    console.log('🎯 Trial confirmed:', subscriptionId, customerId);

    // Simulate delay and redirect to actual signup
    const timeout = setTimeout(() => {
      navigate('/adminregister'); // Or whatever page comes next
    }, 2000);

    return () => clearTimeout(timeout);
  }, [searchParams, navigate]);

  return (
    <div className="admin-confirm-wrapper">
      <h2>✅ {t('admin_confirm.title')}</h2>
      <p>{t('admin_confirm.subtitle')}</p>
    </div>
  );
}

export default AdminConfirmTrialPage;
