
// --- Accordion Section Component ---
import React, { useState, useRef, useEffect, ReactNode } from 'react';

export interface AccordionItemProps {
  title: ReactNode;
  children: ReactNode;
  /** If true, the accordion is open by default */
  defaultOpen?: boolean;
  /** If provided, overrides internal state (Controlled mode) */
  isOpen?: boolean;
  /** Callback fired when toggled */
  onToggle?: (isOpen: boolean) => void;
  /** Optional icon override */
  icon?: ReactNode;
}

/**
 * A highly accessible Accordion Item.
 * Uses `aria-expanded` and `aria-controls` to link the header button to the collapsible region.
 * Features smooth height transitions by measuring DOM dimensions dynamically.
 */
export const AccordionItem: React.FC<AccordionItemProps> = ({
  title,
  children,
  defaultOpen = false,
  isOpen: controlledIsOpen,
  onToggle,
  icon,
}) => {
  const [internalIsOpen, setInternalIsOpen] = useState(defaultOpen);
  const isControlled = controlledIsOpen !== undefined;
  const isOpen = isControlled ? controlledIsOpen : internalIsOpen;

  const contentRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState<number | 'auto'>(defaultOpen ? 'auto' : 0);

  useEffect(() => {
    if (!contentRef.current) return;
    
    if (isOpen) {
      // Measure actual content height to animate to
      const scrollHeight = contentRef.current.scrollHeight;
      setHeight(scrollHeight);
      // After animation completes, set to auto so it can resize with window
      const timeout = setTimeout(() => setHeight('auto'), 300);
      return () => clearTimeout(timeout);
    } else {
      // To animate close, we first set the fixed height, then immediately set to 0
      setHeight(contentRef.current.scrollHeight);
      const raf = requestAnimationFrame(() => {
        setHeight(0);
      });
      return () => cancelAnimationFrame(raf);
    }
  }, [isOpen]);

  const handleToggle = () => {
    const newState = !isOpen;
    if (!isControlled) {
      setInternalIsOpen(newState);
    }
    if (onToggle) {
      onToggle(newState);
    }
  };

  const id = useRef(`accordion-${Math.random().toString(36).substr(2, 9)}`).current;

  return (
    <div style={{ borderBottom: '1px solid #e5e7eb', marginBottom: '8px' }}>
      <h3>
        <button
          onClick={handleToggle}
          aria-expanded={isOpen}
          aria-controls={`content-${id}`}
          id={`header-${id}`}
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            width: '100%',
            padding: '16px',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            textAlign: 'left',
            fontSize: '16px',
            fontWeight: 500,
            color: '#111827',
          }}
        >
          <span>{title}</span>
          <span
            style={{
              transform: isOpen ? 'rotate(180deg)' : 'rotate(0)',
              transition: 'transform 0.3s ease',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            {icon || (
              <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            )}
          </span>
        </button>
      </h3>
      <div
        id={`content-${id}`}
        role="region"
        aria-labelledby={`header-${id}`}
        style={{
          height,
          overflow: 'hidden',
          transition: 'height 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        }}
      >
        <div ref={contentRef} style={{ padding: '0 16px 16px 16px', color: '#4b5563' }}>
          {children}
        </div>
      </div>
    </div>
  );
};
