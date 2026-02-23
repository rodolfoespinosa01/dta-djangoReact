import React, { useEffect, useRef, useState } from 'react';

const GOOGLE_SCRIPT_SRC = 'https://accounts.google.com/gsi/client';
const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID || '';

let scriptPromise;
function loadGoogleScript() {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (!scriptPromise) {
    scriptPromise = new Promise((resolve, reject) => {
      const existing = document.querySelector(`script[src="${GOOGLE_SCRIPT_SRC}"]`);
      if (existing) {
        existing.addEventListener('load', () => resolve(), { once: true });
        existing.addEventListener('error', reject, { once: true });
        return;
      }
      const script = document.createElement('script');
      script.src = GOOGLE_SCRIPT_SRC;
      script.async = true;
      script.defer = true;
      script.onload = () => resolve();
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }
  return scriptPromise;
}

function GoogleSignInButton({ onCredential, disabled = false, label = 'Continue with Google' }) {
  const btnRef = useRef(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let mounted = true;
    const render = async () => {
      if (!GOOGLE_CLIENT_ID || !btnRef.current) return;
      try {
        await loadGoogleScript();
        if (!mounted || !window.google?.accounts?.id) return;
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: (response) => {
            if (!mounted) return;
            if (!response?.credential) {
              setError('Google sign-in did not return a credential.');
              return;
            }
            setError('');
            onCredential?.(response.credential);
          },
          auto_select: false,
          cancel_on_tap_outside: true,
        });
        btnRef.current.innerHTML = '';
        window.google.accounts.id.renderButton(btnRef.current, {
          theme: 'outline',
          size: 'large',
          shape: 'pill',
          text: 'continue_with',
          width: 320,
        });
      } catch (err) {
        console.error('Google script load failed:', err);
        if (mounted) setError('Unable to load Google Sign-In.');
      }
    };
    render();
    return () => { mounted = false; };
  }, [onCredential]);

  if (!GOOGLE_CLIENT_ID) {
    return null;
  }

  return (
    <div className="google-auth-block" aria-disabled={disabled}>
      <div style={{ opacity: disabled ? 0.6 : 1, pointerEvents: disabled ? 'none' : 'auto' }}>
        <div ref={btnRef} />
      </div>
      {!btnRef.current && (
        <button type="button" disabled className="client-auth-google-fallback">
          {label}
        </button>
      )}
      {error ? <p className="client-auth-error">{error}</p> : null}
    </div>
  );
}

export default GoogleSignInButton;

