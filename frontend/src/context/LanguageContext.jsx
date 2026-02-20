import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';
import translations from '../i18n/translations';

const STORAGE_KEY = 'app_language';
const LanguageContext = createContext(null);

function resolveInitialLanguage() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'en' || stored === 'es') return stored;
  return 'en';
}

function formatTemplate(template, params = {}) {
  if (typeof template !== 'string') return template;
  return template.replace(/\{(\w+)\}/g, (_, key) => (params[key] ?? `{${key}}`));
}

export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(resolveInitialLanguage);

  const setLanguage = useCallback((nextLanguage) => {
    if (nextLanguage !== 'en' && nextLanguage !== 'es') return;
    setLanguageState(nextLanguage);
    localStorage.setItem(STORAGE_KEY, nextLanguage);
  }, []);

  const t = useCallback((key, params) => {
    const localized = translations[language]?.[key];
    const fallback = translations.en?.[key];
    const value = localized ?? fallback ?? key;
    return formatTemplate(value, params);
  }, [language]);

  const value = useMemo(
    () => ({ language, setLanguage, t }),
    [language, setLanguage, t]
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within LanguageProvider');
  }
  return context;
}
