import React from 'react';

export default function PrivacyPage() {
  return (
    <div className="container py-20 min-h-screen max-w-4xl">
      <h1 className="text-4xl font-black mb-10 text-[var(--text-primary)]">Telemetry & Privacy Protection</h1>
      
      <div className="prose prose-invert prose-lg text-[var(--text-secondary)]">
        <p>At EnvForage, we believe your code is your business. Our diagnostic tools are designed to read hardware signatures, NOT your source code.</p>
        
        <h2 className="text-2xl font-bold text-[var(--text-primary)] mt-10 mb-4">1. What We Collect</h2>
        <p>When you run an audit or diagnostic, we collect:</p>
        <ul>
          <li>OS Version and Kernel details</li>
          <li>GPU Models and Driver versions (e.g., NVIDIA Driver 535)</li>
          <li>CUDA/ROCm toolkit versions</li>
          <li>Python version and installed package hashes</li>
        </ul>
        
        <h2 className="text-2xl font-bold text-[var(--text-primary)] mt-10 mb-4">2. What We Never Collect</h2>
        <ul>
          <li>Source code or proprietary algorithms</li>
          <li>Environment variables (unless explicitly opted-in for troubleshooting)</li>
          <li>File paths outside the virtual environment</li>
          <li>Personally Identifiable Information (PII)</li>
        </ul>
        
        <h2 className="text-2xl font-bold text-[var(--text-primary)] mt-10 mb-4">3. Opting Out</h2>
        <p>You can fully disable all telemetry by running: <code>envforge config set telemetry false</code></p>
      </div>
    </div>
  );
}
