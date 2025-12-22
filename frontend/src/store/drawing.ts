import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Time } from 'lightweight-charts';

export type DrawingToolType = 'none' | 'trendline' | 'horizontal' | 'ray' | 'rectangle';

export interface DrawingPoint {
  time: Time;
  price: number;
}

export interface Drawing {
  id: string;
  type: DrawingToolType;
  points: DrawingPoint[];
  color: string;
  lineWidth: number;
  symbol: string; // The symbol this drawing is associated with
}

interface DrawingState {
  // Current drawing tool
  activeTool: DrawingToolType;
  setActiveTool: (tool: DrawingToolType) => void;

  // Drawing color and width
  drawingColor: string;
  setDrawingColor: (color: string) => void;
  lineWidth: number;
  setLineWidth: (width: number) => void;

  // Saved drawings per symbol
  drawings: Drawing[];
  addDrawing: (drawing: Drawing) => void;
  removeDrawing: (id: string) => void;
  clearDrawings: (symbol?: string) => void;
  getDrawingsForSymbol: (symbol: string) => Drawing[];

  // Drawing in progress
  isDrawing: boolean;
  setIsDrawing: (isDrawing: boolean) => void;
  currentDrawingPoints: DrawingPoint[];
  addDrawingPoint: (point: DrawingPoint) => void;
  clearCurrentDrawing: () => void;
}

export const useDrawingStore = create<DrawingState>()(
  persist(
    (set, get) => ({
      activeTool: 'none',
      setActiveTool: (tool) => set({ activeTool: tool, isDrawing: false, currentDrawingPoints: [] }),

      drawingColor: '#2962FF',
      setDrawingColor: (color) => set({ drawingColor: color }),

      lineWidth: 2,
      setLineWidth: (width) => set({ lineWidth: width }),

      drawings: [],
      addDrawing: (drawing) =>
        set((state) => ({ drawings: [...state.drawings, drawing] })),
      removeDrawing: (id) =>
        set((state) => ({ drawings: state.drawings.filter((d) => d.id !== id) })),
      clearDrawings: (symbol) =>
        set((state) => ({
          drawings: symbol ? state.drawings.filter((d) => d.symbol !== symbol) : [],
        })),
      getDrawingsForSymbol: (symbol) => get().drawings.filter((d) => d.symbol === symbol),

      isDrawing: false,
      setIsDrawing: (isDrawing) => set({ isDrawing }),

      currentDrawingPoints: [],
      addDrawingPoint: (point) =>
        set((state) => ({ currentDrawingPoints: [...state.currentDrawingPoints, point] })),
      clearCurrentDrawing: () => set({ currentDrawingPoints: [], isDrawing: false }),
    }),
    {
      name: 'chart-drawings',
      partialize: (state) => ({ drawings: state.drawings }),
    }
  )
);

