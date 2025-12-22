import { useQuery } from '@tanstack/react-query';
import { marketDataApi } from '@/lib/api';
import { useWebSocketStore } from '@/store';
import { useEffect } from 'react';
import type { StockQuote } from '@/types';

interface UseQuoteOptions {
  enabled?: boolean;
  refetchInterval?: number | false;
  useWebSocket?: boolean;
}

export function useQuote(symbol: string, options: UseQuoteOptions = {}) {
  const { enabled = true, refetchInterval = 30000, useWebSocket = true } = options;
  
  const { subscribe, unsubscribe, getQuote, isConnected } = useWebSocketStore();
  const wsQuote = useWebSocketStore((state) => state.quotes.get(symbol));

  // Subscribe to WebSocket updates
  useEffect(() => {
    if (useWebSocket && symbol && isConnected) {
      subscribe([symbol]);
      return () => unsubscribe([symbol]);
    }
  }, [symbol, useWebSocket, isConnected, subscribe, unsubscribe]);

  // Fallback to REST API
  const query = useQuery({
    queryKey: ['quote', symbol],
    queryFn: async () => {
      const response = await marketDataApi.getQuote(symbol);
      return response.data;
    },
    enabled: enabled && !!symbol,
    refetchInterval: useWebSocket && isConnected ? false : refetchInterval,
    staleTime: 5000,
  });

  // Merge WebSocket data with REST data
  const data: StockQuote | undefined = wsQuote
    ? {
        symbol: wsQuote.symbol,
        price: wsQuote.price,
        change: wsQuote.change,
        change_pct: wsQuote.change_pct,
        volume: wsQuote.volume,
        timestamp: wsQuote.timestamp,
        open: query.data?.open ?? null,
        high: query.data?.high ?? null,
        low: query.data?.low ?? null,
        close: query.data?.close ?? null,
      }
    : query.data;

  return {
    data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
    isLive: useWebSocket && isConnected,
  };
}

export function useQuotes(symbols: string[], options: UseQuoteOptions = {}) {
  const { enabled = true, useWebSocket = true } = options;
  
  const { subscribe, unsubscribe, isConnected } = useWebSocketStore();
  const quotes = useWebSocketStore((state) => {
    const result: Record<string, StockQuote | undefined> = {};
    symbols.forEach((symbol) => {
      const wsQuote = state.quotes.get(symbol);
      if (wsQuote) {
        result[symbol] = {
          symbol: wsQuote.symbol,
          price: wsQuote.price,
          change: wsQuote.change,
          change_pct: wsQuote.change_pct,
          volume: wsQuote.volume,
          timestamp: wsQuote.timestamp,
          open: null,
          high: null,
          low: null,
          close: null,
        };
      }
    });
    return result;
  });

  useEffect(() => {
    if (useWebSocket && symbols.length > 0 && isConnected) {
      subscribe(symbols);
      return () => unsubscribe(symbols);
    }
  }, [symbols.join(','), useWebSocket, isConnected, subscribe, unsubscribe]);

  return {
    quotes,
    isLive: useWebSocket && isConnected,
  };
}

