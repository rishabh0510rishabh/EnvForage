"use client";
import React, { useState } from 'react';

interface TooltipProps {
  content: string;
  children: React.ReactNode;
  position?: 'top' | 'bottom' | 'left' | 'right';
}

export const Tooltip: React.FC<TooltipProps> = ({ content, children, position = 'top' }) => {
  const [isVisible, setIsVisible] = useState(false);

  const posStyles = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    right: "left-full top-1/2 -translate-y-1/2 ml-2"
  };

  return (
    <div 
      className="relative inline-flex items-center justify-center"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
    >
      {children}
      {isVisible && (
        <div className={`absolute z-50 px-3 py-1.5 text-xs font-mono text-[var(--text-inverse)] bg-[var(--bg-inverse)] rounded-md whitespace-nowrap shadow-xl animate-in fade-in zoom-in duration-200 ${posStyles[position]}`}>
          {content}
          {/* Subtle triangle pointer could be added here */}
        </div>
      )}
    </div>
  );
};

// --- Reusable Tooltip Component ---
import React, { useState, useRef, useEffect, ReactNode, forwardRef } from 'react';
import { createPortal } from 'react-dom';

export type TooltipPosition = 'top' | 'bottom' | 'left' | 'right';

export interface TooltipProps {
  /** The content to display inside the tooltip */
  content: ReactNode;
  /** The element that triggers the tooltip on hover/focus */
  children: ReactNode;
  /** Preferred position relative to the target */
  position?: TooltipPosition;
  /** Delay in ms before showing */
  delay?: number;
  /** Delay in ms before hiding */
  hideDelay?: number;
  /** Optional custom CSS class for the tooltip wrapper */
  className?: string;
  /** If true, the tooltip is disabled */
  disabled?: boolean;
}

/**
 * A highly robust Tooltip component.
 * Features:
 * - Uses React Portals to render at the document root (avoids z-index / overflow clipping issues)
 * - Dynamic repositioning if it collides with viewport boundaries
 * - Accessible focus/blur event listeners for keyboard navigation
 * - Hover intent delays to prevent flickering
 */
export const Tooltip = forwardRef<HTMLDivElement, TooltipProps>(
  (
    {
      content,
      children,
      position = 'top',
      delay = 300,
      hideDelay = 100,
      className = '',
      disabled = false,
    },
    ref
  ) => {
    const [isVisible, setIsVisible] = useState(false);
    const [coords, setCoords] = useState({ top: 0, left: 0 });
    
    const triggerRef = useRef<HTMLDivElement>(null);
    const tooltipRef = useRef<HTMLDivElement>(null);
    
    const showTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
    const hideTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

    const calculatePosition = () => {
      if (!triggerRef.current || !tooltipRef.current) return;

      const triggerRect = triggerRef.current.getBoundingClientRect();
      const tooltipRect = tooltipRef.current.getBoundingClientRect();
      
      let top = 0;
      let left = 0;
      const margin = 8;

      switch (position) {
        case 'top':
          top = triggerRect.top - tooltipRect.height - margin;
          left = triggerRect.left + (triggerRect.width / 2) - (tooltipRect.width / 2);
          // Viewport collision adjustment
          if (top < 0) top = triggerRect.bottom + margin;
          break;
        case 'bottom':
          top = triggerRect.bottom + margin;
          left = triggerRect.left + (triggerRect.width / 2) - (tooltipRect.width / 2);
          if (top + tooltipRect.height > window.innerHeight) top = triggerRect.top - tooltipRect.height - margin;
          break;
        case 'left':
          top = triggerRect.top + (triggerRect.height / 2) - (tooltipRect.height / 2);
          left = triggerRect.left - tooltipRect.width - margin;
          if (left < 0) left = triggerRect.right + margin;
          break;
        case 'right':
          top = triggerRect.top + (triggerRect.height / 2) - (tooltipRect.height / 2);
          left = triggerRect.right + margin;
          if (left + tooltipRect.width > window.innerWidth) left = triggerRect.left - tooltipRect.width - margin;
          break;
      }

      // Final viewport boundary checks for horizontal overflow
      if (left < margin) left = margin;
      if (left + tooltipRect.width > window.innerWidth - margin) {
        left = window.innerWidth - tooltipRect.width - margin;
      }

      setCoords({ top: top + window.scrollY, left: left + window.scrollX });
    };

    const handleMouseEnter = () => {
      if (disabled) return;
      if (hideTimeout.current) clearTimeout(hideTimeout.current);
      showTimeout.current = setTimeout(() => {
        setIsVisible(true);
      }, delay);
    };

    const handleMouseLeave = () => {
      if (showTimeout.current) clearTimeout(showTimeout.current);
      hideTimeout.current = setTimeout(() => {
        setIsVisible(false);
      }, hideDelay);
    };

    useEffect(() => {
      if (isVisible) {
        calculatePosition();
        // Recalculate on scroll or resize
        window.addEventListener('scroll', calculatePosition, { passive: true });
        window.addEventListener('resize', calculatePosition, { passive: true });
        return () => {
          window.removeEventListener('scroll', calculatePosition);
          window.removeEventListener('resize', calculatePosition);
        };
      }
    }, [isVisible, position]);

    useEffect(() => {
      return () => {
        if (showTimeout.current) clearTimeout(showTimeout.current);
        if (hideTimeout.current) clearTimeout(hideTimeout.current);
      };
    }, []);

    const tooltipElement = isVisible && !disabled ? (
      <div
        ref={tooltipRef}
        role="tooltip"
        style={{
          position: 'absolute',
          top: coords.top,
          left: coords.left,
          zIndex: 9999,
          pointerEvents: 'none',
          backgroundColor: '#1f2937',
          color: 'white',
          padding: '6px 10px',
          borderRadius: '4px',
          fontSize: '0.875rem',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
          transition: 'opacity 0.2s ease-in-out',
          opacity: 1,
        }}
        className={className}
      >
        {content}
      </div>
    ) : null;

    return (
      <>
        <div
          ref={triggerRef}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          onFocus={handleMouseEnter}
          onBlur={handleMouseLeave}
          style={{ display: 'inline-block' }}
          aria-describedby={isVisible ? 'tooltip' : undefined}
        >
          {children}
        </div>
        {/* Render tooltip at document root to avoid z-index trapping */}
        {typeof document !== 'undefined' && tooltipElement
          ? createPortal(tooltipElement, document.body)
          : null}
      </>
    );
  }
);

Tooltip.displayName = 'Tooltip';
