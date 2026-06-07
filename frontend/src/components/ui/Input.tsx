import React from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input: React.FC<InputProps> = ({ label, error, className = '', ...props }) => {
  return (
    <div className="flex flex-col gap-2 w-full">
      {label && <label className="text-sm font-semibold tracking-wider text-[var(--text-secondary)] uppercase">{label}</label>}
      <div className="relative">
        <input 
          className={`w-full bg-[var(--bg-tertiary)] border-b-2 border-[var(--border-strong)] px-4 py-3 text-[var(--text-primary)] outline-none transition-all focus:border-[var(--brand-secondary)] focus:bg-[rgba(0,255,255,0.02)] ${error ? 'border-red-500' : ''} ${className}`}
          style={{ borderTop: 'none', borderLeft: 'none', borderRight: 'none' }}
          {...props}
        />
        <div className="absolute bottom-[-2px] left-0 h-[2px] w-0 bg-[var(--brand-secondary)] transition-all duration-300 peer-focus:w-full" />
      </div>
      {error && <span className="text-xs text-red-500 mt-1">{error}</span>}
    </div>
  );
};
