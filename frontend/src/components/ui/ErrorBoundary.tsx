
// --- Unified Error Boundary Component ---
import React, { Component, ErrorInfo, ReactNode } from 'react';

export interface ErrorBoundaryProps {
  children: ReactNode;
  /** Custom fallback UI to display when an error occurs */
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode);
  /** Callback fired when an error is caught (useful for telemetry/logging) */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** Callback fired when the boundary is reset */
  onReset?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * A highly robust Error Boundary component for React 18+.
 * Catches JavaScript errors anywhere in the child component tree,
 * logs those errors, and displays a fallback UI instead of crashing the whole app.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // You can also log the error to an error reporting service like Sentry or Datadog here
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  resetBoundary = () => {
    if (this.props.onReset) {
      this.props.onReset();
    }
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError && this.state.error) {
      // If a custom fallback render prop is provided, use it
      if (typeof this.props.fallback === 'function') {
        return this.props.fallback(this.state.error, this.resetBoundary);
      }
      
      // If a custom static fallback node is provided, use it
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default gracefully styled fallback UI
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '40px 20px',
          textAlign: 'center',
          backgroundColor: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '8px',
          margin: '20px 0',
          color: '#991b1b'
        }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '12px' }}>
            Something went wrong.
          </h2>
          <p style={{ marginBottom: '24px', color: '#b91c1c' }}>
            We&apos;ve encountered an unexpected error. Our team has been notified.
          </p>
          <div style={{
            backgroundColor: '#fee2e2',
            padding: '12px',
            borderRadius: '4px',
            fontFamily: 'monospace',
            fontSize: '0.875rem',
            textAlign: 'left',
            maxWidth: '100%',
            overflowX: 'auto',
            marginBottom: '24px'
          }}>
            {this.state.error.toString()}
          </div>
          <button
            onClick={this.resetBoundary}
            style={{
              padding: '10px 20px',
              backgroundColor: '#ef4444',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'background-color 0.2s'
            }}
            onMouseOver={(e) => (e.currentTarget.style.backgroundColor = '#dc2626')}
            onMouseOut={(e) => (e.currentTarget.style.backgroundColor = '#ef4444')}
          >
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Higher Order Component (HOC) wrapper for ErrorBoundary
 */
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>
) {
  return function WithErrorBoundary(props: P) {
    return (
      <ErrorBoundary {...errorBoundaryProps}>
        <Component {...props} />
      </ErrorBoundary>
    );
  };
}
