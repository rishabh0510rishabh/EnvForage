import React from 'react';

export default function DockerTemplatesPage() {
  return (
    <div className="container py-20 min-h-screen">
      <h1 className="text-4xl font-black mb-6 text-[var(--text-primary)]">Docker Virtualization Hub</h1>
      <p className="text-xl text-[var(--text-secondary)] mb-12 max-w-2xl">
        Pre-configured Dockerfiles and Docker Compose templates injected with EnvForage base images for instant GPU access.
      </p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="bg-[var(--bg-tertiary)] p-8 rounded-xl border border-[var(--border-subtle)]">
          <h2 className="text-2xl font-bold mb-4">PyTorch + CUDA 12.1</h2>
          <p className="text-[var(--text-secondary)] mb-6">Ubuntu 22.04 base with pre-installed Nvidia Container Toolkit configurations.</p>
          <pre className="bg-[var(--bg-core)] p-4 rounded-md font-mono text-sm overflow-x-auto text-green-400">
            FROM ghcr.io/envforage/pytorch:2.1.0-cuda12.1
          </pre>
        </div>
        <div className="bg-[var(--bg-tertiary)] p-8 rounded-xl border border-[var(--border-subtle)]">
          <h2 className="text-2xl font-bold mb-4">TensorFlow + ROCm 5.6</h2>
          <p className="text-[var(--text-secondary)] mb-6">AMD GPU optimized base image for TensorFlow workflows.</p>
          <pre className="bg-[var(--bg-core)] p-4 rounded-md font-mono text-sm overflow-x-auto text-green-400">
            FROM ghcr.io/envforage/tf:2.14-rocm5.6
          </pre>
        </div>
      </div>
    </div>
  );
}
