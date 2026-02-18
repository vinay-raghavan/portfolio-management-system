'use client';

import { useEffect, useRef, useMemo, useState, useCallback } from 'react';
import { useQueries } from '@tanstack/react-query';
import {
  createChart,
  ColorType,
  CrosshairMode,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type Time,
} from 'lightweight-charts';
import { Plus, X, TrendingUp, Eye, EyeOff, RefreshCw, Save, FolderOpen, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { marketDataApi } from '@/lib/api';
import { useUIStore, type ComparisonGroup } from '@/store';
import { useChartTheme } from '@/hooks';
import { cn } from '@/lib/utils';

// Symbol colors for comparison
const SYMBOL_COLORS = [
  '#3b82f6', // blue
  '#ef4444', // red
  '#22c55e', // green
  '#f59e0b', // amber
  '#8b5cf6', // violet
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#f97316', // orange
];

interface ComparisonSymbol {
  symbol: string;
  color: string;
  visible: boolean;
}

interface ComparisonChartProps {
  initialSymbols?: string[];
  height?: number;
  className?: string;
}

const TIMEFRAMES = [
  { value: '1W', label: '1 Week', period: '7d', interval: '1d' },
  { value: '1M', label: '1 Month', period: '1mo', interval: '1d' },
  { value: '3M', label: '3 Months', period: '3mo', interval: '1d' },
  { value: '6M', label: '6 Months', period: '6mo', interval: '1d' },
  { value: '1Y', label: '1 Year', period: '1y', interval: '1d' },
  { value: '2Y', label: '2 Years', period: '2y', interval: '1wk' },
];

// Yahoo Finance index symbols for Indian indices
const INDEX_SYMBOLS = [
  { value: '^NSEI', label: 'NIFTY 50' },
  { value: '^NSEBANK', label: 'Bank NIFTY' },
  { value: '^BSESN', label: 'Sensex' },
];

export function ComparisonChart({
  initialSymbols = [],
  height = 400,
  className,
}: ComparisonChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesMapRef = useRef<Map<string, ISeriesApi<'Line'>>>(new Map());

  // Get theme-aware chart colors
  const { colors } = useChartTheme();

  const [symbols, setSymbols] = useState<ComparisonSymbol[]>(() =>
    initialSymbols.slice(0, 8).map((s, i) => ({
      symbol: s.toUpperCase(),
      color: SYMBOL_COLORS[i % SYMBOL_COLORS.length],
      visible: true,
    }))
  );
  const [symbolInput, setSymbolInput] = useState('');
  const [timeframe, setTimeframe] = useState('3M');
  const [showNormalized, setShowNormalized] = useState(true);
  const [indexComparison, setIndexComparison] = useState<string | null>(null);
  const [groupName, setGroupName] = useState('');
  const [savePopoverOpen, setSavePopoverOpen] = useState(false);

  // Comparison groups from store
  const { comparisonGroups, addComparisonGroup, deleteComparisonGroup } = useUIStore();

  const activeTimeframe = TIMEFRAMES.find((t) => t.value === timeframe) || TIMEFRAMES[2];

  // Load a saved comparison group
  const loadGroup = useCallback((group: ComparisonGroup) => {
    setSymbols(
      group.symbols.slice(0, 8).map((s, i) => ({
        symbol: s.toUpperCase(),
        color: SYMBOL_COLORS[i % SYMBOL_COLORS.length],
        visible: true,
      }))
    );
    setIndexComparison(group.indexComparison || null);
  }, []);

  // Save current comparison as a group
  const saveAsGroup = useCallback(() => {
    if (!groupName.trim() || symbols.length === 0) return;
    const id = `custom-${Date.now()}`;
    addComparisonGroup({
      id,
      name: groupName.trim(),
      symbols: symbols.map((s) => s.symbol),
      indexComparison,
    });
    setGroupName('');
    setSavePopoverOpen(false);
  }, [groupName, symbols, indexComparison, addComparisonGroup]);

  // Fetch data for all symbols
  const allSymbols = useMemo(() => {
    const syms = symbols.filter((s) => s.visible).map((s) => s.symbol);
    if (indexComparison) syms.push(indexComparison);
    return syms;
  }, [symbols, indexComparison]);

  const queries = useQueries({
    queries: allSymbols.map((symbol) => ({
      queryKey: ['comparison-history', symbol, activeTimeframe.period, activeTimeframe.interval],
      queryFn: () => marketDataApi.getHistory(symbol, activeTimeframe.period, activeTimeframe.interval).then((res) => res.data),
      enabled: !!symbol,
      staleTime: 5 * 60 * 1000,
    })),
  });

  const isLoading = queries.some((q) => q.isLoading);
  const hasData = queries.some((q) => q.data?.data?.length);

  // Normalize data to percentage change from first value
  const normalizeData = useCallback((data: { date: string; close: number }[]): LineData<Time>[] => {
    if (!data.length) return [];
    const baseValue = data[0].close;
    return data.map((d) => ({
      time: d.date.split('T')[0] as Time,
      value: showNormalized ? ((d.close - baseValue) / baseValue) * 100 : d.close,
    }));
  }, [showNormalized]);

  const addSymbol = useCallback(() => {
    const sym = symbolInput.trim().toUpperCase();
    if (!sym || symbols.find((s) => s.symbol === sym)) {
      setSymbolInput('');
      return;
    }
    if (symbols.length >= 8) return;

    setSymbols((prev) => [
      ...prev,
      { symbol: sym, color: SYMBOL_COLORS[prev.length % SYMBOL_COLORS.length], visible: true },
    ]);
    setSymbolInput('');
  }, [symbolInput, symbols]);

  const removeSymbol = useCallback((symbol: string) => {
    setSymbols((prev) => prev.filter((s) => s.symbol !== symbol));
  }, []);

  const toggleSymbol = useCallback((symbol: string) => {
    setSymbols((prev) => prev.map((s) => (s.symbol === symbol ? { ...s, visible: !s.visible } : s)));
  }, []);

  // Initialize chart with theme-aware colors
  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: colors.text },
      grid: { vertLines: { color: colors.grid }, horzLines: { color: colors.grid } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: colors.border },
      timeScale: { borderColor: colors.border, timeVisible: true },
    });
    chartRef.current = chart;
    const handleResize = () => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth });
    };
    window.addEventListener('resize', handleResize);
    return () => { window.removeEventListener('resize', handleResize); chart.remove(); };
  }, [height, colors]);

  // Update series data when queries change
  useEffect(() => {
    if (!chartRef.current) return;

    // Remove old series
    seriesMapRef.current.forEach((series) => {
      try {
        chartRef.current?.removeSeries(series);
      } catch {
        // Series may already be removed
      }
    });
    seriesMapRef.current.clear();

    // Create series for each symbol
    queries.forEach((query, index) => {
      if (!query.data?.data?.length) return;

      const symbol = allSymbols[index];
      const symbolConfig = symbols.find((s) => s.symbol === symbol);
      const isIndex = symbol === indexComparison;
      const color = isIndex ? '#fbbf24' : symbolConfig?.color || SYMBOL_COLORS[index];

      const series = chartRef.current!.addSeries(LineSeries, {
        color,
        lineWidth: isIndex ? 1 : 2,
        priceFormat: showNormalized
          ? { type: 'custom', formatter: (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}%` }
          : { type: 'price', precision: 2, minMove: 0.01 },
        title: symbol,
      });

      const lineData = normalizeData(query.data.data);
      series.setData(lineData);
      seriesMapRef.current.set(symbol, series);
    });

    chartRef.current?.timeScale().fitContent();
  }, [queries, allSymbols, symbols, indexComparison, showNormalized, normalizeData]);

  return (
    <Card className={cn('', className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Symbol Comparison
          </CardTitle>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Switch id="normalized" checked={showNormalized} onCheckedChange={setShowNormalized} />
              <Label htmlFor="normalized" className="text-sm">Normalized %</Label>
            </div>
            <Select value={timeframe} onValueChange={setTimeframe}>
              <SelectTrigger className="w-24">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TIMEFRAMES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Saved Groups */}
        {comparisonGroups.length > 0 && (
          <div className="flex items-center gap-2 mt-3 flex-wrap">
            <span className="text-sm text-muted-foreground">Quick Load:</span>
            {comparisonGroups.map((group) => (
              <Badge
                key={group.id}
                variant="secondary"
                className="cursor-pointer hover:bg-secondary/80 gap-1"
              >
                <button onClick={() => loadGroup(group)} className="flex items-center gap-1">
                  <FolderOpen className="h-3 w-3" />
                  {group.name}
                </button>
                {!group.id.startsWith('banking') && !group.id.startsWith('it') && !group.id.startsWith('auto') && (
                  <button onClick={() => deleteComparisonGroup(group.id)} className="ml-1 hover:text-destructive">
                    <Trash2 className="h-3 w-3" />
                  </button>
                )}
              </Badge>
            ))}
          </div>
        )}

        {/* Symbol Input */}
        <div className="flex gap-2 mt-3 flex-wrap">
          <Input
            placeholder="Add symbol (e.g., RELIANCE)"
            value={symbolInput}
            onChange={(e) => setSymbolInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addSymbol()}
            className="max-w-xs"
          />
          <Button size="sm" onClick={addSymbol} disabled={symbols.length >= 8}>
            <Plus className="h-4 w-4 mr-1" /> Add
          </Button>
          <Select value={indexComparison || 'none'} onValueChange={(v) => setIndexComparison(v === 'none' ? null : v)}>
            <SelectTrigger className="w-36">
              <SelectValue placeholder="Compare Index" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">None</SelectItem>
              {INDEX_SYMBOLS.map((idx) => (
                <SelectItem key={idx.value} value={idx.value}>{idx.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Popover open={savePopoverOpen} onOpenChange={setSavePopoverOpen}>
            <PopoverTrigger asChild>
              <Button size="sm" variant="outline" disabled={symbols.length === 0}>
                <Save className="h-4 w-4 mr-1" /> Save Group
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-64">
              <div className="space-y-2">
                <Label htmlFor="group-name">Group Name</Label>
                <Input
                  id="group-name"
                  placeholder="e.g., My Favorites"
                  value={groupName}
                  onChange={(e) => setGroupName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && saveAsGroup()}
                />
                <Button size="sm" onClick={saveAsGroup} disabled={!groupName.trim()} className="w-full">
                  Save
                </Button>
              </div>
            </PopoverContent>
          </Popover>
        </div>

        {/* Symbol Tags */}
        <div className="flex flex-wrap gap-2 mt-3">
          {symbols.map((s) => (
            <Badge
              key={s.symbol}
              variant={s.visible ? 'default' : 'outline'}
              style={{ backgroundColor: s.visible ? s.color : 'transparent', borderColor: s.color }}
              className="cursor-pointer gap-1"
            >
              <button onClick={() => toggleSymbol(s.symbol)} className="flex items-center gap-1">
                {s.visible ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3" />}
                {s.symbol}
              </button>
              <button onClick={() => removeSymbol(s.symbol)} className="ml-1 hover:text-destructive">
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
          {indexComparison && (
            <Badge variant="outline" className="border-yellow-500 text-yellow-500">
              <TrendingUp className="h-3 w-3 mr-1" />
              {INDEX_SYMBOLS.find((i) => i.value === indexComparison)?.label || indexComparison}
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center" style={{ height }}>
            <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : !hasData && symbols.length === 0 ? (
          <div className="flex items-center justify-center text-muted-foreground text-sm" style={{ height }}>
            Add symbols to compare their performance
          </div>
        ) : (
          <div ref={containerRef} style={{ height }} />
        )}
      </CardContent>
    </Card>
  );
}

