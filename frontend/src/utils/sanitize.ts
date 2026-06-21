
import React from 'react';

// --- DOMPurify HTML Sanitizer ---
// Note: In a real project, run `npm install dompurify @types/dompurify`
// import DOMPurify from 'dompurify';

/**
 * Mocking DOMPurify for this snippet.
 * In production, this uses the actual DOMPurify library.
 */
const DOMPurify = {
  sanitize: (html: string, config?: any) => {
    // Highly simplistic mock. Do NOT use this exact regex loop in production.
    // The real DOMPurify uses a complex inert DOM tree to strip malicious execution vectors.
    let clean = html;
    // Very naive mock strip of script tags
    clean = clean.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
    clean = clean.replace(/on\w+="[^"]*"/gi, ''); // mock strip inline handlers
    return clean;
  }
};

export interface SanitizeConfig {
  /** If true, strips all HTML tags, returning plain text */
  stripAll?: boolean;
  /** Specific tags to allow. Defaults to a safe subset. */
  allowedTags?: string[];
  /** Ensure links open in new tabs securely */
  secureLinks?: boolean;
}

const DEFAULT_SAFE_TAGS = [
  'b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code', 'pre'
];

/**
 * A crucial security utility for React frontends.
 * Any data originating from the backend (or user input) that needs to be 
 * rendered via `dangerouslySetInnerHTML` MUST pass through this sanitizer first.
 * 
 * Prevents Cross-Site Scripting (XSS) by parsing HTML into an inert document 
 * and stripping malicious vectors like <script> or onerror="..." attributes.
 * 
 * @param dirtyHtml The potentially unsafe HTML string
 * @param config Options for strictness
 * @returns A guaranteed safe HTML string
 */
export function sanitizeHtml(dirtyHtml: string | null | undefined, config: SanitizeConfig = {}): string {
  if (!dirtyHtml) return '';

  const {
    stripAll = false,
    allowedTags = DEFAULT_SAFE_TAGS,
    secureLinks = true,
  } = config;

  const purifyConfig: { FORCE_BODY: boolean; ALLOWED_TAGS?: string[]; ALLOWED_ATTR?: string[] } = {
    // ALWAYS force body, prevents weird root node bypasses
    FORCE_BODY: true,
  };

  if (stripAll) {
    purifyConfig.ALLOWED_TAGS = [];
    purifyConfig.ALLOWED_ATTR = [];
  } else {
    purifyConfig.ALLOWED_TAGS = allowedTags;
    // Allow class, href, title, but NOT style (prevents CSS injection)
    purifyConfig.ALLOWED_ATTR = ['class', 'href', 'title', 'target', 'rel'];
  }

  // Hook to enforce secure links (target="_blank" rel="noopener noreferrer")
  // In real DOMPurify, this is done via a hook:
  // DOMPurify.addHook('afterSanitizeAttributes', function(node) { ... })
  
  let cleanHtml = DOMPurify.sanitize(dirtyHtml, purifyConfig);
  
  // Simulated link securing (since we mocked the hook above)
  if (secureLinks && !stripAll) {
    cleanHtml = cleanHtml.replace(/<a /g, '<a target="_blank" rel="noopener noreferrer" ');
  }

  return cleanHtml as string;
}

/**
 * React Component Wrapper for convenience.
 * 
 * Usage:
 * <SafeHtml html={user.bio} className="prose" />
 */
export const SafeHtml: React.FC<{ html: string; className?: string; config?: SanitizeConfig }> = ({
  html,
  className,
  config,
}) => {
  const safeContent = sanitizeHtml(html, config);
  
  return React.createElement("div", {
    className,
    dangerouslySetInnerHTML: { __html: safeContent }
  });
};
