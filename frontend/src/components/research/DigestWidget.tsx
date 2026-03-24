'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import {
  TrendingUp,
  TrendingDown,
  Newspaper,
  RefreshCw,
  Zap,
  Plus,
} from 'lucide-react';
import { researchApi } from '@/lib/api';
import { cn } from '@/lib/utils';
import { useToast } from '@/components/ui/use-toast';

interface DigestWidgetProps {
  className?: string;
}

export function DigestWidget({ className }: DigestWidgetProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ['research-digest-latest'],
    queryFn: () => researchApi.getLatestDigest(),
    staleTime: 5 * 60 * 1000,
  });

  const generateMutation = useMutation({
    mutationFn: () => researchApi.generateDigest(),
    onSuccess: (response) => {
      toast({
        title: 'Success',
        description: 'Daily digest generated successfully',
      });
      // Directly update the cache with the new digest data
      queryClient.setQueryData(['research-digest-latest'], response);
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      const message = error.response?.data?.detail || error.message || 'Failed to generate digest';
      if (message.includes('already exists')) {
        toast({
          title: 'Info',
          description: 'Digest already exists for today',
        });
        // Force refetch to get the existing digest
        refetch();
      } else {
        toast({
          variant: 'destructive',
          title: 'Error',
          description: message,
        });
      }
    },
  });

  // Check if digest is stale (not from today)
  const isDigestStale = () => {
    if (!data?.data?.digest_date) return true;
    const digestDate = new Date(data.data.digest_date).toDateString();
    const today = new Date().toDateString();
    return digestDate !== today;
  };

  const digest = data?.data;

  const formatPercent = (value: number | null | undefined): string => {
    if (value == null) return '-';
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };

  const getSentimentColor = (sentiment: number | null | undefined): string => {
    if (sentiment == null) return 'bg-gray-100 text-gray-800';
    if (sentiment >= 0.3) return 'bg-green-100 text-green-800';
    if (sentiment <= -0.3) return 'bg-red-100 text-red-800';
    return 'bg-gray-100 text-gray-800';
  };

  const getSentimentLabel = (sentiment: number | null | undefined): string => {
    if (sentiment == null) return 'Neutral';
    if (sentiment >= 0.5) return 'Strong Bullish';
    if (sentiment >= 0.3) return 'Bullish';
    if (sentiment >= 0.1) return 'Slightly Bullish';
    if (sentiment <= -0.5) return 'Strong Bearish';
    if (sentiment <= -0.3) return 'Bearish';
    if (sentiment <= -0.1) return 'Slightly Bearish';
    return 'Neutral';
  };

  const getSentimentEmoji = (sentiment: number | null | undefined): string => {
    if (sentiment == null) return '😐';
    if (sentiment >= 0.5) return '🚀';
    if (sentiment >= 0.3) return '📈';
    if (sentiment >= 0.1) return '🔼';
    if (sentiment <= -0.5) return '💥';
    if (sentiment <= -0.3) return '📉';
    if (sentiment <= -0.1) return '🔽';
    return '😐';
  };

  // Calculate gauge position (0-100) from sentiment (-1 to 1)
  const getSentimentGaugePosition = (sentiment: number | null | undefined): number => {
    if (sentiment == null) return 50;
    // Map -1 to 1 => 0 to 100
    return Math.max(0, Math.min(100, (sentiment + 1) * 50));
  };

  // Calculate component sentiments from available data
  const getComponentSentiments = () => {
    if (!digest) return null;

    const components: { name: string; score: number; weight: number; emoji: string }[] = [];

    // 1. Index Performance (40% weight) - from market_summary
    if (digest.market_summary?.indices && digest.market_summary.indices.length > 0) {
      const indexChanges = digest.market_summary.indices
        .map((idx) => idx.change_pct)
        .filter((pct): pct is number => pct != null);
      if (indexChanges.length > 0) {
        const avgChange = indexChanges.reduce((a, b) => a + b, 0) / indexChanges.length;
        // Normalize: +/-3% maps to +/-1.0 (capped)
        const indexScore = Math.max(-1, Math.min(1, avgChange / 3));
        components.push({ name: 'Indices', score: indexScore, weight: 40, emoji: indexScore >= 0 ? '📊' : '📉' });
      }
    }

    // 2. Market Breadth (30% weight) - from gainers/losers
    if (digest.top_gainers?.length || digest.top_losers?.length) {
      const gainers = digest.top_gainers || [];
      const losers = digest.top_losers || [];
      const avgGain = gainers.length > 0
        ? gainers.reduce((sum, g) => sum + (g.change_pct || 0), 0) / gainers.length
        : 0;
      const avgLoss = losers.length > 0
        ? losers.reduce((sum, l) => sum + Math.abs(l.change_pct || 0), 0) / losers.length
        : 0;

      let breadthScore = 0;
      if (avgGain + avgLoss > 0) {
        breadthScore = (avgGain - avgLoss) / (avgGain + avgLoss);
      }
      // Blend with count ratio
      const totalMovers = gainers.length + losers.length;
      if (totalMovers > 0) {
        const countRatio = (gainers.length - losers.length) / totalMovers;
        breadthScore = 0.7 * breadthScore + 0.3 * countRatio;
      }
      components.push({ name: 'Breadth', score: breadthScore, weight: 30, emoji: breadthScore >= 0 ? '⚖️' : '📉' });
    }

    // 3. News Sentiment (30% weight) - from news_highlights
    if (digest.news_highlights?.length) {
      const sentimentValues: Record<string, number> = { positive: 1, negative: -1, neutral: 0 };
      const newsScores = digest.news_highlights
        .filter(n => n.sentiment && n.sentiment in sentimentValues)
        .map(n => sentimentValues[n.sentiment!]);
      if (newsScores.length > 0) {
        const newsScore = newsScores.reduce((a, b) => a + b, 0) / newsScores.length;
        components.push({ name: 'News', score: newsScore, weight: 30, emoji: newsScore >= 0 ? '📰' : '🗞️' });
      }
    }

    return components;
  };

  if (error) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <div className="text-center text-muted-foreground">
            Failed to load digest
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader className="pb-2">
          <Skeleton className="h-6 w-40" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!digest) {
    return (
      <Card className={className}>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="flex items-center gap-2">
            <Newspaper className="h-5 w-5" />
            Daily Digest
          </CardTitle>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending}
              title="Generate today's digest"
            >
              <Plus className={cn('h-4 w-4', generateMutation.isPending && 'animate-pulse')} />
            </Button>
            <Button variant="ghost" size="icon" onClick={() => refetch()} disabled={isFetching}>
              <RefreshCw className={cn('h-4 w-4', isFetching && 'animate-spin')} />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <p className="text-muted-foreground mb-4">No digest available for today</p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending}
            >
              {generateMutation.isPending ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4 mr-2" />
                  Generate Today&apos;s Digest
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const stale = isDigestStale();

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="flex items-center gap-2">
          <Newspaper className="h-5 w-5" />
          Daily Digest
          <Badge variant={stale ? 'secondary' : 'outline'} className="ml-2">
            {new Date(digest.digest_date).toLocaleDateString()}
            {stale && ' (old)'}
          </Badge>
        </CardTitle>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            title="Regenerate digest"
          >
            <RefreshCw className={cn('h-4 w-4', generateMutation.isPending && 'animate-spin')} />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Stale digest warning */}
        {stale && (
          <div className="flex items-center justify-between p-3 rounded-lg bg-yellow-50 dark:bg-yellow-950/20 border border-yellow-200 dark:border-yellow-800">
            <span className="text-sm text-yellow-700 dark:text-yellow-400">
              This digest is from a previous day
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending}
            >
              {generateMutation.isPending ? 'Generating...' : 'Update'}
            </Button>
          </div>
        )}
        {/* Market Sentiment */}
        <div className="p-3 rounded-lg bg-muted/50 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4" />
              <span className="text-sm font-medium">Market Sentiment</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-lg">{getSentimentEmoji(digest.market_sentiment)}</span>
              <Badge className={cn('font-bold', getSentimentColor(digest.market_sentiment))}>
                {getSentimentLabel(digest.market_sentiment)}
              </Badge>
            </div>
          </div>

          {/* Sentiment Score & Gauge */}
          <div className="space-y-2">
            {/* Score Display */}
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Score</span>
              <span className="font-mono font-medium">
                {digest.market_sentiment != null
                  ? (digest.market_sentiment >= 0 ? '+' : '') + digest.market_sentiment.toFixed(3)
                  : 'N/A'
                }
              </span>
            </div>

            {/* Visual Gauge */}
            <div className="relative h-2 bg-gradient-to-r from-red-500 via-gray-300 to-green-500 rounded-full">
              {/* Marker */}
              <div
                className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white border-2 border-gray-800 rounded-full shadow-md transition-all duration-300"
                style={{ left: `calc(${getSentimentGaugePosition(digest.market_sentiment)}% - 6px)` }}
              />
            </div>

            {/* Range Labels */}
            <div className="flex justify-between text-[10px] text-muted-foreground">
              <span>-1.0</span>
              <span>Bearish</span>
              <span>Neutral</span>
              <span>Bullish</span>
              <span>+1.0</span>
            </div>

            {/* Category Breakdown */}
            <div className="grid grid-cols-3 gap-1 text-[10px] mt-1">
              <div className="text-center p-1 rounded bg-red-100 dark:bg-red-950/30">
                <div className="font-medium text-red-700 dark:text-red-400">≤ -0.3</div>
                <div className="text-red-600 dark:text-red-500">Bearish</div>
              </div>
              <div className="text-center p-1 rounded bg-gray-100 dark:bg-gray-800">
                <div className="font-medium text-gray-700 dark:text-gray-300">-0.3 to 0.3</div>
                <div className="text-gray-600 dark:text-gray-400">Neutral</div>
              </div>
              <div className="text-center p-1 rounded bg-green-100 dark:bg-green-950/30">
                <div className="font-medium text-green-700 dark:text-green-400">≥ 0.3</div>
                <div className="text-green-600 dark:text-green-500">Bullish</div>
              </div>
            </div>

            {/* Component Sentiments */}
            {getComponentSentiments() && getComponentSentiments()!.length > 0 && (
              <div className="mt-3 pt-2 border-t border-muted">
                <div className="text-[10px] text-muted-foreground mb-2">Sentiment Components</div>
                <div className="space-y-1.5">
                  {getComponentSentiments()!.map((comp) => (
                    <div key={comp.name} className="flex items-center gap-2 text-xs">
                      <span className="w-4">{comp.emoji}</span>
                      <span className="w-14 text-muted-foreground">{comp.name}</span>
                      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className={cn(
                            "h-full transition-all",
                            comp.score >= 0.3 ? "bg-green-500" :
                            comp.score <= -0.3 ? "bg-red-500" : "bg-gray-400"
                          )}
                          style={{
                            width: `${Math.abs(comp.score) * 100}%`,
                            marginLeft: comp.score < 0 ? `${(1 + comp.score) * 50}%` : '50%',
                          }}
                        />
                      </div>
                      <span className={cn(
                        "w-12 text-right font-mono text-[10px]",
                        comp.score >= 0.3 ? "text-green-600" :
                        comp.score <= -0.3 ? "text-red-600" : "text-muted-foreground"
                      )}>
                        {comp.score >= 0 ? '+' : ''}{comp.score.toFixed(2)}
                      </span>
                      <span className="w-8 text-[9px] text-muted-foreground">({comp.weight}%)</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Top Movers */}
        <div className="grid grid-cols-2 gap-3">
          {/* Top Gainers */}
          {digest.top_gainers && digest.top_gainers.length > 0 && (
            <div>
              <h4 className="text-sm font-medium mb-2 flex items-center gap-1 text-green-600">
                <TrendingUp className="h-4 w-4" />
                Top Gainers
              </h4>
              <div className="space-y-1">
                {digest.top_gainers.slice(0, 3).map((stock) => (
                  <div key={stock.symbol} className="flex justify-between text-xs">
                    <span className="truncate">{stock.symbol}</span>
                    <span className="font-medium text-green-600">
                      {formatPercent(stock.change_pct)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Losers */}
          {digest.top_losers && digest.top_losers.length > 0 && (
            <div>
              <h4 className="text-sm font-medium mb-2 flex items-center gap-1 text-red-600">
                <TrendingDown className="h-4 w-4" />
                Top Losers
              </h4>
              <div className="space-y-1">
                {digest.top_losers.slice(0, 3).map((stock) => (
                  <div key={stock.symbol} className="flex justify-between text-xs">
                    <span className="truncate">{stock.symbol}</span>
                    <span className="font-medium text-red-600">
                      {formatPercent(stock.change_pct)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* News Highlights */}
        {digest.news_highlights && digest.news_highlights.length > 0 && (
          <div>
            <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
              <Newspaper className="h-4 w-4" />
              News Highlights
            </h4>
            <div className="space-y-2">
              {digest.news_highlights.slice(0, 2).map((news, idx) => (
                <div key={idx} className="text-xs p-2 rounded-lg bg-muted/50">
                  <a
                    href={news.url || '#'}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:underline line-clamp-2"
                  >
                    {news.title}
                  </a>
                  {news.source && (
                    <span className="text-muted-foreground ml-1">— {news.source}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

      </CardContent>
    </Card>
  );
}

