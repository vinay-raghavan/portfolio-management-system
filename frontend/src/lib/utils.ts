import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const CURRENCY_LOCALES: Record<string, string> = {
  USD: 'en-US',
  INR: 'en-IN',
  EUR: 'de-DE',
  GBP: 'en-GB',
};

export function formatCurrency(value: number | string | null | undefined, currency = 'USD'): string {
  let numValue: number;
  if (typeof value === 'string') {
    numValue = parseFloat(value);
  } else if (typeof value === 'number') {
    numValue = value;
  } else {
    numValue = 0;
  }
  numValue = isFinite(numValue) ? numValue : 0;
  const locale = CURRENCY_LOCALES[currency] || 'en-US';
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numValue);
}

export function formatPercent(value: number | string | null | undefined): string {
  let numValue: number;
  if (typeof value === 'string') {
    numValue = parseFloat(value);
  } else if (typeof value === 'number') {
    numValue = value;
  } else {
    numValue = 0;
  }
  numValue = isFinite(numValue) ? numValue : 0;
  return new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numValue / 100);
}

export function formatNumber(value: number | null | undefined, decimals = 2): string {
  const numValue = typeof value === 'number' && isFinite(value) ? value : 0;
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(numValue);
}

export function formatCompactNumber(value: number | null | undefined): string {
  const numValue = typeof value === 'number' && isFinite(value) ? value : 0;
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    compactDisplay: 'short',
  }).format(numValue);
}

export function safeToFixed(value: number | string | null | undefined, decimals = 2): string {
  let numValue: number;
  if (typeof value === 'string') {
    numValue = parseFloat(value);
  } else if (typeof value === 'number') {
    numValue = value;
  } else {
    numValue = 0;
  }
  return isFinite(numValue) ? numValue.toFixed(decimals) : '0.00';
}

