import { create } from 'zustand';
import { wsClient } from '@/lib/websocket';
import type { QuoteUpdate } from '@/types';

interface WebSocketState {
  isConnected: boolean;
  quotes: Map<string, QuoteUpdate>;
  subscribedSymbols: Set<string>;
  
  // Actions
  connect: () => Promise<void>;
  disconnect: () => void;
  subscribe: (symbols: string[]) => void;
  unsubscribe: (symbols: string[]) => void;
  getQuote: (symbol: string) => QuoteUpdate | undefined;
}

export const useWebSocketStore = create<WebSocketState>((set, get) => ({
  isConnected: false,
  quotes: new Map(),
  subscribedSymbols: new Set(),

  connect: async () => {
    try {
      await wsClient.connect();
      
      // Set up quote handler
      wsClient.on('quote', (data: QuoteUpdate) => {
        set((state) => {
          const newQuotes = new Map(state.quotes);
          newQuotes.set(data.symbol, data);
          return { quotes: newQuotes };
        });
      });

      set({ isConnected: true });
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      set({ isConnected: false });
    }
  },

  disconnect: () => {
    wsClient.disconnect();
    set({ isConnected: false, quotes: new Map() });
  },

  subscribe: (symbols: string[]) => {
    wsClient.subscribeToQuotes(symbols);
    set((state) => {
      const newSymbols = new Set(state.subscribedSymbols);
      symbols.forEach((s) => newSymbols.add(s));
      return { subscribedSymbols: newSymbols };
    });
  },

  unsubscribe: (symbols: string[]) => {
    wsClient.unsubscribeFromQuotes(symbols);
    set((state) => {
      const newSymbols = new Set(state.subscribedSymbols);
      symbols.forEach((s) => newSymbols.delete(s));
      return { subscribedSymbols: newSymbols };
    });
  },

  getQuote: (symbol: string) => {
    return get().quotes.get(symbol);
  },
}));

