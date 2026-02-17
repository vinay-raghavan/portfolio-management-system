'use client';

import { useMemo } from 'react';
import { useUIStore } from '@/store';

export interface ChartThemeColors {
  background: string;
  text: string;
  grid: string;
  border: string;
  profit: string;
  profitArea: string;
  loss: string;
  lossArea: string;
  volume: string;
  crosshair: string;
  sma20: string;
  sma50: string;
  sma200: string;
  ema: string;
  bollinger: string;
  rsi: string;
}

// Default colors (fallback)
const LIGHT_DEFAULTS: ChartThemeColors = {
  background: '#ffffff',
  text: '#374151',
  grid: '#e5e7eb',
  border: '#e5e7eb',
  profit: '#22c55e',
  profitArea: 'rgba(34, 197, 94, 0.2)',
  loss: '#ef4444',
  lossArea: 'rgba(239, 68, 68, 0.2)',
  volume: '#6366f1',
  crosshair: '#9ca3af',
  sma20: '#3b82f6',
  sma50: '#f59e0b',
  sma200: '#8b5cf6',
  ema: '#ec4899',
  bollinger: '#06b6d4',
  rsi: '#f97316',
};

const DARK_DEFAULTS: ChartThemeColors = {
  background: '#1a1a2e',
  text: '#d1d5db',
  grid: '#2d2d44',
  border: '#2d2d44',
  profit: '#4ade80',
  profitArea: 'rgba(74, 222, 128, 0.2)',
  loss: '#f87171',
  lossArea: 'rgba(248, 113, 113, 0.2)',
  volume: '#818cf8',
  crosshair: '#6b7280',
  sma20: '#60a5fa',
  sma50: '#fbbf24',
  sma200: '#a78bfa',
  ema: '#f472b6',
  bollinger: '#22d3ee',
  rsi: '#fb923c',
};

/**
 * Helper to resolve the actual theme (considering system preference).
 * Safe to call during render.
 */
function resolveTheme(theme: 'light' | 'dark' | 'system'): 'light' | 'dark' {
  if (theme === 'system') {
    if (typeof window !== 'undefined') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'light';
  }
  return theme;
}

/**
 * Hook that provides chart theme colors based on current app theme.
 * Uses default colors based on resolved theme (light/dark).
 */
export function useChartTheme(): {
  colors: ChartThemeColors;
  isDark: boolean;
  resolvedTheme: 'light' | 'dark';
} {
  const { theme } = useUIStore();

  // Resolve the theme and compute colors - all synchronous, no effects needed
  const result = useMemo(() => {
    const resolved = resolveTheme(theme);
    const colors = resolved === 'dark' ? DARK_DEFAULTS : LIGHT_DEFAULTS;
    return {
      colors,
      isDark: resolved === 'dark',
      resolvedTheme: resolved,
    };
  }, [theme]);

  return result;
}

