'use client';

import { useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { TrendingUp, TrendingDown, X, ShoppingCart } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { watchlistApi } from '@/lib/api';
import { useWebSocketStore, useTradingStore, useNotificationStore } from '@/store';
import { formatCurrency, formatPercent, cn } from '@/lib/utils';
import type { WatchlistItem } from '@/types';

interface WatchlistTableProps {
  watchlistId: string | null;
}

export function WatchlistTable({ watchlistId }: WatchlistTableProps) {
  const queryClient = useQueryClient();
  const { addNotification } = useNotificationStore();
  const { quickBuy, quickSell } = useTradingStore();
  const { subscribe, unsubscribe, quotes, isConnected } = useWebSocketStore();

  const { data: watchlist, isLoading } = useQuery({
    queryKey: ['watchlist', watchlistId],
    queryFn: () => watchlistApi.getWatchlist(watchlistId!).then((res) => res.data),
    enabled: !!watchlistId,
  });

  const removeMutation = useMutation({
    mutationFn: (symbol: string) => watchlistApi.removeItem(watchlistId!, symbol),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist', watchlistId] });
      queryClient.invalidateQueries({ queryKey: ['watchlists'] });
    },
    onError: (error: any) => {
      addNotification({ type: 'error', title: 'Error', message: error.response?.data?.detail || 'Failed to remove symbol' });
    },
  });

  // Subscribe to WebSocket updates for watchlist symbols
  useEffect(() => {
    if (!watchlist?.items || !isConnected) return;
    const symbols = watchlist.items.map((item: WatchlistItem) => item.symbol);
    if (symbols.length > 0) {
      subscribe(symbols);
      return () => unsubscribe(symbols);
    }
  }, [watchlist?.items, isConnected, subscribe, unsubscribe]);

  if (!watchlistId) {
    return (
      <Card className="flex-1">
        <CardContent className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">Select a watchlist to view symbols</p>
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card className="flex-1">
        <CardHeader>
          <CardTitle>Loading...</CardTitle>
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

  const items = watchlist?.items ?? [];

  return (
    <Card className="flex-1">
      <CardHeader>
        <CardTitle>{watchlist?.name}</CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-muted-foreground text-center py-8">
            No symbols in this watchlist. Add some to get started.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b text-sm text-muted-foreground">
                  <th className="text-left py-3 px-2">Symbol</th>
                  <th className="text-right py-3 px-2">Price</th>
                  <th className="text-right py-3 px-2">Change</th>
                  <th className="text-right py-3 px-2">Change %</th>
                  <th className="text-right py-3 px-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item: WatchlistItem) => {
                  const wsQuote = quotes.get(item.symbol);
                  const price = wsQuote?.price ?? item.current_price ?? 0;
                  const change = wsQuote?.change ?? item.change ?? 0;
                  const changePct = wsQuote?.change_pct ?? item.change_pct ?? 0;
                  const isPositive = change >= 0;

                  return (
                    <tr key={item.id} className="border-b last:border-0 hover:bg-muted/30">
                      <td className="py-3 px-2">
                        <div className="flex items-center gap-2">
                          {isPositive ? (
                            <TrendingUp className="h-4 w-4 text-profit" />
                          ) : (
                            <TrendingDown className="h-4 w-4 text-loss" />
                          )}
                          <span className="font-medium">{item.symbol}</span>
                        </div>
                      </td>
                      <td className="text-right py-3 px-2 font-medium">
                        {formatCurrency(price)}
                      </td>
                      <td className={cn('text-right py-3 px-2', isPositive ? 'text-profit' : 'text-loss')}>
                        {isPositive ? '+' : ''}{formatCurrency(change)}
                      </td>
                      <td className={cn('text-right py-3 px-2', isPositive ? 'text-profit' : 'text-loss')}>
                        {formatPercent(changePct)}
                      </td>
                      <td className="text-right py-3 px-2">
                        <div className="flex justify-end gap-1">
                          <Button size="sm" variant="outline" onClick={() => quickBuy(item.symbol)}>
                            Buy
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => quickSell(item.symbol)}>
                            Sell
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => removeMutation.mutate(item.symbol)}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

