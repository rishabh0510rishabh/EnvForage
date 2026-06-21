import React, { ButtonHTMLAttributes } from 'react';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'ghost' | 'cyber';
    size?: 'sm' | 'md' | 'lg';
    isLoading?: boolean;
}

const ButtonComponent = React.forwardRef<HTMLButtonElement, ButtonProps>(
    ({ children, variant = 'primary', size = 'md', isLoading, className = '', disabled, ...props }, ref) => {
        const baseStyles = "inline-flex items-center justify-center font-bold transition-all duration-200 uppercase tracking-wider text-sm outline-none";
        
        const variants = {
            primary: "bg-[var(--brand-primary)] text-[var(--text-inverse)] rounded-md hover:bg-opacity-90 hover:shadow-lg",
            secondary: "bg-transparent border border-[var(--border-strong)] text-[var(--text-primary)] rounded-md hover:border-[var(--brand-secondary)] hover:text-[var(--brand-secondary)]",
            ghost: "bg-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] rounded-md",
            cyber: "relative bg-[var(--bg-core)] text-[var(--brand-secondary)] border border-[var(--brand-secondary)] hover:bg-[var(--brand-secondary)] hover:text-[var(--bg-core)] before:content-[''] before:absolute before:top-0 before:left-[-10px] before:w-[10px] before:h-full before:bg-[var(--brand-secondary)] before:opacity-0 hover:before:opacity-100 before:transition-all"
        };

        const sizes = {
            sm: "px-4 py-2 text-xs",
            md: "px-6 py-3 text-sm",
            lg: "px-8 py-4 text-base"
        };

        const clipPathStyle = variant === 'cyber' ? { clipPath: 'polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px)' } : {};

        return (
            <button 
                ref={ref}
                disabled={isLoading || disabled}
                className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
                style={clipPathStyle}
                {...props}
            >
                {isLoading ? <span className="animate-spin mr-2">⏳</span> : null}
                {children}
            </button>
        );
    }
);

ButtonComponent.displayName = 'Button';

export const Button = React.memo(ButtonComponent);
