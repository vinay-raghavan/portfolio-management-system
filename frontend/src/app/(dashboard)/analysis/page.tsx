'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, TrendingUp, TrendingDown, Building2, BarChart3, Target, Activity } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { CandlestickChart, DrawingToolbar } from '@/components/charts';
import { QuickTradePanel } from '@/components/trading';
import { BrandedSpinner, SkeletonChart } from '@/components/shared';
import { marketDataApi, analysisApi } from '@/lib/api';
import { calculateSMA, calculateEMA, calculateBollingerBands } from '@/lib/indicators';
import { formatPercent, formatCompactNumber, safeToFixed, cn } from '@/lib/utils';
import { useUIStore, useTradingStore } from '@/store';
import { useCurrency } from '@/hooks';

const TIMEFRAMES = [
  { value: '1d', label: '1D', period: '1d', interval: '5m', isIntraday: true },
  { value: '5d', label: '5D', period: '5d', interval: '15m', isIntraday: true },
  { value: '1w', label: '1W', period: '5d', interval: '30m', isIntraday: true },
  { value: '1m', label: '1M', period: '1mo', interval: '1d', isIntraday: false },
  { value: '3m', label: '3M', period: '3mo', interval: '1d', isIntraday: false },
  { value: '6m', label: '6M', period: '6mo', interval: '1d', isIntraday: false },
  { value: '1y', label: '1Y', period: '1y', interval: '1d', isIntraday: false },
  { value: '5y', label: '5Y', period: '5y', interval: '1wk', isIntraday: false },
];

