import { create } from 'zustand';
import type { OrderSide, OrderType, ProductType } from '@/types';

interface TradingFormState {
  symbol: string;
  side: OrderSide;
  orderType: OrderType;
  quantity: number;
  price: number | null;
  stopLoss: number | null;
  takeProfit: number | null;
  productType: ProductType;
}

interface TradingModalState {
  isOpen: boolean;
  formState: TradingFormState;
  
  // Actions
  openModal: (initialState?: Partial<TradingFormState>) => void;
  closeModal: () => void;
  updateForm: (updates: Partial<TradingFormState>) => void;
  resetForm: () => void;
  setSymbol: (symbol: string) => void;
  setSide: (side: OrderSide) => void;
  quickBuy: (symbol: string, quantity?: number) => void;
  quickSell: (symbol: string, quantity?: number) => void;
}

const defaultFormState: TradingFormState = {
  symbol: '',
  side: 'BUY',
  orderType: 'MARKET',
  quantity: 1,
  price: null,
  stopLoss: null,
  takeProfit: null,
  productType: 'DELIVERY',
};

export const useTradingStore = create<TradingModalState>((set) => ({
  isOpen: false,
  formState: { ...defaultFormState },

  openModal: (initialState) => {
    set((state) => ({
      isOpen: true,
      formState: initialState
        ? { ...state.formState, ...initialState }
        : state.formState,
    }));
  },

  closeModal: () => {
    set({ isOpen: false });
  },

  updateForm: (updates) => {
    set((state) => ({
      formState: { ...state.formState, ...updates },
    }));
  },

  resetForm: () => {
    set({ formState: { ...defaultFormState } });
  },

  setSymbol: (symbol) => {
    set((state) => ({
      formState: { ...state.formState, symbol },
    }));
  },

  setSide: (side) => {
    set((state) => ({
      formState: { ...state.formState, side },
    }));
  },

  quickBuy: (symbol, quantity = 1) => {
    set({
      isOpen: true,
      formState: {
        ...defaultFormState,
        symbol,
        side: 'BUY',
        quantity,
      },
    });
  },

  quickSell: (symbol, quantity = 1) => {
    set({
      isOpen: true,
      formState: {
        ...defaultFormState,
        symbol,
        side: 'SELL',
        quantity,
      },
    });
  },
}));

