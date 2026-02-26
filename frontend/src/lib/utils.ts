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

/**
 * Check if the current time is within a trading time window.
 * @param startTime - Start time in HH:MM:SS format
 * @param endTime - End time in HH:MM:SS format
 * @param timezone - IANA timezone string (e.g., 'Asia/Kolkata')
 * @param activeDays - Array of active day indices (0=Monday, 6=Sunday)
 * @returns true if current time is within the trading window
 */
export function isWithinTradingWindow(
  startTime: string | undefined,
  endTime: string | undefined,
  timezone: string = 'Asia/Kolkata',
  activeDays: number[] = [0, 1, 2, 3, 4]
): boolean {
  if (!startTime || !endTime) return true; // No window configured

  try {
    // Get current time in the specified timezone
    const now = new Date();
    const formatter = new Intl.DateTimeFormat('en-US', {
      timeZone: timezone,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
      weekday: 'short',
    });
    const parts = formatter.formatToParts(now);

    const hour = parseInt(parts.find(p => p.type === 'hour')?.value || '0');
    const minute = parseInt(parts.find(p => p.type === 'minute')?.value || '0');
    const second = parseInt(parts.find(p => p.type === 'second')?.value || '0');
    const weekdayStr = parts.find(p => p.type === 'weekday')?.value || 'Mon';

    // Convert weekday string to index (0=Monday, 6=Sunday)
    const weekdayMap: Record<string, number> = {
      'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6
    };
    const currentDay = weekdayMap[weekdayStr] ?? 0;

    // Check if current day is an active trading day
    if (!activeDays.includes(currentDay)) return false;

    // Convert times to seconds for comparison
    const [startH, startM, startS = '0'] = startTime.split(':');
    const [endH, endM, endS = '0'] = endTime.split(':');

    const currentSeconds = hour * 3600 + minute * 60 + second;
    const startSeconds = parseInt(startH) * 3600 + parseInt(startM) * 60 + parseInt(startS);
    const endSeconds = parseInt(endH) * 3600 + parseInt(endM) * 60 + parseInt(endS);

    return currentSeconds >= startSeconds && currentSeconds <= endSeconds;
  } catch {
    return true; // On error, assume within window
  }
}

