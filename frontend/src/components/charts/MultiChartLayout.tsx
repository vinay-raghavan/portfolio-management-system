'use client';

import { useState, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Grid2x2, Grid3x3, Columns, Square, X, Maximize2, Minimize2, Search, Settings2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { CandlestickChart } from './CandlestickChart';
import { marketDataApi } from '@/lib/api';
import { calculateSMA, calculateEMA, calculateBollingerBands } from '@/lib/indicators';
import { cn } from '@/lib/utils';

type LayoutType = '1x1' | '2x1' | '2x2' | '3x2';

interface ChartPanelState {
  id: string;
  symbol: string;
  interval: string;
  indicators: string[];
}

interface MultiChartLayoutProps {
  defaultSymbols?: string[];
  className?: string;
}

const LAYOUTS: { type: LayoutType; icon: React.ElementType; label: string; panels: number }[] = [
  { type: '1x1', icon: Square, label: 'Single', panels: 1 },
  { type: '2x1', icon: Columns, label: '2 Charts', panels: 2 },
  { type: '2x2', icon: Grid2x2, label: '4 Charts', panels: 4 },
  { type: '3x2', icon: Grid3x3, label: '6 Charts', panels: 6 },
];

const TIMEFRAMES = [
  { value: '1d', label: '1D', period: '1d', interval: '5m' },
  { value: '5d', label: '5D', period: '5d', interval: '15m' },
  { value: '1m', label: '1M', period: '1mo', interval: '1d' },
  { value: '3m', label: '3M', period: '3mo', interval: '1d' },
  { value: '1y', label: '1Y', period: '1y', interval: '1d' },
];

const DEFAULT_SYMBOLS = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META'];

function createPanelState(id: string, symbol: string): ChartPanelState {
  return { id, symbol, interval: '1m', indicators: ['sma_20'] };
}

export function MultiChartLayout({ defaultSymbols = DEFAULT_SYMBOLS, className }: MultiChartLayoutProps) {
  const [layout, setLayout] = useState<LayoutType>('2x2');
  const [maximizedPanel, setMaximizedPanel] = useState<string | null>(null);
  const [panels, setPanels] = useState<ChartPanelState[]>(() =>
    defaultSymbols.slice(0, 6).map((symbol, i) => createPanelState(`panel-${i}`, symbol))
  );

  const layoutConfig = LAYOUTS.find((l) => l.type === layout)!;
  const visiblePanels = maximizedPanel
    ? panels.filter((p) => p.id === maximizedPanel)
    : panels.slice(0, layoutConfig.panels);

  const updatePanel = useCallback((panelId: string, updates: Partial<ChartPanelState>) => {
    setPanels((prev) => prev.map((p) => (p.id === panelId ? { ...p, ...updates } : p)));
  }, []);

  const gridClasses = useMemo(() => {
    if (maximizedPanel) return 'grid-cols-1';
    switch (layout) {
      case '1x1': return 'grid-cols-1';
      case '2x1': return 'grid-cols-1 md:grid-cols-2';
      case '2x2': return 'grid-cols-1 md:grid-cols-2';
      case '3x2': return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3';
      default: return 'grid-cols-1';
    }
  }, [layout, maximizedPanel]);

  return (
    <div className={cn('space-y-4', className)}>
      {/* Layout Selector */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm text-muted-foreground mr-2">Layout:</span>
        {LAYOUTS.map((l) => (
          <Button
            key={l.type}
            variant={layout === l.type ? 'default' : 'outline'}
            size="sm"
            onClick={() => { setLayout(l.type); setMaximizedPanel(null); }}
            title={l.label}
          >
            <l.icon className="h-4 w-4" />
          </Button>
        ))}
      </div>

      {/* Chart Grid */}
      <div className={cn('grid gap-4', gridClasses)}>
        {visiblePanels.map((panel) => (
          <ChartPanel
            key={panel.id}
            panel={panel}
            onUpdate={(updates) => updatePanel(panel.id, updates)}
            isMaximized={maximizedPanel === panel.id}
            onToggleMaximize={() => setMaximizedPanel(maximizedPanel === panel.id ? null : panel.id)}
            height={maximizedPanel ? 600 : layout === '1x1' ? 500 : 300}
          />
        ))}
      </div>
    </div>
  );
}

interface ChartPanelProps {
  panel: ChartPanelState;
  onUpdate: (updates: Partial<ChartPanelState>) => void;
  isMaximized: boolean;
  onToggleMaximize: () => void;
  height: number;
}

function ChartPanel({ panel, onUpdate, isMaximized, onToggleMaximize, height }: ChartPanelProps) {
  const [symbolInput, setSymbolInput] = useState(panel.symbol);

  const timeframe = TIMEFRAMES.find((t) => t.value === panel.interval) || TIMEFRAMES[2];

  const { data: historyData, isLoading } = useQuery({
    queryKey: ['history', panel.symbol, timeframe.period, timeframe.interval],
    queryFn: () => marketDataApi.getHistory(panel.symbol, timeframe.period, timeframe.interval).then((res) => res.data),
    enabled: !!panel.symbol,
  });

  const chartData = useMemo(() => {
    if (!historyData?.data) return [];
    return historyData.data.map((d) => ({
      time: d.date.split('T')[0],
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
      volume: d.volume,
    }));
  }, [historyData]);

  const indicators = useMemo(() => {
    if (chartData.length === 0) return [];
    const result: any[] = [];
    if (panel.indicators.includes('sma_20')) {
      result.push({ type: 'sma', period: 20, color: '#3b82f6', data: calculateSMA(chartData, 20) });
    }
    if (panel.indicators.includes('sma_50')) {
      result.push({ type: 'sma', period: 50, color: '#f59e0b', data: calculateSMA(chartData, 50) });
    }
    if (panel.indicators.includes('ema_12')) {
      result.push({ type: 'ema', period: 12, color: '#10b981', data: calculateEMA(chartData, 12) });
    }
    return result;
  }, [chartData, panel.indicators]);

  const handleSymbolSubmit = () => {
    if (symbolInput.trim()) {
      onUpdate({ symbol: symbolInput.toUpperCase() });
    }
  };

  return (
    <div className={cn(
      'border rounded-lg bg-card overflow-hidden',
      isMaximized && 'ring-2 ring-primary'
    )}>
      {/* Panel Header */}
      <div className="flex items-center gap-2 p-2 border-b bg-muted/50">
        <Input
          value={symbolInput}
          onChange={(e) => setSymbolInput(e.target.value.toUpperCase())}
          onKeyDown={(e) => e.key === 'Enter' && handleSymbolSubmit()}
          onBlur={handleSymbolSubmit}
          className="h-7 w-24 text-xs font-medium"
          placeholder="Symbol"
        />
        <Select value={panel.interval} onValueChange={(v) => onUpdate({ interval: v })}>
          <SelectTrigger className="h-7 w-20 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TIMEFRAMES.map((tf) => (
              <SelectItem key={tf.value} value={tf.value}>{tf.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="flex-1" />
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onToggleMaximize}>
          {isMaximized ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
        </Button>
      </div>

      {/* Chart Content */}
      <div className="p-2">
        {isLoading ? (
          <div className="flex items-center justify-center" style={{ height }}>
            <div className="animate-spin h-6 w-6 border-2 border-primary border-t-transparent rounded-full" />
          </div>
        ) : chartData.length === 0 ? (
          <div className="flex items-center justify-center text-muted-foreground text-sm" style={{ height }}>
            No data for {panel.symbol}
          </div>
        ) : (
          <CandlestickChart
            data={chartData}
            indicators={indicators}
            height={height}
            showVolume={isMaximized}
            symbol={panel.symbol}
          />
        )}
      </div>
    </div>
  );
}

