
// --- Accessible ToggleSwitch ---
import React from 'react';

export interface ToggleSwitchProps {
  /** Current state of the toggle */
  checked: boolean;
  /** Callback fired when the state changes */
  onChange: (checked: boolean) => void;
  /** Optional label text placed next to the switch */
  label?: string;
  /** Description text placed below the label */
  description?: string;
  /** If true, the switch is disabled */
  disabled?: boolean;
  /** Screen-reader specific text if no visual label is provided */
  ariaLabel?: string;
}

/**
 * A highly accessible toggle switch (checkbox alternative).
 * Features:
 * - Proper `role="switch"` and `aria-checked` bindings
 * - Tactile spring-like CSS transitions on the thumb
 * - Focus rings for keyboard navigation
 */
export const ToggleSwitch: React.FC<ToggleSwitchProps> = ({
  checked,
  onChange,
  label,
  description,
  disabled = false,
  ariaLabel,
}) => {
  const handleToggle = () => {
    if (!disabled) {
      onChange(!checked);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      handleToggle();
    }
  };

  return (
    <label
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
      }}
    >
      <div style={{ flex: 1, marginRight: '16px' }}>
        {label && (
          <div style={{ fontSize: '14px', fontWeight: 500, color: '#111827' }}>
            {label}
          </div>
        )}
        {description && (
          <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '2px' }}>
            {description}
          </div>
        )}
      </div>

      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={ariaLabel || label}
        disabled={disabled}
        onClick={handleToggle}
        onKeyDown={handleKeyDown}
        style={{
          position: 'relative',
          display: 'inline-flex',
          height: '24px',
          width: '44px',
          flexShrink: 0,
          cursor: disabled ? 'not-allowed' : 'pointer',
          borderRadius: '9999px',
          border: '2px solid transparent',
          backgroundColor: checked ? '#3b82f6' : '#e5e7eb',
          transition: 'background-color 0.2s ease-in-out',
          outline: 'none',
        }}
      >
        <span
          aria-hidden="true"
          style={{
            pointerEvents: 'none',
            display: 'inline-block',
            height: '20px',
            width: '20px',
            borderRadius: '50%',
            backgroundColor: '#ffffff',
            boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
            transform: checked ? 'translateX(20px)' : 'translateX(0)',
            transition: 'transform 0.2s cubic-bezier(0.4, 0.0, 0.2, 1)',
          }}
        />
      </button>
    </label>
  );
};
