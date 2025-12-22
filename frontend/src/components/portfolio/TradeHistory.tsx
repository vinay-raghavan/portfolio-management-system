'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowUpRight, ArrowDownRight, ChevronLeft, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { portfolioApi } from '@/lib/api';
import { formatCurrency, cn } from '@/lib/utils';
import type { Trade } from '@/types';

interface TradeHistoryProps {
  pageSize?: number;
}

export function TradeHistory({ pageSize = 20 }: TradeHistoryProps) {
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ['trades', page, pageSize],
    queryFn: () => portfolioApi.getTrades(page, pageSize).then((res) => res.data),
  });

  const trades = data?.trades ?? [];
  const totalCount = data?.total_count ?? 0;
  const currentPageSize = data?.page_size ?? pageSize;
  const totalPages = Math.ceil(totalCount / currentPageSize) || 1;

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Trade History</CardTitle>
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

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Trade History ({totalCount})</CardTitle>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {trades.length === 0 ? (
          <p className="text-muted-foreground text-center py-8">
            No trades yet.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b text-sm text-muted-foreground">
                  <th className="text-left py-3 px-3">Date</th>
                  <th className="text-left py-3 px-3">Symbol</th>
                  <th className="text-left py-3 px-3">Side</th>
                  <th className="text-right py-3 px-3">Quantity</th>
                  <th className="text-right py-3 px-3">Price</th>
                  <th className="text-right py-3 px-3">Total</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((trade: Trade) => (
                  <tr key={trade.id} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="py-3 px-3 text-sm text-muted-foreground">
                      {formatDate(trade.executed_at)}
                    </td>
                    <td className="py-3 px-3 font-medium">{trade.symbol}</td>
                    <td className="py-3 px-3">
                      <span
                        className={cn(
                          'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium',
                          trade.side === 'BUY'
                            ? 'bg-profit/10 text-profit'
                            : 'bg-loss/10 text-loss'
                        )}
                      >
                        {trade.side === 'BUY' ? (
                          <ArrowUpRight className="h-3 w-3" />
                        ) : (
                          <ArrowDownRight className="h-3 w-3" />
                        )}
                        {trade.side}
                      </span>
                    </td>
                    <td className="text-right py-3 px-3">{trade.quantity}</td>
                    <td className="text-right py-3 px-3">{formatCurrency(trade.price)}</td>
                    <td className="text-right py-3 px-3 font-medium">
                      {formatCurrency(trade.quantity * trade.price)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

