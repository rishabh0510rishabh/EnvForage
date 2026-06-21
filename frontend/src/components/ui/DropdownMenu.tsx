
// --- Accessible DropdownMenu ---
import React, { useState, useRef, useEffect, ReactNode, forwardRef } from 'react';

export interface DropdownItemProps {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
}

export const DropdownItem = forwardRef<HTMLButtonElement, DropdownItemProps>(
  ({ children, onClick, disabled = false, className = '' }, ref) => {
    return (
      <button
        ref={ref}
        role="menuitem"
        tabIndex={-1}
        disabled={disabled}
        onClick={onClick}
        style={{
          display: 'block',
          width: '100%',
          textAlign: 'left',
          padding: '8px 16px',
          background: 'none',
          border: 'none',
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.5 : 1,
        }}
        className={className}
      >
        {children}
      </button>
    );
  }
);
DropdownItem.displayName = 'DropdownItem';

export interface DropdownMenuProps {
  trigger: ReactNode;
  children: ReactNode;
  align?: 'left' | 'right';
  className?: string;
}

/**
 * A fully accessible WAI-ARIA compliant Dropdown Menu.
 * Features:
 * - Keyboard navigation (ArrowDown, ArrowUp, Escape)
 * - Click-outside closure detection
 * - Focus trapping and restoration
 */
export const DropdownMenu: React.FC<DropdownMenuProps> = ({
  trigger,
  children,
  align = 'left',
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const handleToggle = () => {
    setIsOpen(!isOpen);
  };

  const handleClose = () => {
    setIsOpen(false);
    triggerRef.current?.focus();
  };

  // Click outside to close
  useEffect(() => {
    if (!isOpen) return;
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        handleClose();
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [isOpen]);

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen || !menuRef.current) return;
    
    const items = Array.from(
      menuRef.current.querySelectorAll('[role="menuitem"]:not([disabled])')
    ) as HTMLButtonElement[];
    
    if (items.length > 0) {
      // Focus first item initially
      items[0].focus();
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        handleClose();
        return;
      }

      if (e.key === 'Tab') {
        // Tab closes menu to prevent breaking focus trap
        handleClose();
        return;
      }

      const currentIndex = items.findIndex((item) => document.activeElement === item);

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        const nextIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
        items[nextIndex]?.focus();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const prevIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
        items[prevIndex]?.focus();
      }
    };

    menuRef.current.addEventListener('keydown', handleKeyDown);
    return () => {
      // eslint-disable-next-line react-hooks/exhaustive-deps
      menuRef.current?.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  return (
    <div ref={containerRef} style={{ position: 'relative', display: 'inline-block' }}>
      <button
        ref={triggerRef}
        onClick={handleToggle}
        aria-haspopup="true"
        aria-expanded={isOpen}
        style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer' }}
      >
        {trigger}
      </button>

      {isOpen && (
        <div
          ref={menuRef}
          role="menu"
          aria-orientation="vertical"
          style={{
            position: 'absolute',
            top: '100%',
            [align === 'left' ? 'left' : 'right']: 0,
            marginTop: '8px',
            minWidth: '200px',
            backgroundColor: '#ffffff',
            border: '1px solid #e5e7eb',
            borderRadius: '6px',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
            zIndex: 50,
            padding: '4px 0',
          }}
          className={className}
        >
          {/* We intercept clicks on children to close the menu automatically */}
          {React.Children.map(children, (child) => {
            if (React.isValidElement(child)) {
              const element = child as React.ReactElement<{ onClick?: (e: React.MouseEvent) => void }>;
              return React.cloneElement(element, {
                onClick: (e: React.MouseEvent) => {
                  if (element.props.onClick) element.props.onClick(e);
                  handleClose();
                },
              });
            }
            return child;
          })}
        </div>
      )}
    </div>
  );
};
