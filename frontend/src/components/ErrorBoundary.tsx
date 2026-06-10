"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import * as Sentry from "@sentry/nextjs";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    if (process.env.NODE_ENV !== "production") {
      console.error("Uncaught error:", error, errorInfo);
    }
    Sentry.captureException(error, { extra: { errorInfo } });
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex flex-col items-center justify-center p-6 border border-red-500/20 rounded-lg bg-red-500/10 text-center">
          <h2 className="text-xl font-bold text-red-500 mb-2">Something went wrong</h2>
          <p className="text-sm text-[var(--text-secondary)] mb-4">
            An error occurred inside this component.
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: undefined })}
            className="px-4 py-2 bg-[var(--brand-primary)] text-white rounded-md text-sm font-semibold hover:opacity-90 transition-opacity"
          >
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
