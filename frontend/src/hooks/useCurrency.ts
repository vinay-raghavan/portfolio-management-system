import { useCallback } from 'react';
import { useUIStore } from '@/store';
import { formatCurrency } from '@/lib/utils';

/**
 * Hook to format currency values using the user's preferred currency setting.
 */
export function useCurrency() {
  const currency = useUIStore((state) => state.currency);

  const format = useCallback(
    (value: number) => formatCurrency(value, currency),
    [currency]
  );

  return {
    currency,
    format,
  };
}

