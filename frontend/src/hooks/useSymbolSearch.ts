import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useDebounce } from './useDebounce';
import { marketDataApi, instrumentsApi } from '@/lib/api';
import type { SearchResult, Instrument } from '@/types';

interface UseSymbolSearchOptions {
  minLength?: number;
  debounceMs?: number;
  exchange?: string;
  limit?: number;
  useInstruments?: boolean; // Use instruments API instead of market data search
}

export function useSymbolSearch(options: UseSymbolSearchOptions = {}) {
  const {
    minLength = 2,
    debounceMs = 300,
    exchange,
    limit = 20,
    useInstruments = false,
  } = options;

  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, debounceMs);

  const shouldSearch = debouncedQuery.length >= minLength;

  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ['symbol-search', debouncedQuery, exchange, useInstruments],
    queryFn: async () => {
      if (useInstruments) {
        const response = await instrumentsApi.search(debouncedQuery, exchange, limit);
        // Map Instrument to SearchResult format
        return response.data.map((inst: Instrument): SearchResult => ({
          symbol: inst.symbol,
          name: inst.name,
          exchange: inst.exchange,
          type: inst.instrument_type,
        }));
      } else {
        const response = await marketDataApi.search(debouncedQuery);
        return response.data;
      }
    },
    enabled: shouldSearch,
    staleTime: 60000, // Cache for 1 minute
    placeholderData: (previousData) => previousData,
  });

  const clear = useCallback(() => {
    setQuery('');
  }, []);

  return {
    query,
    setQuery,
    results: data ?? [],
    isLoading: isLoading && shouldSearch,
    isFetching,
    error,
    clear,
    hasMinLength: query.length >= minLength,
  };
}

// Hook for searching with a pre-defined list of symbols
export function useFilteredSymbols(
  symbols: string[],
  searchQuery: string
): string[] {
  const query = searchQuery.toLowerCase().trim();

  if (!query) return symbols;

  return symbols.filter((symbol) =>
    symbol.toLowerCase().includes(query)
  );
}

