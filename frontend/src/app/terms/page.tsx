import React from 'react';

export default function TermsPage() {
  return (
    <div className="container py-20 min-h-screen max-w-4xl">
      <h1 className="text-4xl font-black mb-10 text-[var(--text-primary)]">Terms of Service</h1>
      
      <div className="prose prose-invert prose-lg text-[var(--text-secondary)]">
        <p>Effective Date: January 1, 2026</p>
        
        <h2 className="text-2xl font-bold text-[var(--text-primary)] mt-10 mb-4">1. Acceptance of Terms</h2>
        <p>By downloading, installing, or using the EnvForage Agent, backend APIs, or Web Interface, you agree to these terms.</p>
        
        <h2 className="text-2xl font-bold text-[var(--text-primary)] mt-10 mb-4">2. Open Source Licenses</h2>
        <p>The EnvForage CLI and Frontend are provided under the MIT License. The compatibility matrix database is proprietary and subject to access limits.</p>
        
        <h2 className="text-2xl font-bold text-[var(--text-primary)] mt-10 mb-4">3. AI Troubleshooting Liability</h2>
        <p>EnvForage uses Large Language Models to suggest terminal commands for repairing environments. <strong>You are responsible for reviewing commands before executing them.</strong> EnvForage is not liable for data loss or system corruption caused by executing AI-generated repair scripts.</p>
        
        <h2 className="text-2xl font-bold text-[var(--text-primary)] mt-10 mb-4">4. API Rate Limiting</h2>
        <p>Free tier users are limited to 100 API resolutions per day. Enterprise users must provide a valid API key.</p>
      </div>
    </div>
  );
}
