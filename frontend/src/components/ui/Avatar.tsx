
// --- Avatar Fallback System ---
import React, { useState } from 'react';
import Image from 'next/image';

export type AvatarSize = 'sm' | 'md' | 'lg' | 'xl' | number;
export type AvatarShape = 'circle' | 'square' | 'rounded';

export interface AvatarProps {
  /** URL of the image to load */
  src?: string | null;
  /** Alt text for screen readers (highly recommended) */
  alt?: string;
  /** Name used to generate initials if image fails or is absent */
  name?: string;
  size?: AvatarSize;
  shape?: AvatarShape;
  /** Custom background color for the fallback state */
  fallbackColor?: string;
}

/**
 * A robust Avatar component.
 * Features:
 * - Attempts to load `src`.
 * - If `src` fails (404) or is null, falls back to generating initials from `name`.
 * - If `name` is missing, falls back to a generic SVG user icon.
 */
/**
 * A robust Avatar component with automatic fallback handling.
 *
 * Attempts to load the provided `src` URL using next/image for optimized
 * delivery. Falls back to initials derived from `name` if the image fails
 * to load or is absent. If `name` is also missing, renders a generic SVG
 * user icon. Dimensions are fixed to prevent Cumulative Layout Shift (CLS).
 *
 * @param src - URL of the avatar image to load (may be null/undefined)
 * @param alt - Accessible alt text for the image
 * @param name - Display name used to generate initials fallback
 * @param size - Avatar size: preset string or pixel number
 * @param shape - Border-radius shape: circle, rounded, or square
 * @param fallbackColor - Background colour used in the fallback state
 */
export const Avatar: React.FC<AvatarProps> = ({
  src,
  alt = 'Avatar',
  name,
  size = 'md',
  shape = 'circle',
  fallbackColor = '#e5e7eb',
}) => {
  const [imgError, setImgError] = useState(false);

  // Size mapping
  const sizeMap: Record<string, number> = {
    sm: 32,
    md: 48,
    lg: 64,
    xl: 96,
  };
  const pixelSize = typeof size === 'number' ? size : sizeMap[size] || 48;

  // Shape mapping
  const radiusMap: Record<AvatarShape, string> = {
    circle: '50%',
    rounded: '12px',
    square: '0px',
  };

  /**
   * Derive up to two initials from a display name string.
   * Returns the first character of the first two words, or the first two
   * characters of a single-word name.
   */
  const getInitials = (str?: string) => {
    if (!str) return '';
    const parts = str.trim().split(' ');
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    }
    return str.substring(0, 2).toUpperCase();
  };

  const showFallback = !src || imgError;
  const initials = getInitials(name);

  return (
    <div
      style={{
        width: pixelSize,
        height: pixelSize,
        borderRadius: radiusMap[shape],
        overflow: 'hidden',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: showFallback ? fallbackColor : 'transparent',
        color: '#4b5563',
        fontWeight: 600,
        fontSize: `${pixelSize * 0.4}px`,
        flexShrink: 0,
        userSelect: 'none',
      }}
      role="img"
      aria-label={alt || name || 'User Avatar'}
    >
      {!showFallback ? (
        <Image
          src={src as string}
          alt={alt}
          width={pixelSize}
          height={pixelSize}
          onError={() => setImgError(true)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
          }}
        />
      ) : initials ? (
        <span>{initials}</span>
      ) : (
        // Generic User Icon SVG Fallback
        <svg
          style={{ width: '60%', height: '60%', color: '#9ca3af' }}
          fill="currentColor"
          viewBox="0 0 24 24"
        >
          <path d="M24 20.993V24H0v-2.996A14.977 14.977 0 0112.004 15c4.904 0 9.26 2.354 11.996 5.993zM16.002 8.999a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      )}
    </div>
  );
};
