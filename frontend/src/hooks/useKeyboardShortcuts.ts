'use client';

import { useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useTradingStore, useUIStore } from '@/store';

// Shortcut definitions
export interface Shortcut {
  key: string;
  ctrl?: boolean;
  meta?: boolean;
  shift?: boolean;
  alt?: boolean;
  description: string;
  category: 'navigation' | 'trading' | 'chart' | 'general';
  action: () => void;
}

export interface ShortcutGroup {
  category: string;
  shortcuts: { keys: string; description: string }[];
}

// Check if user is typing in an input field
function isTypingInInput(): boolean {
  const activeElement = document.activeElement;
  if (!activeElement) return false;
  
  const tagName = activeElement.tagName.toLowerCase();
  const isInput = tagName === 'input' || tagName === 'textarea' || tagName === 'select';
  const isContentEditable = activeElement.getAttribute('contenteditable') === 'true';
  
  return isInput || isContentEditable;
}

// Parse key combination string (e.g., "g+d", "ctrl+s")
function parseKeyCombo(combo: string): { key: string; modifiers: { ctrl?: boolean; meta?: boolean; shift?: boolean; alt?: boolean } } {
  const parts = combo.toLowerCase().split('+');
  const modifiers: { ctrl?: boolean; meta?: boolean; shift?: boolean; alt?: boolean } = {};
  let key = '';

  for (const part of parts) {
    switch (part) {
      case 'ctrl':
        modifiers.ctrl = true;
        break;
      case 'meta':
      case 'cmd':
        modifiers.meta = true;
        break;
      case 'shift':
        modifiers.shift = true;
        break;
      case 'alt':
        modifiers.alt = true;
        break;
      default:
        key = part;
    }
  }

  return { key, modifiers };
}

// Check if key event matches a shortcut
function matchesShortcut(
  event: KeyboardEvent,
  key: string,
  modifiers: { ctrl?: boolean; meta?: boolean; shift?: boolean; alt?: boolean }
): boolean {
  const eventKey = event.key.toLowerCase();
  
  // Handle special keys
  const normalizedKey = key === 'escape' ? 'escape' : key === 'esc' ? 'escape' : key;
  
  const keyMatch = eventKey === normalizedKey || event.code.toLowerCase() === `key${normalizedKey}`;
  const ctrlMatch = !!modifiers.ctrl === (event.ctrlKey || event.metaKey);
  const shiftMatch = !!modifiers.shift === event.shiftKey;
  const altMatch = !!modifiers.alt === event.altKey;

  return keyMatch && ctrlMatch && shiftMatch && altMatch;
}

// Sequence state for multi-key shortcuts (like g+d)
interface SequenceState {
  prefix: string | null;
  timestamp: number;
}

export function useKeyboardShortcuts(enabled: boolean = true) {
  const router = useRouter();
  const { openModal, closeModal, isOpen: isTradingModalOpen } = useTradingStore();
  const { toggleSidebar, setChartInterval } = useUIStore();
  const sequenceRef = useRef<SequenceState>({ prefix: null, timestamp: 0 });
  const helpModalRef = useRef<{ open: () => void } | null>(null);

  // Register help modal ref for opening via shortcut
  const registerHelpModal = useCallback((ref: { open: () => void } | null) => {
    helpModalRef.current = ref;
  }, []);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;
      
      // Skip if typing in input
      if (isTypingInInput()) return;

      const key = event.key.toLowerCase();
      const now = Date.now();
      const sequence = sequenceRef.current;

      // Clear sequence if too much time has passed (500ms)
      if (sequence.prefix && now - sequence.timestamp > 500) {
        sequenceRef.current = { prefix: null, timestamp: 0 };
      }

      // Handle ESC - close modals
      if (key === 'escape') {
        if (isTradingModalOpen) {
          closeModal();
          event.preventDefault();
          return;
        }
        // Reset sequence
        sequenceRef.current = { prefix: null, timestamp: 0 };
        return;
      }

      // Handle "?" for help modal
      if (key === '?' || (event.shiftKey && key === '/')) {
        helpModalRef.current?.open();
        event.preventDefault();
        return;
      }

      // Handle G prefix for navigation shortcuts
      if (key === 'g' && !sequence.prefix) {
        sequenceRef.current = { prefix: 'g', timestamp: now };
        event.preventDefault();
        return;
      }

      // Handle G+X navigation sequences
      if (sequence.prefix === 'g') {
        sequenceRef.current = { prefix: null, timestamp: 0 };
        event.preventDefault();

        switch (key) {
          case 'd':
            router.push('/dashboard');
            break;
          case 'p':
            router.push('/portfolio');
            break;
          case 'a':
            router.push('/analysis');
            break;
          case 's':
            router.push('/signals');
            break;
          case 'o':
            router.push('/orders');
            break;
          case 'w':
            router.push('/watchlist');
            break;
          case 't':
            router.push('/algo');
            break;
          case 'b':
            router.push('/backtest');
            break;
          case ',':
            router.push('/settings');
            break;
        }
        return;
      }

      // Trading shortcuts (single key)
      switch (key) {
        case 'n':
          // New order
          openModal();
          event.preventDefault();
          break;
        case 'b':
          // Focus buy
          openModal({ side: 'BUY' });
          event.preventDefault();
          break;
        // Note: 's' is used for sell only when not in G sequence
        // Handled above in G sequence check
      }

      // Sidebar toggle with [
      if (key === '[') {
        toggleSidebar();
        event.preventDefault();
        return;
      }

      // Chart timeframe shortcuts (1-9)
      if (/^[1-9]$/.test(key) && !event.ctrlKey && !event.metaKey) {
        const timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M'];
        const index = parseInt(key) - 1;
        if (index < timeframes.length) {
          setChartInterval(timeframes[index]);
          event.preventDefault();
        }
        return;
      }
    },
    [enabled, router, openModal, closeModal, isTradingModalOpen, toggleSidebar, setChartInterval]
  );

  useEffect(() => {
    if (!enabled) return;

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [enabled, handleKeyDown]);

  return { registerHelpModal };
}

// Get all shortcuts for display in help modal
export function getShortcutGroups(): ShortcutGroup[] {
  return [
    {
      category: 'Navigation',
      shortcuts: [
        { keys: 'G then D', description: 'Go to Dashboard' },
        { keys: 'G then P', description: 'Go to Portfolio' },
        { keys: 'G then A', description: 'Go to Analysis' },
        { keys: 'G then S', description: 'Go to Signals' },
        { keys: 'G then O', description: 'Go to Orders' },
        { keys: 'G then W', description: 'Go to Watchlist' },
        { keys: 'G then T', description: 'Go to Algo Trading' },
        { keys: 'G then B', description: 'Go to Backtest' },
        { keys: 'G then ,', description: 'Go to Settings' },
        { keys: '[', description: 'Toggle sidebar' },
      ],
    },
    {
      category: 'Trading',
      shortcuts: [
        { keys: 'N', description: 'New order' },
        { keys: 'B', description: 'Quick buy order' },
        { keys: 'ESC', description: 'Close modal / Cancel' },
      ],
    },
    {
      category: 'Chart',
      shortcuts: [
        { keys: '1-9', description: 'Switch timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M)' },
      ],
    },
    {
      category: 'General',
      shortcuts: [
        { keys: '?', description: 'Show keyboard shortcuts' },
      ],
    },
  ];
}

