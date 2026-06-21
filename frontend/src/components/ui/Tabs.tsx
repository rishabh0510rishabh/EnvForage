
// --- Tabs Navigation Engine ---
import React, { useState, ReactNode, useRef } from 'react';

export interface TabData {
  id: string;
  label: ReactNode;
  content: ReactNode;
  disabled?: boolean;
}

export interface TabsProps {
  tabs: TabData[];
  /** Controlled active tab ID */
  activeId?: string;
  /** Uncontrolled default active tab ID */
  defaultActiveId?: string;
  onChange?: (id: string) => void;
  /** If true, unmounts inactive tabs from the DOM. If false, hides via CSS (preserves state). */
  lazyRender?: boolean;
}

/**
 * A highly accessible Tabs component adhering to W3C ARIA Authoring Practices.
 * Features:
 * - Left/Right arrow keyboard navigation moves focus and activates tabs
 * - Home/End keys jump to first/last tab
 * - Lazy rendering option to preserve iframe/video state in hidden tabs
 */
export const Tabs: React.FC<TabsProps> = ({
  tabs,
  activeId,
  defaultActiveId,
  onChange,
  lazyRender = true,
}) => {
  const isControlled = activeId !== undefined;
  const initialId = activeId || defaultActiveId || (tabs[0]?.id || '');
  
  const [internalActiveId, setInternalActiveId] = useState(initialId);
  const currentActiveId = isControlled ? activeId : internalActiveId;

  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const handleTabClick = (id: string) => {
    if (!isControlled) {
      setInternalActiveId(id);
    }
    if (onChange) {
      onChange(id);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent, index: number) => {
    let newIndex = -1;

    switch (e.key) {
      case 'ArrowRight':
        newIndex = index === tabs.length - 1 ? 0 : index + 1;
        break;
      case 'ArrowLeft':
        newIndex = index === 0 ? tabs.length - 1 : index - 1;
        break;
      case 'Home':
        newIndex = 0;
        break;
      case 'End':
        newIndex = tabs.length - 1;
        break;
      default:
        return;
    }

    e.preventDefault();
    
    // Skip disabled tabs if navigating via keyboard
    while (tabs[newIndex].disabled && newIndex !== index) {
      newIndex = e.key === 'ArrowRight' ? (newIndex === tabs.length - 1 ? 0 : newIndex + 1) : 
                 e.key === 'ArrowLeft' ? (newIndex === 0 ? tabs.length - 1 : newIndex - 1) : newIndex;
    }

    if (!tabs[newIndex].disabled) {
      tabRefs.current[newIndex]?.focus();
      handleTabClick(tabs[newIndex].id);
    }
  };

  return (
    <div style={{ width: '100%' }}>
      {/* Tablist */}
      <div
        role="tablist"
        aria-orientation="horizontal"
        style={{
          display: 'flex',
          borderBottom: '2px solid #e5e7eb',
          marginBottom: '16px',
        }}
      >
        {tabs.map((tab, index) => {
          const isActive = currentActiveId === tab.id;
          return (
            <button
              key={tab.id}
              ref={(el) => { tabRefs.current[index] = el; }}
              role="tab"
              aria-selected={isActive}
              aria-controls={`panel-${tab.id}`}
              id={`tab-${tab.id}`}
              disabled={tab.disabled}
              tabIndex={isActive ? 0 : -1} // Only active tab is in tab order
              onClick={() => handleTabClick(tab.id)}
              onKeyDown={(e) => handleKeyDown(e, index)}
              style={{
                padding: '12px 24px',
                background: 'none',
                border: 'none',
                borderBottom: isActive ? '2px solid #3b82f6' : '2px solid transparent',
                marginBottom: '-2px', // Overlay the container border
                cursor: tab.disabled ? 'not-allowed' : 'pointer',
                color: tab.disabled ? '#9ca3af' : isActive ? '#3b82f6' : '#4b5563',
                fontWeight: isActive ? 600 : 500,
                transition: 'all 0.2s ease',
                outline: 'none', // Handle focus ring via custom CSS class usually
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Panels */}
      <div className="tab-panels-container">
        {tabs.map((tab) => {
          const isActive = currentActiveId === tab.id;
          
          if (lazyRender && !isActive) {
            return null; // Don't mount to DOM
          }

          return (
            <div
              key={tab.id}
              role="tabpanel"
              id={`panel-${tab.id}`}
              aria-labelledby={`tab-${tab.id}`}
              hidden={!isActive} // For non-lazy mode, hide via CSS
              tabIndex={0} // Allows content to be focusable if it has no focusable elements
              style={{
                display: isActive ? 'block' : 'none',
                animation: isActive ? 'fadeIn 0.3s ease' : 'none',
              }}
            >
              {tab.content}
            </div>
          );
        })}
      </div>
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(5px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
};
