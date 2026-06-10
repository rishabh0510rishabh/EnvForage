import React from 'react';

export const Heading = ({ level, children, ...props }: { level: number, children: React.ReactNode, [key: string]: unknown }) => {
  const Tag = `h${level}` as keyof React.JSX.IntrinsicElements;
  const id = typeof children === 'string' 
    ? children.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')
    : '';

  return (
    <Tag 
      id={id} 
      className={`group flex items-center relative font-bold text-[var(--text-primary)] mt-8 mb-4 ${level === 1 ? 'text-4xl' : level === 2 ? 'text-2xl' : 'text-xl'}`}
      {...props}
    >
      <a 
        href={`#${id}`} 
        className="absolute -left-6 text-[var(--brand-secondary)] opacity-0 group-hover:opacity-100 transition-opacity"
        aria-hidden="true"
      >
        #
      </a>
      {children}
    </Tag>
  );
};
