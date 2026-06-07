"use client";
import React, { useState, useEffect } from 'react';

export const SearchModal = ({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div 
        className="w-full max-w-2xl bg-[var(--bg-core)] border border-[var(--brand-secondary)] rounded-xl shadow-[0_0_40px_rgba(0,255,255,0.15)] overflow-hidden animate-in fade-in zoom-in-95 duration-200"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center px-4 border-b border-[var(--border-strong)]">
          <svg className="w-5 h-5 text-[var(--text-secondary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
          <input 
            autoFocus
            type="text" 
            placeholder="Search documentation, components, or commands..." 
            className="w-full bg-transparent px-4 py-4 outline-none text-[var(--text-primary)] text-lg placeholder:text-[var(--text-muted)]"
          />
          <span className="text-xs text-[var(--text-muted)] border border-[var(--border-subtle)] rounded px-1.5 py-0.5">ESC</span>
        </div>
        <div className="p-4 bg-[var(--bg-tertiary)] min-h-[200px] flex items-center justify-center text-[var(--text-muted)]">
          Start typing to search...
        </div>
      </div>
    </div>
  );
};
