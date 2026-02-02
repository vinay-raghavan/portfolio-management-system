import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface PortfolioState {
  // Currently selected portfolio ID (null = all portfolios combined)
  selectedPortfolioId: string | null;
  
  // Actions
  setSelectedPortfolio: (portfolioId: string | null) => void;
}

export const usePortfolioStore = create<PortfolioState>()(
  persist(
    (set) => ({
      selectedPortfolioId: null,

      setSelectedPortfolio: (portfolioId) => {
        set({ selectedPortfolioId: portfolioId });
      },
    }),
    {
      name: 'portfolio-storage',
      partialize: (state) => ({
        selectedPortfolioId: state.selectedPortfolioId,
      }),
    }
  )
);

