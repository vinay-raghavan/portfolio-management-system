'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { TrendingUp, TrendingDown, Zap, BarChart3, Layers, RefreshCw, ExternalLink, Clock, ChevronDown, ChevronRight, CheckCircle2, Activity, Target, AlertCircle, Info } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { screenerApi, type RecommendationCategory, type RecommendationItem } from '@/lib/api';
import { useUIStore } from '@/store';
import { useCurrency } from '@/hooks/useCurrency';
import { cn, formatPercent } from '@/lib/utils';

const CATEGORY_CONFIG: Record<RecommendationCategory, { icon: React.ReactNode; color: string }> = {
  momentum: { icon: <TrendingUp className="h-4 w-4" />, color: 'text-green-500' },
  breakout: { icon: <Zap className="h-4 w-4" />, color: 'text-blue-500' },
  pullback: { icon: <BarChart3 className="h-4 w-4" />, color: 'text-purple-500' },
  sector: { icon: <Layers className="h-4 w-4" />, color: 'text-cyan-500' },
};

interface RecommendationRowProps {
  item: RecommendationItem;
  isExpanded: boolean;
  onToggle: (e: React.MouseEvent) => void;
  onNavigate: (symbol: string) => void;
}

function RecommendationRow({ item, isExpanded, onToggle, onNavigate }: RecommendationRowProps) {
  const { format: formatCurrency } = useCurrency();

  return (
    <Collapsible open={isExpanded}>
      <div className="flex items-center justify-between w-full hover:bg-muted/50 rounded-md px-2 py-2 -mx-2 transition-colors">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={onToggle}>
              {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
            </Button>
          </CollapsibleTrigger>
          <Badge variant="outline" className="w-6 h-6 p-0 flex items-center justify-center text-xs shrink-0">
            {item.rank}
          </Badge>
          <button onClick={() => onNavigate(item.symbol)} className="text-left cursor-pointer min-w-0">
            <span className="font-medium hover:underline underline-offset-2">{item.symbol}</span>
            <p className="text-xs text-muted-foreground truncate max-w-[150px]">{item.reasons[0]}</p>
          </button>
        </div>
        <button onClick={() => onNavigate(item.symbol)} className="text-right cursor-pointer shrink-0">
          <div className="text-sm font-medium">{formatCurrency(item.price_at_rec)}</div>
          <div className="flex gap-1 text-xs justify-end">
            {item.return_1d !== null && item.return_1d !== undefined && (
              <span className={cn(item.return_1d >= 0 ? 'text-profit' : 'text-loss')}>
                1D: {formatPercent(item.return_1d)}
              </span>
            )}
          </div>
        </button>
      </div>
      <CollapsibleContent>
        <div className="ml-2 mr-2 mb-2 mt-1 bg-gradient-to-r from-muted/30 via-muted/20 to-muted/30 rounded-lg p-3">
          {/* Multi-Factor Score Banner - show if available */}
          {(item.combined_score || item.confidence_level) && (
            <div className="mb-3 p-2.5 rounded-lg border bg-gradient-to-r from-primary/5 to-transparent">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-3">
                  {/* Combined Score */}
                  {item.combined_score && (
                    <div className="flex items-center gap-2">
                      <Target className="h-4 w-4 text-primary" />
                      <span className="text-xs text-muted-foreground">Score:</span>
                      <span className={cn('font-bold text-sm', item.combined_score >= 70 ? 'text-green-600' : item.combined_score >= 50 ? 'text-yellow-600' : 'text-muted-foreground')}>
                        {item.combined_score.toFixed(0)}
                      </span>
                    </div>
                  )}
                  {/* Signal Direction */}
                  {item.signal_direction && (
                    <Badge variant={item.signal_direction === 'long' ? 'default' : item.signal_direction === 'short' ? 'destructive' : 'secondary'} className="text-xs">
                      {item.signal_direction === 'long' ? '↑ Long' : item.signal_direction === 'short' ? '↓ Short' : '→ Neutral'}
                    </Badge>
                  )}
                  {/* Confidence */}
                  {item.confidence_level && item.confidence_level !== 'skip' && (
                    <Badge variant={item.confidence_level === 'high' ? 'default' : item.confidence_level === 'medium' ? 'secondary' : 'outline'} className="text-xs">
                      {item.confidence_level === 'high' ? '🎯 High' : item.confidence_level === 'medium' ? '⚡ Medium' : '📊 Low'} Confidence
                    </Badge>
                  )}
                  {item.confidence_level === 'skip' && item.skip_reason && (
                    <Badge variant="outline" className="text-xs text-muted-foreground">
                      ⚠️ {item.skip_reason}
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-2 text-[10px]">
                  {/* Individual Factor Scores */}
                  {item.technical_score !== null && item.technical_score !== undefined && (
                    <span className="text-muted-foreground">Tech: <span className="font-medium">{item.technical_score.toFixed(0)}</span></span>
                  )}
                  {item.fundamental_score !== null && item.fundamental_score !== undefined && (
                    <span className="text-muted-foreground">Fund: <span className="font-medium">{item.fundamental_score.toFixed(0)}</span></span>
                  )}
                  {item.sentiment_score !== null && item.sentiment_score !== undefined && (
                    <span className={cn('text-muted-foreground', item.sentiment_score > 0 ? 'text-green-600' : item.sentiment_score < 0 ? 'text-red-600' : '')}>
                      Sent: <span className="font-medium">{item.sentiment_score > 0 ? '+' : ''}{item.sentiment_score.toFixed(0)}</span>
                    </span>
                  )}
                  {/* Recommended Strategy */}
                  {item.recommended_strategy && (
                    <Badge variant="outline" className="text-[10px] ml-1">
                      {item.recommended_strategy.toUpperCase()}
                    </Badge>
                  )}
                </div>
              </div>
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {/* Filter Scores Card */}
            <div className="rounded-lg border bg-card p-2.5 shadow-sm">
              <div className="flex items-center gap-2 mb-2">
                <BarChart3 className="h-3.5 w-3.5 text-blue-500" />
                <h4 className="font-semibold text-xs">Filter Scores</h4>
              </div>
              <div className="space-y-1.5">
                {Object.keys(item.filter_scores).length > 0 ? (
                  Object.entries(item.filter_scores).map(([key, value]) => {
                    const score = typeof value === 'number' ? value : 0;
                    const colorClass = score >= 80 ? 'bg-green-500' : score >= 60 ? 'bg-emerald-500' : score >= 40 ? 'bg-yellow-500' : 'bg-red-500';
                    return (
                      <div key={key} className="flex items-center justify-between gap-2">
                        <span className="text-[11px] text-muted-foreground capitalize">{key.replace(/_/g, ' ')}</span>
                        <div className="flex items-center gap-2">
                          <div className="w-12 h-1.5 bg-muted rounded-full overflow-hidden">
                            <div className={cn('h-full rounded-full', colorClass)} style={{ width: `${Math.min(score, 100)}%` }} />
                          </div>
                          <span className={cn('text-[11px] font-medium w-6 text-right', score >= 70 ? 'text-green-600 dark:text-green-400' : score >= 50 ? 'text-yellow-600 dark:text-yellow-400' : 'text-muted-foreground')}>
                            {score.toFixed(0)}
                          </span>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <p className="text-[11px] text-muted-foreground italic">No filter scores available</p>
                )}
              </div>
            </div>

            {/* Technical Signals Card */}
            <div className="rounded-lg border bg-card p-2.5 shadow-sm">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="h-3.5 w-3.5 text-purple-500" />
                <h4 className="font-semibold text-xs">Technical Signals</h4>
              </div>
              <div className="space-y-1">
                {item.reasons.length > 0 ? (
                  item.reasons.slice(0, 3).map((reason, idx) => (
                    <div key={idx} className="flex items-start gap-1.5">
                      <CheckCircle2 className="h-3 w-3 text-green-500 mt-0.5 shrink-0" />
                      <span className="text-[11px] text-muted-foreground leading-relaxed">{reason}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-[11px] text-muted-foreground italic">No signals available</p>
                )}
              </div>
            </div>

            {/* Detailed Analysis Card - uses metadata for rich info */}
            <div className="rounded-lg border bg-card p-2.5 shadow-sm">
              <div className="flex items-center gap-2 mb-2">
                <Target className="h-3.5 w-3.5 text-orange-500" />
                <h4 className="font-semibold text-xs">Detailed Analysis</h4>
                {/* Returns inline */}
                <div className="flex gap-1.5 ml-auto text-[10px]">
                  {item.return_1d !== null && item.return_1d !== undefined && (
                    <span className={cn(item.return_1d >= 0 ? 'text-profit' : 'text-loss')}>
                      1D: {formatPercent(item.return_1d)}
                    </span>
                  )}
                  {item.return_1w !== null && item.return_1w !== undefined && (
                    <span className={cn(item.return_1w >= 0 ? 'text-profit' : 'text-loss')}>
                      1W: {formatPercent(item.return_1w)}
                    </span>
                  )}
                  {item.return_1m !== null && item.return_1m !== undefined && (
                    <span className={cn(item.return_1m >= 0 ? 'text-profit' : 'text-loss')}>
                      1M: {formatPercent(item.return_1m)}
                    </span>
                  )}
                </div>
              </div>
              <div className="space-y-1">
                {(() => {
                  // Extract detailed metrics from metadata
                  const details: { label: string; value: string; isPositive: boolean; isWarning: boolean }[] = [];
                  const meta = item.metadata || {};

                  // Momentum filter data
                  const momentum = meta.momentum_filter as Record<string, number> | undefined;
                  if (momentum) {
                    if (momentum.roc !== undefined) {
                      details.push({ label: 'ROC', value: `${momentum.roc.toFixed(1)}%`, isPositive: momentum.roc > 0, isWarning: false });
                    }
                    if (momentum.rsi !== undefined) {
                      const rsiPositive = momentum.rsi >= 50 && momentum.rsi <= 70;
                      const rsiWarning = momentum.rsi > 70 || momentum.rsi < 30;
                      details.push({ label: 'RSI', value: momentum.rsi.toFixed(0), isPositive: rsiPositive, isWarning: rsiWarning });
                    }
                    if (momentum.pct_from_52w_high !== undefined) {
                      const nearHigh = momentum.pct_from_52w_high < 10;
                      details.push({ label: '52W High', value: `${momentum.pct_from_52w_high.toFixed(1)}% away`, isPositive: nearHigh, isWarning: !nearHigh });
                    }
                  }

                  // Moving average filter data
                  const ma = meta.moving_average_filter as Record<string, unknown> | undefined;
                  if (ma) {
                    if (ma.trend_up !== undefined) {
                      details.push({ label: 'Trend', value: ma.trend_up ? 'Uptrend' : 'Downtrend', isPositive: !!ma.trend_up, isWarning: !ma.trend_up });
                    }
                    if (ma.above_trend !== undefined) {
                      details.push({ label: 'Above 200MA', value: ma.above_trend ? 'Yes' : 'No', isPositive: !!ma.above_trend, isWarning: !ma.above_trend });
                    }
                    if (ma.stacked_ma !== undefined && ma.stacked_ma) {
                      details.push({ label: 'Stacked MAs', value: 'Yes', isPositive: true, isWarning: false });
                    }
                  }

                  // Volume filter data
                  const volume = meta.volume_filter as Record<string, number> | undefined;
                  if (volume) {
                    if (volume.avg_volume !== undefined) {
                      const avgVol = volume.avg_volume >= 1000000 ? `${(volume.avg_volume / 1000000).toFixed(1)}M` : `${(volume.avg_volume / 1000).toFixed(0)}K`;
                      details.push({ label: 'Avg Volume', value: avgVol, isPositive: volume.avg_volume >= 500000, isWarning: false });
                    }
                  }

                  return details.length > 0 ? (
                    details.map((d, idx) => {
                      const IconComponent = d.isPositive ? TrendingUp : d.isWarning ? AlertCircle : Info;
                      const iconColor = d.isPositive ? 'text-green-500' : d.isWarning ? 'text-yellow-500' : 'text-blue-500';
                      return (
                        <div key={idx} className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-1.5">
                            <IconComponent className={cn('h-3 w-3 shrink-0', iconColor)} />
                            <span className="text-[11px] text-muted-foreground">{d.label}</span>
                          </div>
                          <span className={cn('text-[11px] font-medium', d.isPositive ? 'text-green-600 dark:text-green-400' : d.isWarning ? 'text-yellow-600 dark:text-yellow-400' : 'text-foreground')}>{d.value}</span>
                        </div>
                      );
                    })
                  ) : (
                    <p className="text-[11px] text-muted-foreground italic">No detailed analysis available</p>
                  );
                })()}
              </div>
            </div>
          </div>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

export function RecommendationsWidget() {
  const router = useRouter();
  const { setSelectedSymbol } = useUIStore();
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  const { data, isLoading, refetch, isFetching, dataUpdatedAt } = useQuery({
    queryKey: ['recommendations'],
    queryFn: () => screenerApi.getRecommendations().then((res) => res.data),
    refetchInterval: 5 * 60 * 1000, // Refresh every 5 minutes
    staleTime: 2 * 60 * 1000, // Consider stale after 2 minutes
  });

  const handleNavigate = (symbol: string) => {
    setSelectedSymbol(symbol);
    router.push('/analysis');
  };

  const handleToggleExpand = (symbol: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedItems((prev) => {
      const next = new Set(prev);
      if (next.has(symbol)) {
        next.delete(symbol);
      } else {
        next.add(symbol);
      }
      return next;
    });
  };

  const handleViewAll = () => {
    router.push('/screener');
  };

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (isLoading) {
    return (
      <Card className="col-span-full">
        <CardHeader className="pb-2">
          <div className="h-5 w-48 bg-muted rounded animate-pulse" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 bg-muted rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const categories = data?.categories ?? [];

  return (
    <Card className="col-span-full">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Today&apos;s Picks
        </CardTitle>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {dataUpdatedAt ? formatTime(dataUpdatedAt) : '--:--'}
          </span>
          <Button variant="ghost" size="sm" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={cn('h-4 w-4', isFetching && 'animate-spin')} />
          </Button>
          <Button variant="ghost" size="sm" onClick={handleViewAll}>
            <ExternalLink className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {categories.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            No recommendations available yet. Check back after market open.
          </p>
        ) : (
          <Tabs defaultValue={categories[0]?.category} className="w-full">
            <TabsList className="w-full justify-start">
              {categories.map((cat) => {
                const config = CATEGORY_CONFIG[cat.category];
                return (
                  <TabsTrigger key={cat.category} value={cat.category} className="gap-1">
                    <span className={config?.color}>{config?.icon}</span>
                    <span className="hidden sm:inline">{cat.title}</span>
                  </TabsTrigger>
                );
              })}
            </TabsList>
            {categories.map((cat) => (
              <TabsContent key={cat.category} value={cat.category} className="mt-3">
                <p className="text-xs text-muted-foreground mb-3">{cat.description}</p>
                <div className="space-y-1">
                  {cat.recommendations.slice(0, 5).map((item) => (
                    <RecommendationRow
                      key={item.symbol}
                      item={item}
                      isExpanded={expandedItems.has(item.symbol)}
                      onToggle={(e) => handleToggleExpand(item.symbol, e)}
                      onNavigate={handleNavigate}
                    />
                  ))}
                </div>
              </TabsContent>
            ))}
          </Tabs>
        )}
      </CardContent>
    </Card>
  );
}

