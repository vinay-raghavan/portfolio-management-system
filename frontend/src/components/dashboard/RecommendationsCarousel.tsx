'use client';

import { useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import {
  TrendingUp,
  Zap,
  BarChart3,
  Layers,
  Star,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  RefreshCw,
  ExternalLink,
  Activity,
  Target,
  CheckCircle2,
  AlertCircle,
  Info,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { screenerApi, researchApi, type RecommendationCategory, type RecommendationItem } from '@/lib/api';
import { useUIStore } from '@/store';
import { useCurrency } from '@/hooks/useCurrency';
import { cn, formatPercent } from '@/lib/utils';
import type { RecommendationStock } from '@/types';

// Slide types: screener categories + research
type SlideType = RecommendationCategory | 'research';

interface SlideConfig {
  type: SlideType;
  title: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  navigateTo: string;
}

const SLIDE_CONFIGS: SlideConfig[] = [
  { type: 'momentum', title: 'Momentum', description: 'Strong upward price movement', icon: <TrendingUp className="h-5 w-5" />, color: 'text-green-500', navigateTo: '/screener?preset=momentum' },
  { type: 'breakout', title: 'Breakout', description: 'Breaking key resistance levels', icon: <Zap className="h-5 w-5" />, color: 'text-blue-500', navigateTo: '/screener?preset=breakout' },
  { type: 'pullback', title: 'Pullback', description: 'Buying opportunities in uptrends', icon: <BarChart3 className="h-5 w-5" />, color: 'text-purple-500', navigateTo: '/screener?preset=pullback' },
  { type: 'sector', title: 'Sectors', description: 'Top sector performers', icon: <Layers className="h-5 w-5" />, color: 'text-cyan-500', navigateTo: '/screener?preset=sector_rotation' },
  { type: 'research', title: 'Research Picks', description: 'Fundamental + technical analysis', icon: <Star className="h-5 w-5" />, color: 'text-yellow-500', navigateTo: '/research?tab=recommendations' },
];

const AUTO_SCROLL_INTERVAL = 5000; // 5 seconds

export function RecommendationsCarousel() {
  const router = useRouter();
  const { setSelectedSymbol } = useUIStore();
  const { format: formatCurrency } = useCurrency();
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  // Fetch screener recommendations
  const { data: screenerData, isLoading: screenerLoading, refetch: refetchScreener } = useQuery({
    queryKey: ['recommendations-carousel-screener'],
    queryFn: () => screenerApi.getRecommendations().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });

  // Fetch research recommendations (5 items for expanded view)
  const { data: researchData, isLoading: researchLoading, refetch: refetchResearch } = useQuery({
    queryKey: ['recommendations-carousel-research'],
    queryFn: () => researchApi.getRecommendations(undefined, 5),
    staleTime: 2 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });

  // Auto-scroll logic
  useEffect(() => {
    if (isPaused) return;
    const interval = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % SLIDE_CONFIGS.length);
    }, AUTO_SCROLL_INTERVAL);
    return () => clearInterval(interval);
  }, [isPaused]);

  const handleRefresh = useCallback(() => {
    refetchScreener();
    refetchResearch();
  }, [refetchScreener, refetchResearch]);

  const handleNavigateSymbol = (symbol: string, isResearch: boolean) => {
    if (isResearch) {
      router.push('/research?tab=recommendations');
    } else {
      setSelectedSymbol(symbol);
      router.push('/analysis');
    }
  };

  const handleViewAll = () => {
    router.push(SLIDE_CONFIGS[currentSlide].navigateTo);
  };

  const toggleExpand = (symbol: string) => {
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

  const goToSlide = (index: number) => setCurrentSlide(index);
  const goPrev = () => setCurrentSlide((prev) => (prev - 1 + SLIDE_CONFIGS.length) % SLIDE_CONFIGS.length);
  const goNext = () => setCurrentSlide((prev) => (prev + 1) % SLIDE_CONFIGS.length);

  const isLoading = screenerLoading || researchLoading;
  const screenerCategories = screenerData?.categories ?? [];
  const researchRecs = researchData?.data?.recommendations ?? [];

  // Get data for current slide (5 items for expanded view)
  const getCurrentSlideData = (): { items: Array<RecommendationItem | RecommendationStock>; isScreener: boolean } => {
    const config = SLIDE_CONFIGS[currentSlide];
    if (config.type === 'research') {
      return { items: researchRecs.slice(0, 5), isScreener: false };
    }
    const category = screenerCategories.find((c) => c.category === config.type);
    return { items: category?.recommendations.slice(0, 5) ?? [], isScreener: true };
  };

  const { items, isScreener } = getCurrentSlideData();
  const currentConfig = SLIDE_CONFIGS[currentSlide];

  return (
    <Card
      className="overflow-hidden"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      <CardHeader className="flex flex-row items-center justify-between pb-2 px-4 pt-4">
        <CardTitle className="text-sm flex items-center gap-2">
          <span className={currentConfig.color}>{currentConfig.icon}</span>
          {currentConfig.title}
        </CardTitle>
        <div className="flex items-center gap-1">
          {/* Dot indicators */}
          <div className="flex gap-1 mr-1">
            {SLIDE_CONFIGS.map((_, idx) => (
              <button
                key={idx}
                onClick={() => goToSlide(idx)}
                className={cn(
                  'w-1.5 h-1.5 rounded-full transition-colors',
                  idx === currentSlide ? 'bg-primary' : 'bg-muted-foreground/30 hover:bg-muted-foreground/50'
                )}
              />
            ))}
          </div>
          <Button variant="ghost" size="icon" onClick={goPrev} className="h-6 w-6">
            <ChevronLeft className="h-3 w-3" />
          </Button>
          <Button variant="ghost" size="icon" onClick={goNext} className="h-6 w-6">
            <ChevronRight className="h-3 w-3" />
          </Button>
          <Button variant="ghost" size="icon" onClick={handleViewAll} className="h-6 w-6">
            <ExternalLink className="h-3 w-3" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-4 pt-0">
        {isLoading ? (
          <div className="space-y-1">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-8 bg-muted rounded animate-pulse" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="text-center text-muted-foreground py-4 text-sm">
            No picks available
          </div>
        ) : (
          <div className="space-y-0.5">
            {items.slice(0, 5).map((item, idx) => {
              if (isScreener) {
                const rec = item as RecommendationItem;
                const isExpanded = expandedItems.has(rec.symbol);
                return (
                  <Collapsible key={rec.symbol} open={isExpanded}>
                    <div className="flex items-center justify-between w-full hover:bg-muted/50 rounded px-1.5 py-1 transition-colors">
                      <div className="flex items-center gap-1 min-w-0">
                        <CollapsibleTrigger asChild>
                          <Button variant="ghost" size="sm" className="h-5 w-5 p-0" onClick={() => toggleExpand(rec.symbol)}>
                            <ChevronDown className={cn('h-3 w-3 transition-transform', !isExpanded && '-rotate-90')} />
                          </Button>
                        </CollapsibleTrigger>
                        <span className="text-xs text-muted-foreground w-3">{rec.rank}</span>
                        <button onClick={() => handleNavigateSymbol(rec.symbol, false)} className="font-medium text-sm truncate hover:underline">
                          {rec.symbol}
                        </button>
                      </div>
                      <button onClick={() => handleNavigateSymbol(rec.symbol, false)} className="flex items-center gap-2">
                        <span className="text-xs font-medium">{formatCurrency(rec.price_at_rec)}</span>
                        {rec.return_1d !== null && rec.return_1d !== undefined && (
                          <span className={cn('text-xs', rec.return_1d >= 0 ? 'text-profit' : 'text-loss')}>
                            {formatPercent(rec.return_1d)}
                          </span>
                        )}
                      </button>
                    </div>
                    <CollapsibleContent>
                      <div className="ml-2 mr-2 mb-2 mt-1 bg-gradient-to-r from-muted/30 via-muted/20 to-muted/30 rounded-lg p-2">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                          {/* Filter Scores */}
                          <div className="rounded-lg border bg-card p-2 shadow-sm">
                            <div className="flex items-center gap-1.5 mb-1.5">
                              <BarChart3 className="h-3 w-3 text-blue-500" />
                              <h4 className="font-semibold text-[10px]">Filter Scores</h4>
                            </div>
                            <div className="space-y-1">
                              {Object.keys(rec.filter_scores).length > 0 ? (
                                Object.entries(rec.filter_scores).slice(0, 4).map(([key, value]) => {
                                  const score = typeof value === 'number' ? value : 0;
                                  const colorClass = score >= 80 ? 'bg-green-500' : score >= 60 ? 'bg-emerald-500' : score >= 40 ? 'bg-yellow-500' : 'bg-red-500';
                                  return (
                                    <div key={key} className="flex items-center justify-between gap-1">
                                      <span className="text-[10px] text-muted-foreground capitalize truncate">{key.replace(/_/g, ' ')}</span>
                                      <div className="flex items-center gap-1">
                                        <div className="w-8 h-1 bg-muted rounded-full overflow-hidden">
                                          <div className={cn('h-full rounded-full', colorClass)} style={{ width: `${Math.min(score, 100)}%` }} />
                                        </div>
                                        <span className="text-[10px] font-medium w-4 text-right">{score.toFixed(0)}</span>
                                      </div>
                                    </div>
                                  );
                                })
                              ) : (
                                <p className="text-[10px] text-muted-foreground italic">No scores</p>
                              )}
                            </div>
                          </div>

                          {/* Technical Signals */}
                          <div className="rounded-lg border bg-card p-2 shadow-sm">
                            <div className="flex items-center gap-1.5 mb-1.5">
                              <Activity className="h-3 w-3 text-purple-500" />
                              <h4 className="font-semibold text-[10px]">Signals</h4>
                            </div>
                            <div className="space-y-0.5">
                              {rec.reasons.length > 0 ? (
                                rec.reasons.slice(0, 3).map((reason, ridx) => (
                                  <div key={ridx} className="flex items-start gap-1">
                                    <CheckCircle2 className="h-2.5 w-2.5 text-green-500 mt-0.5 shrink-0" />
                                    <span className="text-[10px] text-muted-foreground leading-tight line-clamp-1">{reason}</span>
                                  </div>
                                ))
                              ) : (
                                <p className="text-[10px] text-muted-foreground italic">No signals</p>
                              )}
                            </div>
                          </div>

                          {/* Detailed Analysis */}
                          <div className="rounded-lg border bg-card p-2 shadow-sm">
                            <div className="flex items-center gap-1.5 mb-1.5">
                              <Target className="h-3 w-3 text-orange-500" />
                              <h4 className="font-semibold text-[10px]">Analysis</h4>
                              <div className="flex gap-1 ml-auto text-[9px]">
                                {rec.return_1d !== null && rec.return_1d !== undefined && (
                                  <span className={cn(rec.return_1d >= 0 ? 'text-profit' : 'text-loss')}>1D:{formatPercent(rec.return_1d)}</span>
                                )}
                                {rec.return_1w !== null && rec.return_1w !== undefined && (
                                  <span className={cn(rec.return_1w >= 0 ? 'text-profit' : 'text-loss')}>1W:{formatPercent(rec.return_1w)}</span>
                                )}
                              </div>
                            </div>
                            <div className="space-y-0.5">
                              {(() => {
                                const details: { label: string; value: string; isPositive: boolean; isWarning: boolean }[] = [];
                                const meta = rec.metadata || {};
                                const momentum = meta.momentum_filter as Record<string, number> | undefined;
                                if (momentum) {
                                  if (momentum.roc !== undefined) details.push({ label: 'ROC', value: `${momentum.roc.toFixed(1)}%`, isPositive: momentum.roc > 0, isWarning: false });
                                  if (momentum.rsi !== undefined) details.push({ label: 'RSI', value: momentum.rsi.toFixed(0), isPositive: momentum.rsi >= 50 && momentum.rsi <= 70, isWarning: momentum.rsi > 70 || momentum.rsi < 30 });
                                }
                                const ma = meta.moving_average_filter as Record<string, unknown> | undefined;
                                if (ma?.trend_up !== undefined) details.push({ label: 'Trend', value: ma.trend_up ? 'Up' : 'Down', isPositive: !!ma.trend_up, isWarning: !ma.trend_up });
                                return details.length > 0 ? (
                                  details.slice(0, 3).map((d, didx) => {
                                    const IconComp = d.isPositive ? TrendingUp : d.isWarning ? AlertCircle : Info;
                                    const iconColor = d.isPositive ? 'text-green-500' : d.isWarning ? 'text-yellow-500' : 'text-blue-500';
                                    return (
                                      <div key={didx} className="flex items-center justify-between gap-1">
                                        <div className="flex items-center gap-1">
                                          <IconComp className={cn('h-2.5 w-2.5 shrink-0', iconColor)} />
                                          <span className="text-[10px] text-muted-foreground">{d.label}</span>
                                        </div>
                                        <span className={cn('text-[10px] font-medium', d.isPositive ? 'text-green-600 dark:text-green-400' : d.isWarning ? 'text-yellow-600 dark:text-yellow-400' : '')}>{d.value}</span>
                                      </div>
                                    );
                                  })
                                ) : (
                                  <p className="text-[10px] text-muted-foreground italic">No analysis</p>
                                );
                              })()}
                            </div>
                          </div>
                        </div>
                      </div>
                    </CollapsibleContent>
                  </Collapsible>
                );
              } else {
                const rec = item as RecommendationStock;
                const isExpanded = expandedItems.has(rec.symbol);
                return (
                  <Collapsible key={rec.symbol} open={isExpanded}>
                    <div className="flex items-center justify-between w-full hover:bg-muted/50 rounded px-1.5 py-1 transition-colors">
                      <div className="flex items-center gap-1 min-w-0">
                        <CollapsibleTrigger asChild>
                          <Button variant="ghost" size="sm" className="h-5 w-5 p-0" onClick={() => toggleExpand(rec.symbol)}>
                            <ChevronDown className={cn('h-3 w-3 transition-transform', !isExpanded && '-rotate-90')} />
                          </Button>
                        </CollapsibleTrigger>
                        <span className="text-xs text-muted-foreground w-3">{idx + 1}</span>
                        <button onClick={() => handleNavigateSymbol(rec.symbol, true)} className="font-medium text-sm truncate hover:underline">
                          {rec.symbol}
                        </button>
                        <Badge variant="secondary" className="text-[9px] px-1 py-0 h-4">{rec.category}</Badge>
                      </div>
                      <button onClick={() => handleNavigateSymbol(rec.symbol, true)} className="flex items-center gap-1">
                        <Badge variant="outline" className="text-[10px] px-1 py-0 h-4">
                          <Zap className="h-2.5 w-2.5 mr-0.5" />
                          {rec.combined_score.toFixed(0)}
                        </Badge>
                      </button>
                    </div>
                    <CollapsibleContent>
                      <div className="ml-2 mr-2 mb-2 mt-1 bg-gradient-to-r from-muted/30 via-muted/20 to-muted/30 rounded-lg p-2">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                          {/* Scores */}
                          <div className="rounded-lg border bg-card p-2 shadow-sm">
                            <div className="flex items-center gap-1.5 mb-1.5">
                              <BarChart3 className="h-3 w-3 text-blue-500" />
                              <h4 className="font-semibold text-[10px]">Scores</h4>
                            </div>
                            <div className="space-y-1">
                              {[
                                { label: 'Fundamental', value: rec.fundamental_score, color: rec.fundamental_score >= 70 ? 'bg-green-500' : rec.fundamental_score >= 50 ? 'bg-yellow-500' : 'bg-red-500' },
                                { label: 'Technical', value: rec.technical_score, color: rec.technical_score >= 70 ? 'bg-green-500' : rec.technical_score >= 50 ? 'bg-yellow-500' : 'bg-red-500' },
                                { label: 'Combined', value: rec.combined_score, color: rec.combined_score >= 70 ? 'bg-green-500' : rec.combined_score >= 50 ? 'bg-yellow-500' : 'bg-red-500' },
                              ].map((s) => (
                                <div key={s.label} className="flex items-center justify-between gap-1">
                                  <span className="text-[10px] text-muted-foreground">{s.label}</span>
                                  <div className="flex items-center gap-1">
                                    <div className="w-8 h-1 bg-muted rounded-full overflow-hidden">
                                      <div className={cn('h-full rounded-full', s.color)} style={{ width: `${Math.min(s.value, 100)}%` }} />
                                    </div>
                                    <span className="text-[10px] font-medium w-4 text-right">{s.value.toFixed(0)}</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Thesis / Reasons */}
                          <div className="rounded-lg border bg-card p-2 shadow-sm">
                            <div className="flex items-center gap-1.5 mb-1.5">
                              <Activity className="h-3 w-3 text-purple-500" />
                              <h4 className="font-semibold text-[10px]">Thesis</h4>
                            </div>
                            <div className="space-y-0.5">
                              {rec.thesis ? (
                                <p className="text-[10px] text-muted-foreground leading-tight line-clamp-3">{rec.thesis}</p>
                              ) : rec.reasons.length > 0 ? (
                                rec.reasons.slice(0, 2).map((reason, ridx) => (
                                  <div key={ridx} className="flex items-start gap-1">
                                    <CheckCircle2 className="h-2.5 w-2.5 text-green-500 mt-0.5 shrink-0" />
                                    <span className="text-[10px] text-muted-foreground leading-tight line-clamp-1">{reason}</span>
                                  </div>
                                ))
                              ) : (
                                <p className="text-[10px] text-muted-foreground italic">No thesis</p>
                              )}
                            </div>
                          </div>

                          {/* Metrics */}
                          <div className="rounded-lg border bg-card p-2 shadow-sm">
                            <div className="flex items-center gap-1.5 mb-1.5">
                              <Target className="h-3 w-3 text-orange-500" />
                              <h4 className="font-semibold text-[10px]">Metrics</h4>
                            </div>
                            <div className="space-y-0.5">
                              {rec.current_price && (
                                <div className="flex items-center justify-between gap-1">
                                  <span className="text-[10px] text-muted-foreground">Price</span>
                                  <span className="text-[10px] font-medium">{formatCurrency(rec.current_price)}</span>
                                </div>
                              )}
                              {rec.pe_ratio && (
                                <div className="flex items-center justify-between gap-1">
                                  <span className="text-[10px] text-muted-foreground">P/E</span>
                                  <span className="text-[10px] font-medium">{rec.pe_ratio.toFixed(1)}</span>
                                </div>
                              )}
                              {rec.roe && (
                                <div className="flex items-center justify-between gap-1">
                                  <span className="text-[10px] text-muted-foreground">ROE</span>
                                  <span className="text-[10px] font-medium">{(rec.roe * 100).toFixed(1)}%</span>
                                </div>
                              )}
                              {rec.rsi && (
                                <div className="flex items-center justify-between gap-1">
                                  <span className="text-[10px] text-muted-foreground">RSI</span>
                                  <span className={cn('text-[10px] font-medium', rec.rsi > 70 ? 'text-yellow-500' : rec.rsi < 30 ? 'text-red-500' : 'text-green-500')}>{rec.rsi.toFixed(0)}</span>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    </CollapsibleContent>
                  </Collapsible>
                );
              }
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

