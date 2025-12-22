'use client';

import { TrendingUp, TrendingDown } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatPercent, cn } from '@/lib/utils';
import { useCurrency } from '@/hooks/useCurrency';
import type { Position } from '@/types';

interface TopMoversProps {
  positions: Position[];
  isLoading?: boolean;
}

export function TopMovers({ positions, isLoading }: TopMoversProps) {
  const { format: formatCurrency } = useCurrency();

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        {[...Array(2)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="pb-2">
              <div className="h-5 w-32 bg-muted rounded" />
            </CardHeader>
            <CardContent className="space-y-3">
              {[...Array(3)].map((_, j) => (
                <div key={j} className="flex justify-between">
                  <div className="h-4 w-16 bg-muted rounded" />
                  <div className="h-4 w-20 bg-muted rounded" />
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  // Sort positions by P&L percentage
  const sortedByPnl = [...positions].sort(
    (a, b) => (b.unrealized_pnl_pct ?? 0) - (a.unrealized_pnl_pct ?? 0)
  );

  const topGainers = sortedByPnl
    .filter((p) => (p.unrealized_pnl_pct ?? 0) > 0)
    .slice(0, 5);

  const topLosers = sortedByPnl
    .filter((p) => (p.unrealized_pnl_pct ?? 0) < 0)
    .slice(-5)
    .reverse();

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {/* Top Gainers */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingUp className="h-4 w-4 text-profit" />
            Top Gainers
          </CardTitle>
        </CardHeader>
        <CardContent>
          {topGainers.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No gainers today
            </p>
          ) : (
            <div className="space-y-3">
              {topGainers.map((position) => (
                <div
                  key={position.id}
                  className="flex items-center justify-between"
                >
                  <div>
                    <span className="font-medium">{position.symbol}</span>
                    <span className="text-xs text-muted-foreground ml-2">
                      {position.quantity} shares
                    </span>
                  </div>
                  <div className="text-right">
                    <div className="text-profit font-medium">
                      {formatPercent(position.unrealized_pnl_pct ?? 0)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {formatCurrency(position.unrealized_pnl ?? 0)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Top Losers */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingDown className="h-4 w-4 text-loss" />
            Top Losers
          </CardTitle>
        </CardHeader>
        <CardContent>
          {topLosers.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No losers today
            </p>
          ) : (
            <div className="space-y-3">
              {topLosers.map((position) => (
                <div
                  key={position.id}
                  className="flex items-center justify-between"
                >
                  <div>
                    <span className="font-medium">{position.symbol}</span>
                    <span className="text-xs text-muted-foreground ml-2">
                      {position.quantity} shares
                    </span>
                  </div>
                  <div className="text-right">
                    <div className="text-loss font-medium">
                      {formatPercent(position.unrealized_pnl_pct ?? 0)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {formatCurrency(position.unrealized_pnl ?? 0)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

