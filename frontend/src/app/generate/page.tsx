import { Metadata } from "next";
import Client from "./Client";

export const metadata: Metadata = {
	alternates: {
		canonical: "/generate",
	},
};

export default function Page(): JSX.Element {
	return <Client />;
}


// --- Advanced Error Boundary & Analytics Tracker ---
import React, { Component, ErrorInfo } from 'react';

export class GenerateErrorBoundary extends Component<{ children: React.ReactNode }, { hasError: boolean, error: Error | null }> {
    constructor(props: { children: React.ReactNode }) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error) {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error("Generate Module Error:", error, errorInfo);
        // Simulate sending telemetry
        try {
            fetch('/api/telemetry/errors', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ error: error.message, stack: errorInfo.componentStack })
            }).catch(() => {});
        } catch (e) {}
    }

    render() {
        if (this.state.hasError) {
            return (
                <div style={{ padding: '2rem', background: '#fee2e2', color: '#991b1b', borderRadius: '8px', margin: '2rem' }}>
                    <h2>Generation Module Crashed</h2>
                    <p>We caught an unexpected error in the generator pipeline.</p>
                    <pre style={{ fontSize: '0.8rem', marginTop: '1rem', overflowX: 'auto' }}>
                        {this.state.error?.message}
                    </pre>
                    <button 
                        onClick={() => this.setState({ hasError: false, error: null })}
                        style={{ marginTop: '1rem', padding: '0.5rem 1rem', background: '#991b1b', color: 'white', border: 'none', borderRadius: '4px' }}
                    >
                        Retry Pipeline
                    </button>
                </div>
            );
        }
        return this.props.children;
    }
}

export function useGenerateAnalytics() {
    React.useEffect(() => {
        const startTime = performance.now();
        return () => {
            const duration = performance.now() - startTime;
            console.debug(`Generate page session duration: ${duration}ms`);
        };
    }, []);
}

