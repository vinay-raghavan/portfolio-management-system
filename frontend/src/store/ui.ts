import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Currency = 'USD' | 'INR' | 'EUR' | 'GBP';

// Available market indices
export const AVAILABLE_INDICES = [
  // Indian Indices
  { symbol: '^NSEI', name: 'NIFTY 50', market: 'IN' },
  { symbol: '^NSEBANK', name: 'BANK NIFTY', market: 'IN' },
  { symbol: '^BSESN', name: 'SENSEX', market: 'IN' },
  { symbol: '^NSMIDCP', name: 'NIFTY MIDCAP', market: 'IN' },
  { symbol: '^CNXIT', name: 'NIFTY IT', market: 'IN' },
  { symbol: '^CNXPHARMA', name: 'NIFTY PHARMA', market: 'IN' },
  // US Indices
  { symbol: '^GSPC', name: 'S&P 500', market: 'US' },
  { symbol: '^DJI', name: 'DOW JONES', market: 'US' },
  { symbol: '^IXIC', name: 'NASDAQ', market: 'US' },
  { symbol: '^RUT', name: 'RUSSELL 2000', market: 'US' },
] as const;

export type MarketIndex = typeof AVAILABLE_INDICES[number];

// Default selected indices
const DEFAULT_SELECTED_INDICES = ['^NSEI', '^NSEBANK', '^BSESN', '^NSMIDCP'];

// Comparison groups for chart comparison feature
export interface ComparisonGroup {
  id: string;
  name: string;
  symbols: string[];
  indexComparison?: string | null;
}

const DEFAULT_COMPARISON_GROUPS: ComparisonGroup[] = [
  { id: 'banking', name: 'Banking', symbols: ['HDFCBANK', 'ICICIBANK', 'SBIN', 'KOTAKBANK'], indexComparison: 'NIFTYBANK' },
  { id: 'it', name: 'IT Sector', symbols: ['TCS', 'INFY', 'WIPRO', 'HCLTECH'], indexComparison: 'NIFTY50' },
  { id: 'auto', name: 'Auto', symbols: ['MARUTI', 'TATAMOTORS', 'M&M', 'BAJAJ-AUTO'], indexComparison: 'NIFTY50' },
];

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

  // Market indices preferences
  selectedMarketIndices: string[];

  // Comparison groups for chart comparison
  comparisonGroups: ComparisonGroup[];

  // Actions
  setSelectedSymbol: (symbol: string | null) => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  setCurrency: (currency: Currency) => void;
  setChartInterval: (interval: string) => void;
  toggleChartIndicator: (indicator: string) => void;
  toggleMarketIndex: (symbol: string) => void;
  setMarketIndices: (symbols: string[]) => void;
  addComparisonGroup: (group: ComparisonGroup) => void;
  updateComparisonGroup: (id: string, updates: Partial<ComparisonGroup>) => void;
  deleteComparisonGroup: (id: string) => void;
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
      selectedMarketIndices: DEFAULT_SELECTED_INDICES,
      comparisonGroups: DEFAULT_COMPARISON_GROUPS,

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

      toggleMarketIndex: (symbol) => {
        set((state) => {
          const indices = state.selectedMarketIndices.includes(symbol)
            ? state.selectedMarketIndices.filter((s) => s !== symbol)
            : [...state.selectedMarketIndices, symbol];
          return { selectedMarketIndices: indices };
        });
      },

      setMarketIndices: (symbols) => {
        set({ selectedMarketIndices: symbols });
      },

      addComparisonGroup: (group) => {
        set((state) => ({
          comparisonGroups: [...state.comparisonGroups, group],
        }));
      },

      updateComparisonGroup: (id, updates) => {
        set((state) => ({
          comparisonGroups: state.comparisonGroups.map((g) =>
            g.id === id ? { ...g, ...updates } : g
          ),
        }));
      },

      deleteComparisonGroup: (id) => {
        set((state) => ({
          comparisonGroups: state.comparisonGroups.filter((g) => g.id !== id),
        }));
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
        selectedMarketIndices: state.selectedMarketIndices,
        comparisonGroups: state.comparisonGroups,
      }),
    }
  )
);

