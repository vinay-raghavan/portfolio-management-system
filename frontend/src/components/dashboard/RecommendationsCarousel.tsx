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
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
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

  // Fetch screener recommendations
  const { data: screenerData, isLoading: screenerLoading, refetch: refetchScreener } = useQuery({
    queryKey: ['recommendations-carousel-screener'],
    queryFn: () => screenerApi.getRecommendations().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });

  // Fetch research recommendations (4 items for compact view)
  const { data: researchData, isLoading: researchLoading, refetch: refetchResearch } = useQuery({
    queryKey: ['recommendations-carousel-research'],
    queryFn: () => researchApi.getRecommendations(undefined, 4),
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

  const handleNavigateSymbol = (symbol: string) => {
    setSelectedSymbol(symbol);
    router.push('/analysis');
  };

  const handleViewAll = () => {
    router.push(SLIDE_CONFIGS[currentSlide].navigateTo);
  };

  const goToSlide = (index: number) => setCurrentSlide(index);
  const goPrev = () => setCurrentSlide((prev) => (prev - 1 + SLIDE_CONFIGS.length) % SLIDE_CONFIGS.length);
  const goNext = () => setCurrentSlide((prev) => (prev + 1) % SLIDE_CONFIGS.length);

  const isLoading = screenerLoading || researchLoading;
  const screenerCategories = screenerData?.categories ?? [];
  const researchRecs = researchData?.data?.recommendations ?? [];

  // Get data for current slide (4 items max for compact view)
  const getCurrentSlideData = (): { items: Array<RecommendationItem | RecommendationStock>; isScreener: boolean } => {
    const config = SLIDE_CONFIGS[currentSlide];
    if (config.type === 'research') {
      return { items: researchRecs.slice(0, 4), isScreener: false };
    }
    const category = screenerCategories.find((c) => c.category === config.type);
    return { items: category?.recommendations.slice(0, 4) ?? [], isScreener: true };
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
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-8 bg-muted rounded animate-pulse" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="text-center text-muted-foreground py-4 text-sm">
            No picks available
          </div>
        ) : (
          <div className="space-y-0.5">
            {items.slice(0, 4).map((item, idx) => {
              if (isScreener) {
                const rec = item as RecommendationItem;
                return (
                  <button
                    key={rec.symbol}
                    onClick={() => handleNavigateSymbol(rec.symbol)}
                    className="flex items-center justify-between w-full hover:bg-muted/50 rounded px-1.5 py-1.5 transition-colors text-left"
                  >
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="text-xs text-muted-foreground w-4">{rec.rank}</span>
                      <span className="font-medium text-sm truncate">{rec.symbol}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium">{formatCurrency(rec.price_at_rec)}</span>
                      {rec.return_1d !== null && rec.return_1d !== undefined && (
                        <span className={cn('text-xs', rec.return_1d >= 0 ? 'text-profit' : 'text-loss')}>
                          {formatPercent(rec.return_1d)}
                        </span>
                      )}
                    </div>
                  </button>
                );
              } else {
                const rec = item as RecommendationStock;
                return (
                  <button
                    key={rec.symbol}
                    onClick={() => handleNavigateSymbol(rec.symbol)}
                    className="flex items-center justify-between w-full hover:bg-muted/50 rounded px-1.5 py-1.5 transition-colors text-left"
                  >
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="text-xs text-muted-foreground w-4">{idx + 1}</span>
                      <span className="font-medium text-sm truncate">{rec.symbol}</span>
                      <Badge variant="secondary" className="text-[9px] px-1 py-0 h-4">{rec.category}</Badge>
                    </div>
                    <Badge variant="outline" className="text-[10px] px-1 py-0 h-4">
                      <Zap className="h-2.5 w-2.5 mr-0.5" />
                      {rec.combined_score.toFixed(0)}
                    </Badge>
                  </button>
                );
              }
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

