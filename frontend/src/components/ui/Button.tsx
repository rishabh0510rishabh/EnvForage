import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'cyber';
}

export const Button: React.FC<ButtonProps> = ({ children, variant = 'primary', className = '', ...props }) => {
  const baseStyles = "inline-flex items-center justify-center font-bold transition-all duration-200 uppercase tracking-wider text-sm outline-none";
  
  const variants = {
    primary: "bg-[var(--brand-primary)] text-[var(--text-inverse)] rounded-md px-6 py-3 hover:bg-opacity-90 hover:shadow-lg",
    secondary: "bg-transparent border border-[var(--border-strong)] text-[var(--text-primary)] rounded-md px-6 py-3 hover:border-[var(--brand-secondary)] hover:text-[var(--brand-secondary)]",
    ghost: "bg-transparent text-[var(--text-secondary)] px-4 py-2 hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] rounded-md",
    cyber: "relative bg-[var(--bg-core)] text-[var(--brand-secondary)] px-8 py-3 border border-[var(--brand-secondary)] hover:bg-[var(--brand-secondary)] hover:text-[var(--bg-core)] before:content-[''] before:absolute before:top-0 before:left-[-10px] before:w-[10px] before:h-full before:bg-[var(--brand-secondary)] before:opacity-0 hover:before:opacity-100 before:transition-all"
  };

  const clipPathStyle = variant === 'cyber' ? { clipPath: 'polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px)' } : {};

  return (
    <button 
      className={`${baseStyles} ${variants[variant]} ${className}`}
      style={clipPathStyle}
      {...props}
    >
      {children}
    </button>
  );
};
