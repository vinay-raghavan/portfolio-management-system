'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { CandlestickChart } from '@/components/charts';
import { marketDataApi, analysisApi } from '@/lib/api';
import { calculateSMA, calculateEMA, calculateBollingerBands } from '@/lib/indicators';
import { formatCurrency, formatPercent, cn } from '@/lib/utils';
import { useUIStore } from '@/store';

const TIMEFRAMES = [
  { value: '1d', label: '1D', period: '5d', interval: '5m' },
  { value: '1w', label: '1W', period: '1mo', interval: '1h' },
  { value: '1m', label: '1M', period: '1mo', interval: '1d' },
  { value: '3m', label: '3M', period: '3mo', interval: '1d' },
  { value: '1y', label: '1Y', period: '1y', interval: '1wk' },
];

const INDICATOR_OPTIONS = [
  { value: 'sma_20', label: 'SMA 20', color: '#3b82f6' },
  { value: 'sma_50', label: 'SMA 50', color: '#f59e0b' },
  { value: 'ema_12', label: 'EMA 12', color: '#10b981' },
  { value: 'ema_26', label: 'EMA 26', color: '#ef4444' },
  { value: 'bb', label: 'Bollinger Bands', color: '#8b5cf6' },
];

export default function AnalysisPage() {
  const { selectedSymbol, setSelectedSymbol, chartInterval, setChartInterval, chartIndicators, toggleChartIndicator } = useUIStore();
  const [symbolInput, setSymbolInput] = useState(selectedSymbol || 'AAPL');

  const timeframe = TIMEFRAMES.find((t) => t.value === chartInterval) || TIMEFRAMES[2];

  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['history', selectedSymbol || symbolInput, timeframe.period, timeframe.interval],
    queryFn: () => marketDataApi.getHistory(selectedSymbol || symbolInput, timeframe.period, timeframe.interval).then((res) => res.data),
    enabled: !!(selectedSymbol || symbolInput),
  });

  const { data: quoteData } = useQuery({
    queryKey: ['quote', selectedSymbol || symbolInput],
    queryFn: () => marketDataApi.getQuote(selectedSymbol || symbolInput).then((res) => res.data),
    enabled: !!(selectedSymbol || symbolInput),
    refetchInterval: 30000,
  });

  const { data: analysisData } = useQuery({
    queryKey: ['analysis', selectedSymbol || symbolInput],
    queryFn: () => analysisApi.getAnalysis(selectedSymbol || symbolInput).then((res) => res.data),
    enabled: !!(selectedSymbol || symbolInput),
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

    if (chartIndicators.includes('sma_20')) {
      result.push({ type: 'sma', period: 20, color: '#3b82f6', data: calculateSMA(chartData, 20) });
    }
    if (chartIndicators.includes('sma_50')) {
      result.push({ type: 'sma', period: 50, color: '#f59e0b', data: calculateSMA(chartData, 50) });
    }
    if (chartIndicators.includes('ema_12')) {
      result.push({ type: 'ema', period: 12, color: '#10b981', data: calculateEMA(chartData, 12) });
    }
    if (chartIndicators.includes('ema_26')) {
      result.push({ type: 'ema', period: 26, color: '#ef4444', data: calculateEMA(chartData, 26) });
    }
    if (chartIndicators.includes('bb')) {
      const bb = calculateBollingerBands(chartData, 20, 2);
      result.push({ type: 'bb', period: 20, color: '#8b5cf6', data: bb.upper });
      result.push({ type: 'bb', period: 20, color: '#8b5cf6', data: bb.lower });
    }

    return result;
  }, [chartData, chartIndicators]);

  const handleSearch = () => {
    setSelectedSymbol(symbolInput.toUpperCase());
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Analysis</h1>
        <p className="text-muted-foreground">Technical analysis and charts</p>
      </div>

      {/* Symbol Search and Controls */}
      <div className="flex flex-wrap gap-4 items-center">
        <div className="flex gap-2">
          <Input
            value={symbolInput}
            onChange={(e) => setSymbolInput(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Enter symbol..."
            className="w-32"
          />
          <Button onClick={handleSearch}>
            <Search className="h-4 w-4" />
          </Button>
        </div>

        {/* Timeframe Selector */}
        <div className="flex gap-1">
          {TIMEFRAMES.map((tf) => (
            <Button
              key={tf.value}
              variant={chartInterval === tf.value ? 'default' : 'outline'}
              size="sm"
              onClick={() => setChartInterval(tf.value)}
            >
              {tf.label}
            </Button>
          ))}
        </div>

        {/* Indicator Toggles */}
        <Select value="" onValueChange={toggleChartIndicator}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Add Indicator" />
          </SelectTrigger>
          <SelectContent>
            {INDICATOR_OPTIONS.map((ind) => (
              <SelectItem key={ind.value} value={ind.value}>
                {chartIndicators.includes(ind.value) ? '✓ ' : ''}{ind.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Quote Info */}
      {quoteData && (
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center gap-6">
              <div>
                <h2 className="text-2xl font-bold">{selectedSymbol || symbolInput}</h2>
                <p className="text-3xl font-bold">{formatCurrency(quoteData.price)}</p>
              </div>
              <div className={cn('text-lg', (quoteData.change_pct ?? 0) >= 0 ? 'text-profit' : 'text-loss')}>
                {(quoteData.change ?? 0) >= 0 ? '+' : ''}{formatCurrency(quoteData.change ?? 0)}
                {' '}({formatPercent(quoteData.change_pct ?? 0)})
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Price Chart</CardTitle>
        </CardHeader>
        <CardContent>
          {historyLoading ? (
            <div className="h-96 flex items-center justify-center">
              <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
            </div>
          ) : chartData.length === 0 ? (
            <div className="h-96 flex items-center justify-center text-muted-foreground">
              No data available
            </div>
          ) : (
            <CandlestickChart data={chartData} indicators={indicators} height={400} showVolume />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