const GRANULARITY_OPTIONS = [
  { value: '1m', label: '1 min' },
  { value: '5m', label: '5 min' },
  { value: '15m', label: '15 min' },
  { value: '30m', label: '30 min' },
  { value: '1h', label: '1 hour' },
  { value: '1d', label: '1 day' },
  { value: '1wk', label: '1 week' },
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
  const { format: formatPrice, currency } = useCurrency();
  const [symbolInput, setSymbolInput] = useState(selectedSymbol || 'AAPL');
  const [customGranularity, setCustomGranularity] = useState<string | null>(null);

  const timeframe = TIMEFRAMES.find((t) => t.value === chartInterval) || TIMEFRAMES[3];
  const currentSymbol = selectedSymbol || symbolInput;

  // Use custom granularity if set, otherwise use timeframe default
  const effectiveInterval = customGranularity || timeframe.interval;

  // Get valid granularity options based on the selected timeframe
  const validGranularityOptions = useMemo(() => {
    // For intraday periods, only allow minute/hour intervals
    if (timeframe.period === '1d') {
      return GRANULARITY_OPTIONS.filter(g => ['1m', '5m', '15m', '30m'].includes(g.value));
    }
    if (timeframe.period === '5d') {
      return GRANULARITY_OPTIONS.filter(g => ['5m', '15m', '30m', '1h'].includes(g.value));
    }
    if (timeframe.period === '1mo') {
      return GRANULARITY_OPTIONS.filter(g => ['30m', '1h', '1d'].includes(g.value));
    }
    if (timeframe.period === '3mo' || timeframe.period === '6mo') {
      return GRANULARITY_OPTIONS.filter(g => ['1h', '1d'].includes(g.value));
    }
    if (timeframe.period === '1y' || timeframe.period === '2y') {
      return GRANULARITY_OPTIONS.filter(g => ['1d', '1wk'].includes(g.value));
    }
    // For longer periods
    return GRANULARITY_OPTIONS.filter(g => ['1d', '1wk'].includes(g.value));
  }, [timeframe.period]);

  // Reset custom granularity when timeframe changes if it's not valid
  useMemo(() => {
    if (customGranularity && !validGranularityOptions.find(g => g.value === customGranularity)) {
      setCustomGranularity(null);
    }
  }, [validGranularityOptions, customGranularity]);

  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['history', currentSymbol, timeframe.period, effectiveInterval],
    queryFn: () => marketDataApi.getHistory(currentSymbol, timeframe.period, effectiveInterval).then((res) => res.data),
    enabled: !!currentSymbol,
  });

  const { data: quoteData } = useQuery({
    queryKey: ['quote', currentSymbol],
    queryFn: () => marketDataApi.getQuote(currentSymbol).then((res) => res.data),
    enabled: !!currentSymbol,
    refetchInterval: 30000,
  });

  const { data: analysisData } = useQuery({
    queryKey: ['analysis', currentSymbol],
    queryFn: () => analysisApi.getAnalysis(currentSymbol).then((res) => res.data),
    enabled: !!currentSymbol,
  });

  const { data: stockInfo } = useQuery({
    queryKey: ['stockInfo', currentSymbol],
    queryFn: () => analysisApi.getStockInfo(currentSymbol).then((res) => res.data),
    enabled: !!currentSymbol,
  });

  // Check if we're using intraday intervals
  const isIntraday = ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h'].includes(effectiveInterval);

  const chartData = useMemo(() => {
    if (!historyData?.data) return [];
    return historyData.data.map((d) => {
      // For intraday data, we need to use full timestamp as Unix time
      // lightweight-charts expects time as either "YYYY-MM-DD" string or Unix timestamp (seconds)
      let time: string | number;
      if (isIntraday && d.date.includes('T')) {
        // Convert ISO string to Unix timestamp (seconds)
        time = Math.floor(new Date(d.date).getTime() / 1000);
      } else {
        // Daily data - use date string
        time = d.date.split('T')[0];
      }
      return {
        time,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
        volume: d.volume,
      };
    });
  }, [historyData, isIntraday]);

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
              onClick={() => {
                setChartInterval(tf.value);
                setCustomGranularity(null); // Reset granularity when changing timeframe
              }}
            >
              {tf.label}
            </Button>
          ))}
        </div>

        {/* Granularity Selector */}
        <Select
          value={customGranularity || effectiveInterval}
          onValueChange={(val) => setCustomGranularity(val)}
        >
          <SelectTrigger className="w-32">
            <SelectValue placeholder="Granularity" />
          </SelectTrigger>
          <SelectContent>
            {validGranularityOptions.map((g) => (
              <SelectItem key={g.value} value={g.value}>
                {g.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

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

      {/* Stock Header with Quote Info */}
      {(quoteData || stockInfo) && (
        <Card>
          <CardContent className="py-6">
            <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h2 className="text-2xl font-bold">{currentSymbol}</h2>
                  {stockInfo?.exchange && (
                    <span className="text-xs bg-muted px-2 py-1 rounded">{stockInfo.exchange}</span>
                  )}
                </div>
                {stockInfo?.name && (
                  <p className="text-muted-foreground mb-2">{stockInfo.name}</p>
                )}
                <div className="flex items-center gap-4 flex-wrap">
                  <div className="flex items-baseline gap-4">
                    <p className="text-3xl font-bold">{formatPrice(quoteData?.price ?? stockInfo?.current_price ?? 0)}</p>
                    {quoteData && (
                      <div className={cn('text-lg font-medium', (quoteData.change_pct ?? 0) >= 0 ? 'text-profit' : 'text-loss')}>
                        {(quoteData.change ?? 0) >= 0 ? '+' : ''}{formatPrice(quoteData.change ?? 0)}
                        {' '}({formatPercent(quoteData.change_pct ?? 0)})
                      </div>
                    )}
                  </div>
                  {/* Quick Trade Buttons */}
                  <div className="flex gap-2 ml-auto md:ml-4">
                    <Button
                      size="sm"
                      className="bg-profit hover:bg-profit/90"
                      onClick={() => useTradingStore.getState().quickBuy(currentSymbol)}
                    >
                      Buy
                    </Button>
                    <Button
                      size="sm"
                      className="bg-loss hover:bg-loss/90"
                      onClick={() => useTradingStore.getState().quickSell(currentSymbol)}
                    >
                      Sell
                    </Button>
                  </div>
                </div>
                {stockInfo && (
                  <div className="flex flex-wrap gap-4 mt-3 text-sm text-muted-foreground">
                    {stockInfo.sector && (
                      <span className="flex items-center gap-1">
                        <Building2 className="h-4 w-4" />
                        {stockInfo.sector}
                      </span>
                    )}
                    {stockInfo.industry && <span>• {stockInfo.industry}</span>}
                  </div>
                )}
              </div>

              {/* Day Range */}
              {stockInfo?.day_low && stockInfo?.day_high && (
                <div className="w-full md:w-64">
                  <div className="text-xs text-muted-foreground mb-1">Day Range</div>
                  <div className="flex items-center gap-2 text-sm">
                    <span>{formatPrice(stockInfo.day_low)}</span>
                    <Progress
                      value={((quoteData?.price ?? stockInfo.current_price ?? stockInfo.day_low) - stockInfo.day_low) / (stockInfo.day_high - stockInfo.day_low) * 100}
                      className="flex-1 h-2"
                    />
                    <span>{formatPrice(stockInfo.day_high)}</span>
                  </div>
                  {stockInfo.week_52_low && stockInfo.week_52_high && (
                    <>
                      <div className="text-xs text-muted-foreground mb-1 mt-3">52 Week Range</div>
                      <div className="flex items-center gap-2 text-sm">
                        <span>{formatPrice(stockInfo.week_52_low)}</span>
                        <Progress
                          value={((quoteData?.price ?? stockInfo.current_price ?? stockInfo.week_52_low) - stockInfo.week_52_low) / (stockInfo.week_52_high - stockInfo.week_52_low) * 100}
                          className="flex-1 h-2"
                        />
                        <span>{formatPrice(stockInfo.week_52_high)}</span>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Chart */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Price Chart</CardTitle>
          <DrawingToolbar symbol={currentSymbol} />
        </CardHeader>
        <CardContent>
          {historyLoading ? (
            <SkeletonChart height={384} />
          ) : chartData.length === 0 ? (
            <div className="h-96 flex items-center justify-center text-muted-foreground">
              No data available
            </div>
          ) : (
            <CandlestickChart
              data={chartData}
              indicators={indicators}
              height={400}
              showVolume
              symbol={currentSymbol}
              enableDrawing
            />
          )}
        </CardContent>
      </Card>

      {/* Key Statistics Grid */}
      {stockInfo && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {/* Volume Metrics */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <BarChart3 className="h-4 w-4" />
                Volume
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Volume</span>
                <span className="font-medium">{stockInfo.volume ? formatCompactNumber(stockInfo.volume) : 'N/A'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Avg Volume</span>
                <span className="font-medium">{stockInfo.avg_volume ? formatCompactNumber(stockInfo.avg_volume) : 'N/A'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Avg Vol (10D)</span>
                <span className="font-medium">{stockInfo.avg_volume_10d ? formatCompactNumber(stockInfo.avg_volume_10d) : 'N/A'}</span>
              </div>
            </CardContent>
          </Card>

          {/* Fundamentals */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Activity className="h-4 w-4" />
                Fundamentals
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">P/E Ratio</span>
                <span className="font-medium">{stockInfo.pe_ratio != null ? safeToFixed(stockInfo.pe_ratio, 2) : 'N/A'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Forward P/E</span>
                <span className="font-medium">{stockInfo.forward_pe != null ? safeToFixed(stockInfo.forward_pe, 2) : 'N/A'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">EPS</span>
                <span className="font-medium">{stockInfo.eps ? formatPrice(stockInfo.eps) : 'N/A'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">PEG Ratio</span>
                <span className="font-medium">{stockInfo.peg_ratio != null ? safeToFixed(stockInfo.peg_ratio, 2) : 'N/A'}</span>
              </div>
            </CardContent>
          </Card>

          {/* Market Data */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                Market Data
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Market Cap</span>
                <span className="font-medium">{stockInfo.market_cap ? formatCompactNumber(stockInfo.market_cap) : 'N/A'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Beta</span>
                <span className="font-medium">{stockInfo.beta != null ? safeToFixed(stockInfo.beta, 2) : 'N/A'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Dividend Yield</span>
                <span className="font-medium">{stockInfo.dividend_yield ? formatPercent(stockInfo.dividend_yield * 100) : 'N/A'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">P/B Ratio</span>
                <span className="font-medium">{stockInfo.price_to_book != null ? safeToFixed(stockInfo.price_to_book, 2) : 'N/A'}</span>
              </div>
            </CardContent>
          </Card>

          {/* Analyst Targets */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Target className="h-4 w-4" />
                Analyst Targets
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Target Low</span>
                <span className="font-medium">{stockInfo.target_low_price ? formatPrice(stockInfo.target_low_price) : 'N/A'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Target Mean</span>
                <span className="font-medium">{stockInfo.target_mean_price ? formatPrice(stockInfo.target_mean_price) : 'N/A'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Target High</span>
                <span className="font-medium">{stockInfo.target_high_price ? formatPrice(stockInfo.target_high_price) : 'N/A'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Recommendation</span>
                <span className={cn(
                  'font-medium capitalize',
                  stockInfo.recommendation === 'buy' || stockInfo.recommendation === 'strong_buy' ? 'text-profit' :
                  stockInfo.recommendation === 'sell' || stockInfo.recommendation === 'strong_sell' ? 'text-loss' : ''
                )}>
                  {stockInfo.recommendation?.replace('_', ' ') ?? 'N/A'}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Technical Analysis Signal */}
      {analysisData && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {analysisData.signal.signal === 'BUY' ? (
                <TrendingUp className="h-5 w-5 text-profit" />
              ) : analysisData.signal.signal === 'SELL' ? (
                <TrendingDown className="h-5 w-5 text-loss" />
              ) : (
                <Activity className="h-5 w-5" />
              )}
              Technical Signal: {analysisData.signal.signal}
            </CardTitle>
            <CardDescription>
              Trend: {analysisData.trend} • Confidence: {safeToFixed(analysisData.signal.confidence, 0)}%
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <div className="text-sm text-muted-foreground mb-1">RSI (14)</div>
                <div className="flex items-center gap-2">
                  <Progress value={analysisData.indicators.rsi_14 ?? 50} className="flex-1" />
                  <span className={cn(
                    'text-sm font-medium',
                    (analysisData.indicators.rsi_14 ?? 50) > 70 ? 'text-loss' :
                    (analysisData.indicators.rsi_14 ?? 50) < 30 ? 'text-profit' : ''
                  )}>
                    {analysisData.indicators.rsi_14 != null ? safeToFixed(analysisData.indicators.rsi_14, 1) : 'N/A'}
                  </span>
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground mb-1">Support Levels</div>
                <div className="text-sm font-medium">
                  {analysisData.support_levels.length > 0
                    ? analysisData.support_levels.map(l => formatPrice(l)).join(', ')
                    : 'N/A'}
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground mb-1">Resistance Levels</div>
                <div className="text-sm font-medium">
                  {analysisData.resistance_levels.length > 0
                    ? analysisData.resistance_levels.map(l => formatPrice(l)).join(', ')
                    : 'N/A'}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick Trade Panel */}
      <QuickTradePanel symbol={currentSymbol} />
    </div>
  );
}

