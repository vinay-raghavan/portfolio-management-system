'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowUpDown, TrendingUp, TrendingDown, X, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { useToast } from '@/components/ui/use-toast';
import { formatPercent, cn } from '@/lib/utils';
import { useTradingStore, useUIStore } from '@/store';
import { useCurrency } from '@/hooks/useCurrency';
import { tradingApi } from '@/lib/api';
import { ProfitBookingDialog } from './ProfitBookingDialog';
import { TrailingStopDialog } from './TrailingStopDialog';
import { PositionActionsMenu, toUnifiedPosition } from '@/components/shared';
import type { Position } from '@/types';

type SortField = 'symbol' | 'quantity' | 'market_value' | 'unrealized_pnl' | 'unrealized_pnl_pct';
type SortDirection = 'asc' | 'desc';

interface PositionsTableProps {
  positions: Position[];
  isLoading?: boolean;
}

export function PositionsTable({ positions, isLoading }: PositionsTableProps) {
  const [sortField, setSortField] = useState<SortField>('market_value');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [profitBookingPosition, setProfitBookingPosition] = useState<Position | null>(null);
  const [trailingStopPosition, setTrailingStopPosition] = useState<Position | null>(null);
  const [squareOffPosition, setSquareOffPosition] = useState<Position | null>(null);
  const [squareOffLoading, setSquareOffLoading] = useState<string | null>(null);
  const router = useRouter();
  const { quickBuy } = useTradingStore();
  const { setSelectedSymbol } = useUIStore();
  const { format: formatCurrency } = useCurrency();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Square off a single position
  const squareOffMutation = useMutation({
    mutationFn: async (position: Position) => {
      return tradingApi.createOrder({
        symbol: position.symbol,
        order_type: 'MARKET',
        side: 'SELL',
        quantity: position.quantity,
        product_type: 'DELIVERY',
      });
    },
    onSuccess: (_, position) => {
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      toast({
        title: 'Position Squared Off',
        description: `Market sell order placed for ${position.quantity} shares of ${position.symbol}`,
      });
      setSquareOffPosition(null);
      setSquareOffLoading(null);
    },
    onError: (error: any, position) => {
      toast({
        title: 'Failed to square off',
        description: error?.response?.data?.detail || error?.message || 'Unknown error',
        variant: 'destructive',
      });
      setSquareOffLoading(null);
    },
  });

  const handleSquareOff = async (position: Position) => {
    setSquareOffLoading(position.id);
    await squareOffMutation.mutateAsync(position);
  };

  const handleNavigateToAnalysis = (symbol: string) => {
    setSelectedSymbol(symbol);
    router.push('/analysis');
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedPositions = [...positions].sort((a, b) => {
    let aVal: number | string = 0;
    let bVal: number | string = 0;

    switch (sortField) {
      case 'symbol':
        aVal = a.symbol;
        bVal = b.symbol;
        break;
      case 'quantity':
        aVal = a.quantity;
        bVal = b.quantity;
        break;
      case 'market_value':
        aVal = a.market_value ?? 0;
        bVal = b.market_value ?? 0;
        break;
      case 'unrealized_pnl':
        aVal = a.unrealized_pnl ?? 0;
        bVal = b.unrealized_pnl ?? 0;
        break;
      case 'unrealized_pnl_pct':
        aVal = a.unrealized_pnl_pct ?? 0;
        bVal = b.unrealized_pnl_pct ?? 0;
        break;
    }

    if (typeof aVal === 'string') {
      return sortDirection === 'asc' 
        ? aVal.localeCompare(bVal as string)
        : (bVal as string).localeCompare(aVal);
    }
    return sortDirection === 'asc' ? aVal - (bVal as number) : (bVal as number) - aVal;
  });

  const SortHeader = ({ field, children }: { field: SortField; children: React.ReactNode }) => (
    <th
      className="text-left py-3 px-3 cursor-pointer hover:bg-muted/50 transition-colors"
      onClick={() => handleSort(field)}
    >
      <div className="flex items-center gap-1">
        {children}
        <ArrowUpDown className={cn(
          'h-3 w-3',
          sortField === field ? 'text-foreground' : 'text-muted-foreground'
        )} />
      </div>
    </th>
  );

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Positions</CardTitle>
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
      <CardHeader>
        <CardTitle>Positions ({positions.length})</CardTitle>
      </CardHeader>
      <CardContent>
        {positions.length === 0 ? (
          <p className="text-muted-foreground text-center py-8">
            No positions yet. Start trading to see your portfolio here.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b text-sm text-muted-foreground">
                  <SortHeader field="symbol">Symbol</SortHeader>
                  <SortHeader field="quantity">Qty</SortHeader>
                  <th className="text-right py-3 px-3">Avg Cost</th>
                  <th className="text-right py-3 px-3">Current</th>
                  <SortHeader field="market_value">Value</SortHeader>
                  <SortHeader field="unrealized_pnl">P&L</SortHeader>
                  <SortHeader field="unrealized_pnl_pct">P&L %</SortHeader>
                  <th className="text-right py-3 px-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedPositions.map((position) => {
                  const pnl = position.unrealized_pnl ?? 0;
                  const pnlPct = position.unrealized_pnl_pct ?? 0;
                  const isProfit = pnl >= 0;

                  return (
                    <tr key={position.id} className="border-b last:border-0 hover:bg-muted/30">
                      <td className="py-3 px-3">
                        <button
                          onClick={() => handleNavigateToAnalysis(position.symbol)}
                          className="flex items-center gap-2 hover:text-primary transition-colors cursor-pointer"
                        >
                          {isProfit ? (
                            <TrendingUp className="h-4 w-4 text-profit" />
                          ) : (
                            <TrendingDown className="h-4 w-4 text-loss" />
                          )}
                          <span className="font-medium underline-offset-2 hover:underline">{position.symbol}</span>
                        </button>
                      </td>
                      <td className="py-3 px-3">{position.quantity}</td>
                      <td className="text-right py-3 px-3">{formatCurrency(position.avg_cost)}</td>
                      <td className="text-right py-3 px-3">
                        {formatCurrency(position.current_price ?? position.avg_cost)}
                      </td>
                      <td className="text-right py-3 px-3 font-medium">
                        {formatCurrency(position.market_value ?? 0)}
                      </td>
                      <td className={cn('text-right py-3 px-3', isProfit ? 'text-profit' : 'text-loss')}>
                        {formatCurrency(pnl)}
                      </td>
                      <td className={cn('text-right py-3 px-3', isProfit ? 'text-profit' : 'text-loss')}>
                        {formatPercent(pnlPct)}
                      </td>
                      <td className="text-right py-3 px-3">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs border-loss text-loss hover:bg-loss hover:text-white"
                            onClick={() => setSquareOffPosition(position)}
                            disabled={squareOffLoading === position.id}
                          >
                            {squareOffLoading === position.id ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <>
                                <X className="h-3 w-3 mr-1" />
                                Square Off
                              </>
                            )}
                          </Button>
                          <PositionActionsMenu
                            position={toUnifiedPosition(position)}
                            context="portfolio"
                            onProfitBookingClick={() => setProfitBookingPosition(position)}
                            onTrailingStopClick={() => setTrailingStopPosition(position)}
                            onAddClick={() => quickBuy(position.symbol)}
                          />
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
      <ProfitBookingDialog
        position={profitBookingPosition}
        open={!!profitBookingPosition}
        onOpenChange={(open) => !open && setProfitBookingPosition(null)}
      />
      <TrailingStopDialog
        position={trailingStopPosition}
        open={!!trailingStopPosition}
        onOpenChange={(open) => !open && setTrailingStopPosition(null)}
      />

      {/* Square Off Confirmation Dialog */}
      <AlertDialog open={!!squareOffPosition} onOpenChange={(open) => !open && setSquareOffPosition(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Square Off Position?</AlertDialogTitle>
            <AlertDialogDescription>
              This will place a market sell order for {squareOffPosition?.quantity} shares of {squareOffPosition?.symbol}.
              {squareOffPosition && (squareOffPosition.unrealized_pnl ?? 0) !== 0 && (
                <span className={(squareOffPosition.unrealized_pnl ?? 0) >= 0 ? 'text-profit' : 'text-loss'}>
                  {' '}Current unrealized P&L: {formatCurrency(squareOffPosition.unrealized_pnl ?? 0)}
                </span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={!!squareOffLoading}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => squareOffPosition && handleSquareOff(squareOffPosition)}
              disabled={!!squareOffLoading}
              className="bg-loss text-white hover:bg-loss/90"
            >
              {squareOffLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <X className="mr-2 h-4 w-4" />
              )}
              Square Off
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}

