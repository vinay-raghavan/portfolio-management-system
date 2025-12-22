import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Currency = 'USD' | 'INR' | 'EUR' | 'GBP';

interface UIState {
  // Selected symbol for charts and analysis
  selectedSymbol: string | null;

  // Sidebar state
  sidebarCollapsed: boolean;

  // Theme (for future use)
  theme: 'light' | 'dark' | 'system';

  // Currency preference
  currency: Currency;

  // Chart preferences
  chartInterval: string;
  chartIndicators: string[];

  // Actions
  setSelectedSymbol: (symbol: string | null) => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  setCurrency: (currency: Currency) => void;
  setChartInterval: (interval: string) => void;
  toggleChartIndicator: (indicator: string) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      selectedSymbol: null,
      sidebarCollapsed: false,
      theme: 'system',
      currency: 'INR' as Currency,
      chartInterval: '1d',
      chartIndicators: ['sma_20', 'sma_50'],

      setSelectedSymbol: (symbol) => {
        set({ selectedSymbol: symbol });
      },

      toggleSidebar: () => {
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed }));
      },

      setSidebarCollapsed: (collapsed) => {
        set({ sidebarCollapsed: collapsed });
      },

      setTheme: (theme) => {
        set({ theme });
      },

      setCurrency: (currency) => {
        set({ currency });
      },

      setChartInterval: (interval) => {
        set({ chartInterval: interval });
      },

      toggleChartIndicator: (indicator) => {
        set((state) => {
          const indicators = state.chartIndicators.includes(indicator)
            ? state.chartIndicators.filter((i) => i !== indicator)
            : [...state.chartIndicators, indicator];
          return { chartIndicators: indicators };
        });
      },
    }),
    {
      name: 'ui-storage',
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
        currency: state.currency,
        chartInterval: state.chartInterval,
        chartIndicators: state.chartIndicators,
      }),
    }
  )
);

