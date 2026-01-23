'use client';

import { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';

interface AriaLiveContextType {
  announce: (message: string, priority?: 'polite' | 'assertive') => void;
  announcePolite: (message: string) => void;
  announceAssertive: (message: string) => void;
}

const AriaLiveContext = createContext<AriaLiveContextType | null>(null);

export function useAriaLive() {
  const context = useContext(AriaLiveContext);
  if (!context) {
    throw new Error('useAriaLive must be used within AriaLiveProvider');
  }
  return context;
}

interface AriaLiveProviderProps {
  children: React.ReactNode;
}

/**
 * Provider for ARIA live regions that announces dynamic content to screen readers.
 * 
 * Usage:
 * - Wrap your app with <AriaLiveProvider>
 * - Use the useAriaLive() hook to announce messages
 * 
 * Example:
 * const { announce, announcePolite, announceAssertive } = useAriaLive();
 * announce('Order placed successfully');
 * announceAssertive('Error: Connection lost'); // For urgent messages
 */
export function AriaLiveProvider({ children }: AriaLiveProviderProps) {
  const [politeMessage, setPoliteMessage] = useState('');
  const [assertiveMessage, setAssertiveMessage] = useState('');
  const politeTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const assertiveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Clear messages after they're announced
  useEffect(() => {
    return () => {
      if (politeTimeoutRef.current) clearTimeout(politeTimeoutRef.current);
      if (assertiveTimeoutRef.current) clearTimeout(assertiveTimeoutRef.current);
    };
  }, []);

  const announcePolite = useCallback((message: string) => {
    // Clear existing timeout
    if (politeTimeoutRef.current) clearTimeout(politeTimeoutRef.current);
    
    // Set new message
    setPoliteMessage(message);
    
    // Clear after screen reader has time to announce
    politeTimeoutRef.current = setTimeout(() => {
      setPoliteMessage('');
    }, 3000);
  }, []);

  const announceAssertive = useCallback((message: string) => {
    if (assertiveTimeoutRef.current) clearTimeout(assertiveTimeoutRef.current);
    
    setAssertiveMessage(message);
    
    assertiveTimeoutRef.current = setTimeout(() => {
      setAssertiveMessage('');
    }, 3000);
  }, []);

  const announce = useCallback((message: string, priority: 'polite' | 'assertive' = 'polite') => {
    if (priority === 'assertive') {
      announceAssertive(message);
    } else {
      announcePolite(message);
    }
  }, [announcePolite, announceAssertive]);

  return (
    <AriaLiveContext.Provider value={{ announce, announcePolite, announceAssertive }}>
      {children}
      {/* Visually hidden live regions */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {politeMessage}
      </div>
      <div
        role="alert"
        aria-live="assertive"
        aria-atomic="true"
        className="sr-only"
      >
        {assertiveMessage}
      </div>
    </AriaLiveContext.Provider>
  );
}

/**
 * Component for displaying price updates with ARIA live announcements.
 * Use for real-time price data that should be announced to screen readers.
 */
interface PriceDisplayProps {
  symbol: string;
  price: number;
  change?: number;
  formatPrice: (value: number) => string;
  className?: string;
}

export function AccessiblePriceDisplay({
  symbol,
  price,
  change,
  formatPrice,
  className,
}: PriceDisplayProps) {
  const changeText = change !== undefined
    ? change >= 0
      ? `up ${formatPrice(Math.abs(change))}`
      : `down ${formatPrice(Math.abs(change))}`
    : '';

  return (
    <span
      className={className}
      aria-label={`${symbol} price: ${formatPrice(price)}${changeText ? `, ${changeText}` : ''}`}
    >
      {formatPrice(price)}
    </span>
  );
}

