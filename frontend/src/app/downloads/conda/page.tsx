import React from 'react';

export default function CondaHubPage() {
  return (
    <div className="container py-20 min-h-screen">
      <h1 className="text-4xl font-black mb-6 text-[var(--text-primary)]">Conda Environments</h1>
      <p className="text-xl text-[var(--text-secondary)] mb-12 max-w-2xl">
        Generate conflict-free `environment.yml` files solved by our backend matrix engine.
      </p>
      
      <div className="bg-[var(--bg-tertiary)] border border-[var(--border-subtle)] p-8 rounded-xl">
        <h2 className="text-2xl font-bold mb-4">Export Validated Env</h2>
        <p className="mb-6 text-[var(--text-secondary)]">Create a Conda environment that perfectly matches your current OS and GPU architecture.</p>
        
        <div className="bg-[var(--bg-core)] p-4 rounded-md font-mono text-lg border border-[var(--border-strong)]">
          <div className="text-[var(--text-secondary)]"># 1. Analyze system</div>
          <div className="text-[var(--text-primary)] mb-2">envforge audit --export=conda</div>
          <div className="text-[var(--text-secondary)]"># 2. Create environment</div>
          <div className="text-[var(--text-primary)]">conda env create -f environment.yml</div>
        </div>
      </div>
    </div>
  );
}
