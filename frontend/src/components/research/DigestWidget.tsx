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
          {stale && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending}
              title="Generate today's digest"
            >
              <Plus className={cn('h-4 w-4', generateMutation.isPending && 'animate-pulse')} />
            </Button>
          )}
          <Button variant="ghost" size="icon" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={cn('h-4 w-4', isFetching && 'animate-spin')} />
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

