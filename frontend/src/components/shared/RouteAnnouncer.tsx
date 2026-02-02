'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';

/**
 * Announces route changes to screen readers.
 * 
 * This component listens to route changes and announces the new page
 * to screen readers using an ARIA live region.
 */

// Map of routes to human-readable page names
const ROUTE_NAMES: Record<string, string> = {
  '/': 'Dashboard',
  '/dashboard': 'Dashboard',
  '/portfolio': 'Portfolio',
  '/watchlist': 'Watchlist',
  '/orders': 'Orders',
  '/analysis': 'Analysis',
  '/signals': 'Signals',
  '/algo': 'Algo Trading',
  '/alerts': 'Alerts',
  '/settings': 'Settings',
  '/charts': 'Multi-Chart View',
  '/backtest': 'Backtesting',
};

function getPageName(pathname: string): string {
  // Check for exact match first
  if (ROUTE_NAMES[pathname]) {
    return ROUTE_NAMES[pathname];
  }

  // Check for partial matches (e.g., /analysis/RELIANCE -> Analysis)
  for (const [route, name] of Object.entries(ROUTE_NAMES)) {
    if (pathname.startsWith(route) && route !== '/') {
      // Extract any symbol or ID from the path
      const suffix = pathname.replace(route, '').replace(/^\//, '');
      if (suffix) {
        return `${name}: ${suffix}`;
      }
      return name;
    }
  }

  // Fallback to formatted pathname
  const parts = pathname.split('/').filter(Boolean);
  if (parts.length > 0) {
    const lastPart = parts[parts.length - 1];
    return lastPart.charAt(0).toUpperCase() + lastPart.slice(1).replace(/-/g, ' ');
  }

  return 'Page';
}

export function RouteAnnouncer() {
  const pathname = usePathname();
  const [announcement, setAnnouncement] = useState('');

  useEffect(() => {
    // Announce the new page after a small delay to ensure the page has rendered
    const timer = setTimeout(() => {
      const pageName = getPageName(pathname);
      setAnnouncement(`Navigated to ${pageName}`);
      
      // Clear announcement after screen reader has time to announce
      setTimeout(() => {
        setAnnouncement('');
      }, 1000);
    }, 100);

    return () => clearTimeout(timer);
  }, [pathname]);

  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className="sr-only"
    >
      {announcement}
    </div>
  );
}

