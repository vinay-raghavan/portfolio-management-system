'use client';

import { useQuery } from '@tanstack/react-query';
import { ArrowUpRight, ArrowDownRight, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { portfolioApi } from '@/lib/api';
import { cn } from '@/lib/utils';
import { useCurrency } from '@/hooks/useCurrency';
import type { Trade } from '@/types';

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

interface RecentTradesProps {
  limit?: number;
}

export function RecentTrades({ limit = 5 }: RecentTradesProps) {
  const { format: formatCurrency } = useCurrency();
  const { data, isLoading } = useQuery({
    queryKey: ['trades', 'recent', limit],
    queryFn: () => portfolioApi.getTrades(1, limit).then((res) => res.data),
    refetchInterval: 30000,
  });

  const trades = data?.trades ?? [];

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Clock className="h-4 w-4" />
            Recent Trades
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {[...Array(limit)].map((_, i) => (
            <div key={i} className="flex justify-between animate-pulse">
              <div className="space-y-1">
                <div className="h-4 w-20 bg-muted rounded" />
                <div className="h-3 w-16 bg-muted rounded" />
              </div>
              <div className="h-4 w-24 bg-muted rounded" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Clock className="h-4 w-4" />
          Recent Trades
        </CardTitle>
      </CardHeader>
      <CardContent>
        {trades.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No trades yet
          </p>
        ) : (
          <div className="space-y-3">
            {trades.map((trade: Trade) => (
              <div
                key={trade.id}
                className="flex items-center justify-between py-1"
              >
                <div className="flex items-center gap-2">
                  {trade.side === 'BUY' ? (
                    <ArrowUpRight className="h-4 w-4 text-profit" />
                  ) : (
                    <ArrowDownRight className="h-4 w-4 text-loss" />
                  )}
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{trade.symbol}</span>
                      <span
                        className={cn(
                          'text-xs px-1.5 py-0.5 rounded',
                          trade.side === 'BUY'
                            ? 'bg-profit/10 text-profit'
                            : 'bg-loss/10 text-loss'
                        )}
                      >
                        {trade.side}
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {trade.quantity} @ {formatCurrency(trade.price)}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-medium">
                    {formatCurrency(trade.quantity * trade.price)}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {formatTimeAgo(trade.executed_at)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

