import React from 'react';

export default function PyPIDownloadsPage() {
  return (
    <div className="container py-20 min-h-screen">
      <h1 className="text-4xl font-black mb-6 text-[var(--text-primary)]">PyPI Package Hub</h1>
      <p className="text-xl text-[var(--text-secondary)] mb-12 max-w-2xl">
        Download the core EnvForage agent directly via pip. Supported on Windows, Linux, and macOS.
      </p>
      
      <div className="bg-[var(--bg-tertiary)] border border-[var(--border-subtle)] p-8 rounded-xl max-w-3xl">
        <h3 className="text-lg font-bold mb-4 uppercase tracking-wider text-[var(--brand-secondary)]">Latest Release</h3>
        <div className="flex items-center justify-between bg-[var(--bg-core)] p-4 rounded-md font-mono text-lg border border-[var(--border-strong)]">
          <span>pip install envforage</span>
          <button className="text-[var(--brand-secondary)] hover:text-white transition-colors">Copy</button>
        </div>
        
        <div className="mt-8 grid grid-cols-2 gap-6">
          <div>
            <h4 className="font-semibold text-[var(--text-primary)] mb-2">Requirements</h4>
            <ul className="text-[var(--text-secondary)] space-y-2 text-sm">
              <li>Python 3.9+</li>
              <li>pip 21.0+</li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold text-[var(--text-primary)] mb-2">Capabilities</h4>
            <ul className="text-[var(--text-secondary)] space-y-2 text-sm">
              <li>CUDA Hardware Detection</li>
              <li>Auto-fixes & Environment Telemetry</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
