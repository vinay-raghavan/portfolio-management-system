'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  MoreHorizontal,
  Target,
  XCircle,
  TrendingUp,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
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
import { algoApi, tradingApi } from '@/lib/api';
import type { Position, UnrealizedPnLPosition } from '@/types';

// Unified position type that works for both portfolio and algo positions
export interface UnifiedPosition {
  id: string;
  symbol: string;
  quantity: number;
  side?: 'LONG' | 'SHORT' | 'BUY' | 'SELL' | string;
  unrealized_pnl?: number | null;
  unrealized_pnl_pct?: number | null;
  // Algo-specific fields
  strategy_id?: string;
  entry_price?: number;
  current_price?: number | null;
  // Portfolio-specific fields
  avg_cost?: number;
  market_value?: number | null;
}

interface PositionActionsMenuProps {
  position: UnifiedPosition;
  context: 'portfolio' | 'algo';
  onProfitBookingClick?: () => void;
  onAddClick?: () => void;
}

export function PositionActionsMenu({
  position,
  context,
  onProfitBookingClick,
  onAddClick,
}: PositionActionsMenuProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);
  const [isClosing, setIsClosing] = useState(false);

  // Close position mutation for algo
  const closeAlgoPositionMutation = useMutation({
    mutationFn: async () => {
      if (!position.strategy_id) throw new Error('Strategy ID required');
      return algoApi.closePosition(position.strategy_id, position.symbol, {});
    },
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['algo-positions'] });
      queryClient.invalidateQueries({ queryKey: ['algo-unrealized-pnl'] });
      queryClient.invalidateQueries({ queryKey: ['algo-pnl-summary'] });
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
      const realizedPnl = Number(response.data?.realized_pnl ?? 0);
      toast({
        title: 'Position Closed',
        description: `Closed ${position.symbol} position. Realized P&L: ₹${realizedPnl.toFixed(2)}`,
      });
      setShowCloseConfirm(false);
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to close position',
        description: error?.response?.data?.detail || error?.message || 'Unknown error',
        variant: 'destructive',
      });
    },
  });

  // Close position for portfolio (creates a sell order)
  const closePortfolioPositionMutation = useMutation({
    mutationFn: async () => {
      return tradingApi.createOrder({
        symbol: position.symbol,
        order_type: 'MARKET',
        side: 'SELL',
        quantity: position.quantity,
        product_type: 'DELIVERY',
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      toast({
        title: 'Sell Order Placed',
        description: `Market sell order placed for ${position.quantity} shares of ${position.symbol}`,
      });
      setShowCloseConfirm(false);
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to place sell order',
        description: error?.response?.data?.detail || error?.message || 'Unknown error',
        variant: 'destructive',
      });
    },
  });

  const handleClosePosition = async () => {
    setIsClosing(true);
    try {
      if (context === 'algo') {
        await closeAlgoPositionMutation.mutateAsync();
      } else {
        await closePortfolioPositionMutation.mutateAsync();
      }
    } finally {
      setIsClosing(false);
    }
  };

  const pnl = Number(position.unrealized_pnl ?? 0);
  const isProfit = pnl >= 0;

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <MoreHorizontal className="h-4 w-4" />
            <span className="sr-only">Open actions menu</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48">
          <DropdownMenuLabel>{position.symbol} Actions</DropdownMenuLabel>
          <DropdownMenuSeparator />
          
          <DropdownMenuItem onClick={onProfitBookingClick}>
            <Target className="mr-2 h-4 w-4" />
            Set Profit Booking
          </DropdownMenuItem>
          
          {context === 'portfolio' && onAddClick && (
            <DropdownMenuItem onClick={onAddClick}>
              <TrendingUp className="mr-2 h-4 w-4" />
              Add to Position
            </DropdownMenuItem>
          )}
          
          <DropdownMenuSeparator />
          
          <DropdownMenuItem
            className="text-destructive focus:text-destructive"
            onClick={() => setShowCloseConfirm(true)}
          >
            <XCircle className="mr-2 h-4 w-4" />
            {context === 'algo' ? 'Close Position' : 'Sell All'}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Close Position Confirmation Dialog */}
      <AlertDialog open={showCloseConfirm} onOpenChange={setShowCloseConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {context === 'algo' ? 'Close Position?' : 'Sell All Shares?'}
            </AlertDialogTitle>
            <AlertDialogDescription>
              This will {context === 'algo' ? 'close' : 'sell'} your entire position in {position.symbol} ({position.quantity} shares).
              {pnl !== 0 && (
                <span className={isProfit ? 'text-profit' : 'text-loss'}>
                  {' '}Current unrealized P&L: ₹{pnl.toFixed(2)}
                </span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isClosing}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleClosePosition}
              disabled={isClosing}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isClosing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {context === 'algo' ? 'Close Position' : 'Sell All'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

// Helper to convert Position to UnifiedPosition
export function toUnifiedPosition(position: Position): UnifiedPosition {
  return {
    id: position.id,
    symbol: position.symbol,
    quantity: position.quantity,
    side: 'LONG', // Portfolio positions are always long
    unrealized_pnl: position.unrealized_pnl,
    unrealized_pnl_pct: position.unrealized_pnl_pct,
    avg_cost: position.avg_cost,
    current_price: position.current_price,
    market_value: position.market_value,
  };
}

// Helper to convert UnrealizedPnLPosition to UnifiedPosition
export function toUnifiedAlgoPosition(position: UnrealizedPnLPosition): UnifiedPosition {
  return {
    id: position.position_id,
    symbol: position.symbol,
    quantity: position.quantity,
    side: position.side,
    unrealized_pnl: position.unrealized_pnl,
    unrealized_pnl_pct: position.unrealized_pnl_percent,
    strategy_id: position.strategy_id,
    entry_price: position.entry_price,
    current_price: position.current_price,
  };
}

