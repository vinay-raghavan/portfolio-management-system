'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { TrendingUp, TrendingDown, Clock, Target, BarChart3, OctagonX, CircleArrowOutUpRight, Loader2, ChevronDown, ChevronRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

import { algoApi } from '@/lib/api';
import { useCurrency } from '@/hooks';
import { cn } from '@/lib/utils';
import type { AlgoStrategy, StrategyPnL, AlgoPosition, StrategyExecution } from '@/types';

interface StrategyDetailsProps {
  strategy: AlgoStrategy;
}

// Compact execution row with expandable order details
function ExecutionRowCompact({ exec, formatPrice }: { exec: StrategyExecution; formatPrice: (value: number) => string }) {
  const [isOpen, setIsOpen] = useState(false);
  const hasOrders = exec.orders && exec.orders.length > 0;

  return (
    <>
      <TableRow
        className={cn('cursor-pointer hover:bg-muted/50', hasOrders && 'cursor-pointer')}
        onClick={() => hasOrders && setIsOpen(!isOpen)}
      >
        <TableCell className="w-8">
          {hasOrders ? (
            isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />
          ) : (
            <span className="w-4" />
          )}
        </TableCell>
        <TableCell className="text-sm">
          <Clock className="h-3 w-3 inline mr-1" />
          {new Date(exec.started_at).toLocaleString()}
        </TableCell>
        <TableCell>
          <Badge
            variant={
              exec.status === 'COMPLETED' ? 'default' :
              exec.status === 'FAILED' ? 'destructive' :
              'secondary'
            }
            className="text-xs"
          >
            {exec.status}
          </Badge>
        </TableCell>
        <TableCell className="text-right">{exec.symbols_analyzed}</TableCell>
        <TableCell className="text-right">{exec.signals_generated}</TableCell>
        <TableCell className="text-right">
          {exec.orders_placed}
          {exec.orders_filled > 0 && (
            <span className="text-green-500 ml-1">({exec.orders_filled})</span>
          )}
        </TableCell>
        <TableCell className="text-right">
          {exec.realized_pnl !== 0 && (
            <span className={exec.realized_pnl >= 0 ? 'text-green-500' : 'text-red-500'}>
              {formatPrice(exec.realized_pnl)}
            </span>
          )}
        </TableCell>
        <TableCell className="text-right text-muted-foreground">
          {exec.completed_at && exec.started_at
            ? `${(Math.max(0, (new Date(exec.completed_at).getTime() - new Date(exec.started_at).getTime())) / 1000).toFixed(1)}s`
            : '-'}
        </TableCell>
      </TableRow>
      {hasOrders && isOpen && (
        <TableRow className="bg-muted/30 hover:bg-muted/30">
          <TableCell colSpan={8} className="p-0">
            <div className="p-3 pl-10">
              <div className="text-xs font-medium mb-2">Order Details</div>
              <div className="grid gap-2">
                {exec.orders.map((order) => (
                  <div key={order.id} className="flex items-center gap-3 text-xs border rounded p-2 bg-background">
                    <Badge variant={order.side === 'BUY' ? 'default' : 'destructive'} className="text-xs">
                      {order.side === 'BUY' ? (
                        <TrendingUp className="h-3 w-3 mr-1" />
                      ) : (
                        <TrendingDown className="h-3 w-3 mr-1" />
                      )}
                      {order.side}
                    </Badge>
                    <span className="font-medium">{order.symbol}</span>
                    <span className="text-muted-foreground">{order.order_type}</span>
                    <span>Qty: {order.quantity}</span>
                    {order.price && <span>@ {formatPrice(order.price)}</span>}
                    <Badge
                      variant={
                        order.order_status === 'FILLED' ? 'default' :
                        order.order_status === 'REJECTED' ? 'destructive' :
                        'secondary'
                      }
                      className="text-xs"
                    >
                      {order.order_status}
                    </Badge>
                    {order.filled_quantity > 0 && (
                      <span className="text-green-500">
                        Filled: {order.filled_quantity} @ {order.filled_price ? formatPrice(order.filled_price) : '-'}
                      </span>
                    )}
                    {order.signal_type && (
                      <Badge variant="outline" className="text-xs ml-auto">
                        {order.signal_type}
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

export function StrategyDetails({ strategy }: StrategyDetailsProps) {
  const { format: formatPrice } = useCurrency();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // State for dialogs
  const [closePositionDialog, setClosePositionDialog] = useState<AlgoPosition | null>(null);
  const [squareOffDialog, setSquareOffDialog] = useState(false);

  // Fetch universe details if strategy has a universe
  const { data: universe } = useQuery({
    queryKey: ['universe', strategy.universe_id],
    queryFn: () => algoApi.getUniverse(strategy.universe_id!).then((res) => res.data),
    enabled: !!strategy.universe_id,
  });

  // Fetch P&L by strategy to get detailed P&L for this strategy
  const { data: pnlByStrategy } = useQuery({
    queryKey: ['algo-pnl-by-strategy'],
    queryFn: () => algoApi.getPnLByStrategy().then((res) => res.data),
    refetchInterval: 30000,
  });

  // Fetch positions for this strategy
  const { data: positions, refetch: refetchPositions } = useQuery({
    queryKey: ['algo-positions', strategy.id],
    queryFn: () => algoApi.getPositions(strategy.id).then((res) => res.data),
    refetchInterval: 30000,
  });

  // Fetch recent executions for this strategy
  const { data: executions } = useQuery({
    queryKey: ['algo-executions', strategy.id],
    queryFn: () => algoApi.getExecutionHistory(strategy.id, 5).then((res) => res.data),
    refetchInterval: 30000,
  });

  // Close position mutation
  const closePositionMutation = useMutation({
    mutationFn: ({ symbol }: { symbol: string }) =>
      algoApi.closePosition(strategy.id, symbol),
    onSuccess: (response) => {
      toast({
        title: 'Position Closed',
        description: response.data.message,
      });
      refetchPositions();
      queryClient.invalidateQueries({ queryKey: ['algo-pnl-by-strategy'] });
      queryClient.invalidateQueries({ queryKey: ['algo-strategies'] });
      setClosePositionDialog(null);
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to Close Position',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // Square off strategy mutation
  const squareOffMutation = useMutation({
    mutationFn: () => algoApi.squareOffStrategy(strategy.id),
    onSuccess: (response) => {
      toast({
        title: 'Strategy Squared Off',
        description: `Closed ${response.data.positions_closed} positions. Total P&L: ${formatPrice(response.data.total_realized_pnl)}`,
      });
      refetchPositions();
      queryClient.invalidateQueries({ queryKey: ['algo-pnl-by-strategy'] });
      queryClient.invalidateQueries({ queryKey: ['algo-strategies'] });
      setSquareOffDialog(false);
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to Square Off',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // Find this strategy's P&L data
  const strategyPnL: StrategyPnL | undefined = pnlByStrategy?.strategies.find(
    (s) => s.strategy_id === strategy.id
  );

  const losingTrades = strategy.total_trades - strategy.winning_trades;
  const winRate = strategy.total_trades > 0
    ? ((strategy.winning_trades / strategy.total_trades) * 100).toFixed(1)
    : '0.0';

  // Separate open/partial and closed positions
  const openPositions = positions?.filter((p) => p.status === 'OPEN' || p.status === 'PARTIAL') ?? [];
  const closedPositions = positions?.filter((p) => p.status === 'CLOSED').slice(0, 5) ?? [];

  return (
    <div className="bg-muted/30 p-4 space-y-4">
      {/* Description */}
      {strategy.description && (
        <div>
          <h4 className="text-sm font-medium text-muted-foreground mb-1">Description</h4>
          <p className="text-sm">{strategy.description}</p>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Universe & Symbols */}
        <div>
          <h4 className="text-sm font-medium text-muted-foreground mb-1">Universe</h4>
          {universe ? (
            <div>
              <p className="text-sm font-medium">{universe.name}</p>
              <p className="text-xs text-muted-foreground">{universe.symbols?.length || 0} symbols</p>
            </div>
          ) : strategy.symbols?.length ? (
            <div className="flex flex-wrap gap-1">
              {strategy.symbols.slice(0, 5).map((s) => (
                <Badge key={s} variant="outline" className="text-xs">{s}</Badge>
              ))}
              {strategy.symbols.length > 5 && (
                <Badge variant="outline" className="text-xs">+{strategy.symbols.length - 5} more</Badge>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No symbols configured</p>
          )}
        </div>

        {/* Schedule */}
        <div>
          <h4 className="text-sm font-medium text-muted-foreground mb-1">Schedule</h4>
          <p className="text-sm">{strategy.schedule_type}</p>
          {strategy.interval_seconds && (
            <p className="text-xs text-muted-foreground">Every {strategy.interval_seconds}s</p>
          )}
          {strategy.cron_expression && (
            <p className="text-xs text-muted-foreground font-mono">{strategy.cron_expression}</p>
          )}
        </div>

        {/* Position Sizing */}
        <div>
          <h4 className="text-sm font-medium text-muted-foreground mb-1">Position Sizing</h4>
          <p className="text-sm">{strategy.position_sizing_method.replace(/_/g, ' ')}</p>
          <p className="text-xs text-muted-foreground">Value: {strategy.position_size_value}</p>
        </div>

        {/* Trading Mode */}
        <div>
          <h4 className="text-sm font-medium text-muted-foreground mb-1">Trading Mode</h4>
          <Badge variant={strategy.is_paper_trading ? 'secondary' : 'default'}>
            {strategy.is_paper_trading ? 'Paper Trading' : 'Live Trading'}
          </Badge>
        </div>
      </div>

      {/* Risk Parameters */}
      <div>
        <h4 className="text-sm font-medium text-muted-foreground mb-2">Risk Parameters</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Max Position:</span>{' '}
            <span className="font-medium">{formatPrice(strategy.max_position_value || 0)}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Max Daily Loss:</span>{' '}
            <span className="font-medium">{formatPrice(strategy.max_daily_loss)}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Max Consecutive Losses:</span>{' '}
            <span className="font-medium">{strategy.max_consecutive_losses}</span>
          </div>
        </div>
      </div>

      {/* Performance Stats with P&L Breakdown */}
      <div>
        <h4 className="text-sm font-medium text-muted-foreground mb-2 flex items-center gap-2">
          <BarChart3 className="h-4 w-4" />
          Performance & P&L
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Total Trades:</span>{' '}
            <span className="font-medium">{strategyPnL?.total_trades ?? strategy.total_trades}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Winning:</span>{' '}
            <span className="font-medium text-green-500">{strategyPnL?.winning_trades ?? strategy.winning_trades}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Losing:</span>{' '}
            <span className="font-medium text-red-500">{strategyPnL?.losing_trades ?? losingTrades}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Win Rate:</span>{' '}
            <span className="font-medium">
              {strategyPnL?.win_rate !== undefined
                ? Number(strategyPnL.win_rate ?? 0).toFixed(1)
                : winRate}%
            </span>
          </div>
          <div>
            <span className="text-muted-foreground">Realized P&L:</span>{' '}
            <span className={cn(
              'font-medium',
              (strategyPnL?.realized_pnl ?? 0) >= 0 ? 'text-green-500' : 'text-red-500'
            )}>
              {formatPrice(strategyPnL?.realized_pnl ?? 0)}
            </span>
          </div>
          <div>
            <span className="text-muted-foreground">Unrealized P&L:</span>{' '}
            <span className={cn(
              'font-medium',
              (strategyPnL?.unrealized_pnl ?? 0) >= 0 ? 'text-green-500' : 'text-red-500'
            )}>
              {formatPrice(strategyPnL?.unrealized_pnl ?? 0)}
            </span>
          </div>
        </div>
        <div className="mt-2 flex items-center gap-4 text-sm">
          <div className="flex items-center gap-1">
            {(strategyPnL?.total_pnl ?? strategy.total_pnl) >= 0 ? (
              <TrendingUp className="h-4 w-4 text-green-500" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-500" />
            )}
            <span className="text-muted-foreground">Total P&L:</span>{' '}
            <span className={cn(
              'font-bold',
              (strategyPnL?.total_pnl ?? strategy.total_pnl) >= 0 ? 'text-green-500' : 'text-red-500'
            )}>
              {formatPrice(strategyPnL?.total_pnl ?? strategy.total_pnl)}
            </span>
          </div>
          <div className="text-muted-foreground">
            <Target className="h-4 w-4 inline mr-1" />
            {strategyPnL?.open_positions ?? openPositions.length} open positions
          </div>
        </div>
      </div>

      {/* Positions and Executions Tabs */}
      <Tabs defaultValue="positions" className="w-full">
        <div className="flex items-center justify-between mb-2">
          <TabsList className="grid w-full grid-cols-2 max-w-[300px]">
            <TabsTrigger value="positions">Positions ({positions?.length ?? 0})</TabsTrigger>
            <TabsTrigger value="executions">Recent Runs ({executions?.length ?? 0})</TabsTrigger>
          </TabsList>
          {openPositions.length > 0 && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-7 w-7 border-destructive bg-destructive/15 text-destructive hover:bg-destructive hover:text-destructive-foreground"
                    onClick={() => setSquareOffDialog(true)}
                    disabled={squareOffMutation.isPending}
                    aria-label="Exit all positions"
                  >
                    {squareOffMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <OctagonX className="h-4 w-4 fill-current" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Exit All Positions</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>

        <TabsContent value="positions" className="mt-2">
          {positions && positions.length > 0 ? (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Side</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Qty</TableHead>
                    <TableHead className="text-right">Entry</TableHead>
                    <TableHead className="text-right">Exit</TableHead>
                    <TableHead className="text-right">LTP</TableHead>
                    <TableHead className="text-right">Unrealized P&L</TableHead>
                    <TableHead className="text-right">Realized P&L</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {positions.slice(0, 10).map((pos) => (
                    <TableRow key={pos.id}>
                      <TableCell className="font-medium">{pos.symbol}</TableCell>
                      <TableCell>
                        <Badge variant={pos.side === 'BUY' ? 'default' : 'destructive'} className="text-xs">
                          {pos.side}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={pos.status === 'OPEN' ? 'outline' : pos.status === 'PARTIAL' ? 'outline' : 'secondary'}
                          className={cn('text-xs', pos.status === 'PARTIAL' && 'border-yellow-500 text-yellow-600')}
                        >
                          {pos.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">{pos.remaining_quantity}/{pos.entry_quantity}</TableCell>
                      <TableCell className="text-right">{formatPrice(pos.entry_price)}</TableCell>
                      <TableCell className="text-right">
                        {pos.exit_price ? formatPrice(pos.exit_price) : '-'}
                      </TableCell>
                      <TableCell className="text-right">
                        {(pos.status === 'OPEN' || pos.status === 'PARTIAL') && pos.current_price != null
                          ? formatPrice(pos.current_price)
                          : '-'}
                      </TableCell>
                      <TableCell className={cn(
                        'text-right font-medium',
                        (pos.status === 'OPEN' || pos.status === 'PARTIAL')
                          ? (pos.unrealized_pnl ?? 0) >= 0 ? 'text-green-500' : 'text-red-500'
                          : 'text-muted-foreground'
                      )}>
                        {(pos.status === 'OPEN' || pos.status === 'PARTIAL') && pos.unrealized_pnl != null ? (
                          <>
                            {formatPrice(pos.unrealized_pnl)}
                            <span className="text-xs text-muted-foreground ml-1">
                              ({Number(pos.unrealized_pnl_percent ?? 0) >= 0 ? '+' : ''}{Number(pos.unrealized_pnl_percent ?? 0).toFixed(2)}%)
                            </span>
                          </>
                        ) : (pos.status === 'OPEN' || pos.status === 'PARTIAL') ? (
                          <span className="text-muted-foreground">-</span>
                        ) : (
                          <span className="text-muted-foreground">Closed</span>
                        )}
                      </TableCell>
                      <TableCell className={cn(
                        'text-right font-medium',
                        (pos.realized_pnl ?? 0) >= 0 ? 'text-green-500' : 'text-red-500'
                      )}>
                        {formatPrice(pos.realized_pnl ?? 0)}
                        <span className="text-xs text-muted-foreground ml-1">
                          ({Number(pos.realized_pnl_percent ?? 0) >= 0 ? '+' : ''}{Number(pos.realized_pnl_percent ?? 0).toFixed(2)}%)
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        {(pos.status === 'OPEN' || pos.status === 'PARTIAL') && (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="outline"
                                  size="icon"
                                  className="h-7 w-7 border-destructive bg-destructive/15 text-destructive hover:bg-destructive hover:text-destructive-foreground"
                                  onClick={() => setClosePositionDialog(pos)}
                                  disabled={closePositionMutation.isPending}
                                >
                                  <CircleArrowOutUpRight className="h-4 w-4" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>Close Position</TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground py-4 text-center">No positions for this strategy</p>
          )}
        </TabsContent>

        <TabsContent value="executions" className="mt-2">
          {executions && executions.length > 0 ? (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-8"></TableHead>
                    <TableHead>Started</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Symbols</TableHead>
                    <TableHead className="text-right">Signals</TableHead>
                    <TableHead className="text-right">Orders</TableHead>
                    <TableHead className="text-right">P&L</TableHead>
                    <TableHead className="text-right">Duration</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {executions.map((exec) => (
                    <ExecutionRowCompact key={exec.id} exec={exec} formatPrice={formatPrice} />
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground py-4 text-center">No recent executions</p>
          )}
        </TabsContent>
      </Tabs>

      {/* Timestamps */}
      <div className="text-xs text-muted-foreground flex gap-4">
        <span>Created: {new Date(strategy.created_at).toLocaleString()}</span>
        <span>Updated: {new Date(strategy.updated_at).toLocaleString()}</span>
        {strategy.last_run_at && (
          <span>Last Run: {new Date(strategy.last_run_at).toLocaleString()}</span>
        )}
      </div>

      {/* Close Position Confirmation Dialog */}
      <AlertDialog open={!!closePositionDialog} onOpenChange={(open) => !open && setClosePositionDialog(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Close Position</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to close your {closePositionDialog?.symbol} position?
              <br /><br />
              <strong>Position Details:</strong>
              <ul className="mt-2 space-y-1">
                <li>Side: {closePositionDialog?.side}</li>
                <li>Quantity: {closePositionDialog?.remaining_quantity}</li>
                <li>Entry Price: {closePositionDialog ? formatPrice(closePositionDialog.entry_price) : '-'}</li>
              </ul>
              <br />
              The position will be closed at the current market price.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={closePositionMutation.isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => closePositionDialog && closePositionMutation.mutate({ symbol: closePositionDialog.symbol })}
              disabled={closePositionMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {closePositionMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Closing...
                </>
              ) : (
                'Close Position'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Square Off Strategy Confirmation Dialog */}
      <AlertDialog open={squareOffDialog} onOpenChange={setSquareOffDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Exit All Positions</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to close all open positions for strategy &quot;{strategy.name}&quot;?
              <br /><br />
              <strong>This will close {openPositions.length} position(s):</strong>
              <ul className="mt-2 space-y-1 max-h-32 overflow-y-auto">
                {openPositions.map((pos) => (
                  <li key={pos.id}>
                    {pos.symbol}: {pos.side} {pos.remaining_quantity} @ {formatPrice(pos.entry_price)}
                  </li>
                ))}
              </ul>
              <br />
              All positions will be closed at current market prices.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={squareOffMutation.isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => squareOffMutation.mutate()}
              disabled={squareOffMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {squareOffMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Closing All...
                </>
              ) : (
                'Exit All Positions'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

