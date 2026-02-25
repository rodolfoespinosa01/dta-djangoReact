import React from 'react';

class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      errorMessage: error?.message || 'Unexpected UI error.',
    };
  }

  componentDidCatch(error, info) {
    console.error('[AppErrorBoundary] Uncaught error:', error, info);
  }

  handleReload = () => {
    if (typeof window !== 'undefined') window.location.reload();
  };

  handleGoHome = () => {
    this.setState({ hasError: false, errorMessage: '' });
    if (typeof window !== 'undefined') {
      window.location.assign('/welcome');
    }
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div style={{ minHeight: '60vh', display: 'grid', placeItems: 'center', padding: '1rem' }}>
        <div style={{ maxWidth: 640, width: '100%', border: '1px solid rgba(20,40,74,0.12)', borderRadius: 12, padding: '1rem', background: '#fff' }}>
          <h2 style={{ marginTop: 0 }}>This page hit an unexpected error</h2>
          <p style={{ color: '#5b6778' }}>
            A bad bookmark or stale page state can cause this. You can reload or return to the home page.
          </p>
          <p style={{ fontFamily: 'monospace', fontSize: '0.9rem', wordBreak: 'break-word', color: '#5b6778' }}>
            {this.state.errorMessage}
          </p>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button type="button" onClick={this.handleReload}>Reload</button>
            <button type="button" onClick={this.handleGoHome}>Go to Home</button>
          </div>
        </div>
      </div>
    );
  }
}

export default AppErrorBoundary;

