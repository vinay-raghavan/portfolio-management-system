'use client';

import { useQuery } from '@tanstack/react-query';
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
} from 'lucide-react';
import { researchApi } from '@/lib/api';
import { cn } from '@/lib/utils';

interface DigestWidgetProps {
  className?: string;
}

export function DigestWidget({ className }: DigestWidgetProps) {
  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ['research-digest-latest'],
    queryFn: () => researchApi.getLatestDigest(),
    staleTime: 5 * 60 * 1000,
  });

  const digest = data?.data;

  const formatPercent = (value: number | null | undefined): string => {
    if (value == null) return '-';
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };

  const getSentimentColor = (sentiment: number | null | undefined): string => {
    if (sentiment == null) return 'text-muted-foreground';
    if (sentiment >= 0.3) return 'text-green-600';
    if (sentiment <= -0.3) return 'text-red-600';
    return 'text-yellow-600';
  };

  const getSentimentLabel = (sentiment: number | null | undefined): string => {
    if (sentiment == null) return 'Neutral';
    if (sentiment >= 0.3) return 'Bullish';
    if (sentiment <= -0.3) return 'Bearish';
    return 'Neutral';
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
          <Button variant="ghost" size="icon" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={cn('h-4 w-4', isFetching && 'animate-spin')} />
          </Button>
        </CardHeader>
        <CardContent>
          <div className="text-center text-muted-foreground py-8">
            No digest available for today
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="flex items-center gap-2">
          <Newspaper className="h-5 w-5" />
          Daily Digest
          <Badge variant="outline" className="ml-2">
            {new Date(digest.digest_date).toLocaleDateString()}
          </Badge>
        </CardTitle>
        <Button variant="ghost" size="icon" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={cn('h-4 w-4', isFetching && 'animate-spin')} />
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Market Sentiment */}
        <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4" />
            <span className="text-sm font-medium">Market Sentiment</span>
          </div>
          <Badge className={cn('font-bold', getSentimentColor(digest.market_sentiment))}>
            {getSentimentLabel(digest.market_sentiment)}
          </Badge>
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

