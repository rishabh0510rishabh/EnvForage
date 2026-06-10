
// --- Dynamic Badge Component ---
import React, { ReactNode } from 'react';

export type BadgeVariant = 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info' | 'outline';
export type BadgeSize = 'sm' | 'md' | 'lg';

export interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
  /** If true, renders with fully rounded corners (pill shape) */
  pill?: boolean;
  /** Optional icon to render before the text */
  icon?: ReactNode;
  className?: string;
  onClick?: () => void;
}

/**
 * A highly reusable, customizable Badge/Tag component.
 * Perfect for status indicators, categories, or filtering tags.
 */
export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'md',
  pill = false,
  icon,
  className = '',
  onClick,
}) => {
  // Color Maps
  const variantStyles: Record<BadgeVariant, React.CSSProperties> = {
    default: { backgroundColor: '#f3f4f6', color: '#374151' }, // gray
    primary: { backgroundColor: '#dbeafe', color: '#1e40af' }, // blue
    success: { backgroundColor: '#dcfce7', color: '#166534' }, // green
    warning: { backgroundColor: '#fef3c7', color: '#92400e' }, // yellow
    error:   { backgroundColor: '#fee2e2', color: '#991b1b' }, // red
    info:    { backgroundColor: '#e0e7ff', color: '#3730a3' }, // indigo
    outline: { backgroundColor: 'transparent', color: '#374151', border: '1px solid #d1d5db' },
  };

  // Size Maps
  const sizeStyles: Record<BadgeSize, React.CSSProperties> = {
    sm: { fontSize: '10px', padding: '2px 6px' },
    md: { fontSize: '12px', padding: '4px 10px' },
    lg: { fontSize: '14px', padding: '6px 14px' },
  };

  const isInteractive = !!onClick;

  return (
    <span
      onClick={onClick}
      role={isInteractive ? 'button' : 'status'}
      tabIndex={isInteractive ? 0 : undefined}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 600,
        lineHeight: 1,
        whiteSpace: 'nowrap',
        borderRadius: pill ? '9999px' : '4px',
        transition: 'all 0.2s ease',
        cursor: isInteractive ? 'pointer' : 'default',
        ...(isInteractive ? { '&:hover': { opacity: 0.8 } } : {}), // Pseudo handled via CSS class normally
        ...variantStyles[variant],
        ...sizeStyles[size],
      }}
      className={className}
      onKeyDown={(e) => {
        if (isInteractive && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onClick();
        }
      }}
    >
      {icon && (
        <span style={{ marginRight: '6px', display: 'flex', alignItems: 'center' }}>
          {icon}
        </span>
      )}
      {children}
    </span>
  );
};
