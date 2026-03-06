import React from 'react';
import { normalizeTheme } from '../../theme/themeConfig';
import './ThemePreferenceToggle.css';

function ThemePreferenceToggle({
  theme,
  onToggle,
  disabled = false,
  title = 'Theme Color',
  darkLabel = 'Dark',
  lightLabel = 'Light',
  ariaLabel = 'Toggle theme',
  className = '',
}) {
  const normalizedTheme = normalizeTheme(theme);

  return (
    <div className={`theme-pref-row ${className}`.trim()}>
      <div>
        <p className="theme-pref-title">{title}</p>
        <p className="theme-pref-subtitle">
          {normalizedTheme === 'dark' ? darkLabel : lightLabel}
        </p>
      </div>
      <button
        type="button"
        className={`theme-toggle ${normalizedTheme === 'dark' ? 'is-dark' : 'is-light'}`}
        aria-label={ariaLabel}
        onClick={onToggle}
        disabled={disabled}
      >
        <span className="theme-toggle-knob" />
      </button>
    </div>
  );
}

export default ThemePreferenceToggle;
