import React from 'react';

export default function DevcontainerHubPage() {
  return (
    <div className="container py-20 min-h-screen">
      <h1 className="text-4xl font-black mb-6 text-[var(--text-primary)]">Devcontainer Hub</h1>
      <p className="text-xl text-[var(--text-secondary)] mb-12 max-w-2xl">
        VS Code and GitHub Codespaces ready environments. Start coding in 10 seconds.
      </p>
      
      <div className="bg-[var(--bg-tertiary)] border border-[var(--border-subtle)] p-8 rounded-xl">
        <h2 className="text-2xl font-bold mb-4">Initialize a Workspace</h2>
        <p className="mb-6 text-[var(--text-secondary)]">Run this command in your project root to generate a `.devcontainer` directory customized for your hardware.</p>
        
        <div className="bg-[var(--bg-core)] p-4 rounded-md font-mono text-lg border border-[var(--border-strong)] flex justify-between">
          <span className="text-[var(--text-primary)]">envforge init --template=devcontainer</span>
          <span className="text-[var(--brand-secondary)] cursor-pointer">Copy</span>
        </div>
        
        <div className="mt-8 text-sm text-[var(--text-muted)]">
          Includes extensions for Python, Jupyter, and EnvForage Diagnostics by default.
        </div>
      </div>
    </div>
  );
}
