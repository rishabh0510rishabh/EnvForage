import React from 'react';

// Simplified wrapper for MDX code blocks
export const CodeBlock = ({ children, className }: any) => {
  const language = className ? className.replace(/language-/, '') : '';
  
  return (
    <div className="relative group my-6 rounded-lg overflow-hidden border border-[var(--border-strong)]">
      <div className="flex justify-between items-center bg-[#1e1e1e] px-4 py-2 border-b border-[var(--border-subtle)]">
        <span className="text-xs text-gray-400 uppercase font-mono">{language || 'text'}</span>
        <button className="text-xs text-[var(--brand-secondary)] opacity-0 group-hover:opacity-100 transition-opacity">
          Copy
        </button>
      </div>
      <pre className="p-4 bg-[#0d1117] text-gray-300 overflow-x-auto font-mono text-sm">
        <code className={className}>
          {children}
        </code>
      </pre>
    </div>
  );
};
