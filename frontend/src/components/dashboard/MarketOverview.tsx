'use client';

import { useQuery } from '@tanstack/react-query';
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { marketDataApi } from '@/lib/api';
import { formatCurrency, formatPercent, cn } from '@/lib/utils';

// Major market indices to track
const MARKET_INDICES = [
  { symbol: '^GSPC', name: 'S&P 500' },
  { symbol: '^DJI', name: 'Dow Jones' },
  { symbol: '^IXIC', name: 'NASDAQ' },
  { symbol: '^RUT', name: 'Russell 2000' },
];

interface IndexQuote {
  symbol: string;
  name: string;
  price: number | null;
  change: number | null;
  changePct: number | null;
  isLoading: boolean;
  error: boolean;
}

export function MarketOverview() {
  // Fetch quotes for all indices
  const queries = MARKET_INDICES.map((index) => ({
    ...index,
    query: useQuery({
      queryKey: ['quote', index.symbol],
      queryFn: () => marketDataApi.getQuote(index.symbol).then((res) => res.data),
      refetchInterval: 60000, // Refresh every minute
      staleTime: 30000,
      retry: 1,
    }),
  }));

  const indices: IndexQuote[] = queries.map((q) => ({
    symbol: q.symbol,
    name: q.name,
    price: q.query.data?.price ?? null,
    change: q.query.data?.change ?? null,
    changePct: q.query.data?.change_pct ?? null,
    isLoading: q.query.isLoading,
    error: !!q.query.error,
  }));

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Activity className="h-4 w-4" />
          Market Overview
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          {indices.map((index) => (
            <div
              key={index.symbol}
              className="p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
            >
              {index.isLoading ? (
                <div className="animate-pulse space-y-2">
                  <div className="h-4 w-20 bg-muted rounded" />
                  <div className="h-5 w-24 bg-muted rounded" />
                </div>
              ) : index.error ? (
                <div className="text-sm text-muted-foreground">
                  <div className="font-medium">{index.name}</div>
                  <div className="text-xs">Unable to load</div>
                </div>
              ) : (
                <>
                  <div className="text-sm text-muted-foreground mb-1">
                    {index.name}
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">
                      {index.price !== null
                        ? formatCurrency(index.price)
                        : '--'}
                    </span>
                    {index.changePct !== null && (
                      <span
                        className={cn(
                          'flex items-center gap-1 text-sm font-medium',
                          index.changePct >= 0 ? 'text-profit' : 'text-loss'
                        )}
                      >
                        {index.changePct >= 0 ? (
                          <TrendingUp className="h-3 w-3" />
                        ) : (
                          <TrendingDown className="h-3 w-3" />
                        )}
                        {formatPercent(index.changePct)}
                      </span>
                    )}
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

