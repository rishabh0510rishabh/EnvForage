import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  glow?: boolean;
}

export const Card: React.FC<CardProps> = ({ children, className = '', glow = false, ...props }) => {
  return (
    <div 
      className={`relative overflow-hidden rounded-xl bg-[var(--bg-tertiary)] border border-[var(--border-subtle)] p-6 transition-all duration-300 ${glow ? 'hover:shadow-[0_0_20px_rgba(0,255,255,0.2)] hover:border-[var(--brand-secondary)]' : ''} ${className}`}
      style={{
        backdropFilter: 'blur(10px)',
        backgroundColor: 'rgba(15, 23, 42, 0.6)'
      }}
      {...props}
    >
      <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-[var(--brand-secondary)] to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
      {children}
    </div>
  );
};
