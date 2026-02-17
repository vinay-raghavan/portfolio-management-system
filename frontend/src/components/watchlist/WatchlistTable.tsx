'use client';

import { useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragEndEvent } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { TrendingUp, TrendingDown, X, GripVertical } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { watchlistApi } from '@/lib/api';
import { useWebSocketStore, useTradingStore, useNotificationStore } from '@/store';
import { useCurrency } from '@/hooks/useCurrency';
import { formatPercent, cn } from '@/lib/utils';
import type { WatchlistItem, QuoteUpdate } from '@/types';

interface WatchlistTableProps {
  watchlistId: string | null;
}

interface SortableRowProps {
  item: WatchlistItem;
  wsQuote: QuoteUpdate | undefined;
  formatCurrency: (value: number) => string;
  quickBuy: (symbol: string) => void;
  quickSell: (symbol: string) => void;
  onRemove: (symbol: string) => void;
}

function SortableRow({ item, wsQuote, formatCurrency, quickBuy, quickSell, onRemove }: SortableRowProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: item.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const price = wsQuote?.price ?? item.current_price ?? 0;
  const change = wsQuote?.change ?? item.change ?? 0;
  const changePct = wsQuote?.change_pct ?? item.change_pct ?? 0;
  const isPositive = change >= 0;

  return (
    <tr ref={setNodeRef} style={style} className="border-b last:border-0 hover:bg-muted/30">
      <td className="py-3 px-2 w-8">
        <button className="cursor-grab touch-none text-muted-foreground" {...attributes} {...listeners}>
          <GripVertical className="h-4 w-4" />
        </button>
      </td>
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
            onClick={() => onRemove(item.symbol)}
            aria-label={`Remove ${item.symbol} from watchlist`}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </td>
    </tr>
  );
}

export function WatchlistTable({ watchlistId }: WatchlistTableProps) {
  const queryClient = useQueryClient();
  const { addNotification } = useNotificationStore();
  const { quickBuy, quickSell } = useTradingStore();
  const { subscribe, unsubscribe, quotes, isConnected } = useWebSocketStore();
  const { format: formatCurrency } = useCurrency();

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
    onError: (error: unknown) => {
      const err = error as { response?: { data?: { detail?: string } } };
      addNotification({ type: 'error', title: 'Error', message: err.response?.data?.detail || 'Failed to remove symbol' });
    },
  });

  const reorderMutation = useMutation({
    mutationFn: (items: { id: string; sort_order: number }[]) => watchlistApi.reorderItems(watchlistId!, items),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist', watchlistId] });
    },
    onError: (error: unknown) => {
      const err = error as { response?: { data?: { detail?: string } } };
      addNotification({ type: 'error', title: 'Error', message: err.response?.data?.detail || 'Failed to reorder items' });
    },
  });

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

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

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = items.findIndex((i) => i.id === active.id);
      const newIndex = items.findIndex((i) => i.id === over.id);
      const reordered = arrayMove(items, oldIndex, newIndex);
      const reorderItems = reordered.map((item, index) => ({ id: item.id, sort_order: index }));
      reorderMutation.mutate(reorderItems);
    }
  };

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
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={items.map((i) => i.id)} strategy={verticalListSortingStrategy}>
              <div className="overflow-x-auto">
                <table className="w-full" role="table" aria-label="Watchlist symbols">
                  <thead>
                    <tr className="border-b text-sm text-muted-foreground" role="row">
                      <th className="w-8 py-3 px-2" scope="col" aria-label="Drag handle"></th>
                      <th className="text-left py-3 px-2" scope="col">Symbol</th>
                      <th className="text-right py-3 px-2" scope="col">Price</th>
                      <th className="text-right py-3 px-2" scope="col">Change</th>
                      <th className="text-right py-3 px-2" scope="col">Change %</th>
                      <th className="text-right py-3 px-2" scope="col">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item: WatchlistItem) => (
                      <SortableRow
                        key={item.id}
                        item={item}
                        wsQuote={quotes.get(item.symbol)}
                        formatCurrency={formatCurrency}
                        quickBuy={quickBuy}
                        quickSell={quickSell}
                        onRemove={(symbol) => removeMutation.mutate(symbol)}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            </SortableContext>
          </DndContext>
        )}
      </CardContent>
    </Card>
  );
}

