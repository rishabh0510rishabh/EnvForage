
// --- Animated ProgressBar Component ---
import React from 'react';

export interface ProgressBarProps {
  /** The current progress value (0 to 100). If omitted, renders indeterminate mode. */
  value?: number;
  /** Maximum value (default 100) */
  max?: number;
  /** If true, displays the percentage text inside/beside the bar */
  showLabel?: boolean;
  /** Height of the progress bar track */
  height?: number | string;
  /** Custom color for the progress fill */
  color?: string;
  /** Custom track background color */
  trackColor?: string;
  /** Optional aria-label for accessibility */
  ariaLabel?: string;
}

/**
 * A highly accessible, smooth-animated Progress Bar component.
 * Supports both Determinate (known % complete) and Indeterminate (loading spinner style) modes.
 */
export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  max = 100,
  showLabel = false,
  height = 8,
  color = '#3b82f6', // Tailwind blue-500
  trackColor = '#e5e7eb', // Tailwind gray-200
  ariaLabel = 'Progress',
}) => {
  // Determine mode
  const isIndeterminate = value === undefined || value === null;
  
  // Safe percentage calculation
  const safeValue = Math.min(Math.max(value || 0, 0), max);
  const percentage = Math.round((safeValue / max) * 100);

  return (
    <div style={{ width: '100%' }}>
      {showLabel && !isIndeterminate && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '4px' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: '#4b5563' }}>
            {percentage}%
          </span>
        </div>
      )}
      
      <div
        role="progressbar"
        aria-valuenow={isIndeterminate ? undefined : safeValue}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={ariaLabel}
        style={{
          width: '100%',
          height: height,
          backgroundColor: trackColor,
          borderRadius: '9999px',
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        <div
          style={{
            height: '100%',
            backgroundColor: color,
            borderRadius: '9999px',
            // Transition only handles determinate width changes smoothly
            transition: 'width 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
            width: isIndeterminate ? '100%' : `${percentage}%`,
            // If indeterminate, apply a CSS sliding gradient animation
            animation: isIndeterminate ? 'progressIndeterminate 1.5s infinite linear' : 'none',
            transformOrigin: 'left',
          }}
        />
      </div>

      <style>{`
        @keyframes progressIndeterminate {
          0% {
            transform: translateX(-100%) scaleX(0.2);
          }
          50% {
            transform: translateX(0) scaleX(0.5);
          }
          100% {
            transform: translateX(100%) scaleX(0.2);
          }
        }
      `}</style>
    </div>
  );
};
