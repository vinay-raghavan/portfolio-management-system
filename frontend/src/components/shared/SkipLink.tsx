'use client';

import { cn } from '@/lib/utils';

interface SkipLinkProps {
  href?: string;
  className?: string;
  children?: React.ReactNode;
}

/**
 * Skip link component for accessibility.
 * Allows keyboard users to skip to main content.
 * Only visible when focused.
 */
export function SkipLink({
  href = '#main-content',
  className,
  children = 'Skip to main content',
}: SkipLinkProps) {
  return (
    <a
      href={href}
      className={cn(
        // Visually hidden but accessible
        'sr-only focus:not-sr-only',
        // Position at top when focused
        'focus:absolute focus:top-4 focus:left-4 focus:z-[200]',
        // Style when visible
        'focus:inline-flex focus:items-center focus:px-4 focus:py-2',
        'focus:rounded-md focus:bg-primary focus:text-primary-foreground',
        'focus:font-medium focus:shadow-lg',
        'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        // Transition
        'transition-all',
        className
      )}
    >
      {children}
    </a>
  );
}

/**
 * Additional skip links for navigation within sections
 */
export function SkipLinks() {
  return (
    <div className="skip-links">
      <SkipLink href="#main-content">Skip to main content</SkipLink>
      <SkipLink href="#main-navigation" className="focus:top-14">
        Skip to navigation
      </SkipLink>
    </div>
  );
}

