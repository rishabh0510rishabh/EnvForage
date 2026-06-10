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

// --- Memoized Button Component ---
import React, { ButtonHTMLAttributes } from 'react';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
    size?: 'sm' | 'md' | 'lg';
    isLoading?: boolean;
}

const ButtonComponent = React.forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className = '', variant = 'primary', size = 'md', isLoading, children, disabled, ...props }, ref) => {
        const baseStyles = 'inline-flex items-center justify-center font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2';
        
        // Example dynamic classes based on props (in a real app, use clsx/tailwind-merge)
        const variantStyles = {
            primary: 'bg-brand-primary text-white hover:bg-brand-primary/90',
            secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300',
            danger: 'bg-red-600 text-white hover:bg-red-700',
            ghost: 'bg-transparent text-gray-700 hover:bg-gray-100'
        };

        return (
            <button
                ref={ref}
                disabled={isLoading || disabled}
                className={`${baseStyles} ${variantStyles[variant]} ${className}`}
                {...props}
            >
                {isLoading ? <span className="animate-spin mr-2">⏳</span> : null}
                {children}
            </button>
        );
    }
);

ButtonComponent.displayName = 'Button';

// Memoize to prevent unnecessary re-renders when parent state changes
export const Button = React.memo(ButtonComponent);
