"use client";

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { createPortal } from 'react-dom';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastMessage {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
  duration?: number; // ms
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface ToastContextType {
  toast: (message: string | Omit<ToastMessage, 'id'>, type?: ToastType) => void;
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};

let toastCount = 0;

export const ToastProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback((message: string | Omit<ToastMessage, 'id'>, type: ToastType = 'info') => {
    const id = `toast-${++toastCount}`;
    let newToast: ToastMessage;

    if (typeof message === 'string') {
      newToast = {
        id,
        title: message,
        type,
        duration: 5000,
      };
    } else {
      newToast = {
        ...message,
        id,
        duration: message.duration ?? 5000,
      };
    }
    
    setToasts((prev) => [...prev, newToast]);

    // Auto dismiss
    if (newToast.duration && newToast.duration > 0) {
      setTimeout(() => {
        dismiss(id);
      }, newToast.duration);
    }
  }, [dismiss]);

  return (
    <ToastContext.Provider value={{ toast, dismiss }}>
      {children}
      {typeof document !== 'undefined' && createPortal(
        <ToastContainer toasts={toasts} dismiss={dismiss} />,
        document.body
      )}
    </ToastContext.Provider>
  );
};

const ToastContainer: React.FC<{ toasts: ToastMessage[]; dismiss: (id: string) => void }> = ({ toasts, dismiss }) => {
  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        pointerEvents: 'none',
      }}
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          role="alert"
          style={{
            pointerEvents: 'auto',
            minWidth: '300px',
            maxWidth: '400px',
            backgroundColor: t.type === 'error' ? '#fee2e2' : 
                             t.type === 'success' ? '#dcfce7' : 
                             t.type === 'warning' ? '#fef3c7' : '#ffffff',
            borderLeft: `4px solid ${
              t.type === 'error' ? '#ef4444' : 
              t.type === 'success' ? '#22c55e' : 
              t.type === 'warning' ? '#f59e0b' : '#3b82f6'
            }`,
            padding: '16px',
            borderRadius: '6px',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
            transition: 'all 0.3s ease-in-out',
            animation: 'toastSlideIn 0.3s forwards',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <h4 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: '#111827' }}>
                {t.title}
              </h4>
              {t.description && (
                <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#4b5563' }}>
                  {t.description}
                </p>
              )}
            </div>
            <button
              onClick={() => dismiss(t.id)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: '#9ca3af',
                padding: '4px',
              }}
              aria-label="Close"
            >
              ×
            </button>
          </div>
          
          {t.action && (
            <div style={{ marginTop: '12px' }}>
              <button
                onClick={() => {
                  t.action!.onClick();
                  dismiss(t.id);
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#3b82f6',
                  fontWeight: 600,
                  fontSize: '13px',
                  cursor: 'pointer',
                  padding: 0,
                }}
              >
                {t.action.label}
              </button>
            </div>
          )}
        </div>
      ))}
      <style>{`
        @keyframes toastSlideIn {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>
    </div>
  );
};
