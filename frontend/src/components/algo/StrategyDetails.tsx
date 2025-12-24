'use client';

import { useQuery } from '@tanstack/react-query';
import { TrendingUp, TrendingDown, Clock, Target, BarChart3 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { algoApi } from '@/lib/api';
import { useCurrency } from '@/hooks';
import { cn } from '@/lib/utils';
import type { AlgoStrategy, StrategyPnL } from '@/types';

interface StrategyDetailsProps {
  strategy: AlgoStrategy;
}

export function StrategyDetails({ strategy }: StrategyDetailsProps) {
  const { format: formatPrice } = useCurrency();

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
  const { data: positions } = useQuery({
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

  // Find this strategy's P&L data
  const strategyPnL: StrategyPnL | undefined = pnlByStrategy?.strategies.find(
    (s) => s.strategy_id === strategy.id
  );

  const losingTrades = strategy.total_trades - strategy.winning_trades;
  const winRate = strategy.total_trades > 0
    ? ((strategy.winning_trades / strategy.total_trades) * 100).toFixed(1)
    : '0.0';

  // Separate open and closed positions
  const openPositions = positions?.filter((p) => p.status === 'OPEN') ?? [];
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
                ? (strategyPnL.win_rate * 100).toFixed(1)
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
        <TabsList className="grid w-full grid-cols-2 max-w-[300px]">
          <TabsTrigger value="positions">Positions ({positions?.length ?? 0})</TabsTrigger>
          <TabsTrigger value="executions">Recent Runs ({executions?.length ?? 0})</TabsTrigger>
        </TabsList>

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
                    <TableHead className="text-right">P&L</TableHead>
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
                        <Badge variant={pos.status === 'OPEN' ? 'outline' : 'secondary'} className="text-xs">
                          {pos.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">{pos.remaining_quantity}/{pos.entry_quantity}</TableCell>
                      <TableCell className="text-right">{formatPrice(pos.entry_price)}</TableCell>
                      <TableCell className="text-right">{pos.exit_price ? formatPrice(pos.exit_price) : '-'}</TableCell>
                      <TableCell className={cn(
                        'text-right font-medium',
                        pos.realized_pnl >= 0 ? 'text-green-500' : 'text-red-500'
                      )}>
                        {formatPrice(pos.realized_pnl)}
                        <span className="text-xs text-muted-foreground ml-1">
                          ({pos.realized_pnl_percent >= 0 ? '+' : ''}{pos.realized_pnl_percent.toFixed(2)}%)
                        </span>
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
                    <TableHead>Started</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Symbols</TableHead>
                    <TableHead className="text-right">Signals</TableHead>
                    <TableHead className="text-right">Orders</TableHead>
                    <TableHead className="text-right">Duration</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {executions.map((exec) => (
                    <TableRow key={exec.id}>
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
                      <TableCell className="text-right">{exec.orders_placed}</TableCell>
                      <TableCell className="text-right text-muted-foreground">
                        {exec.completed_at
                          ? `${((new Date(exec.completed_at).getTime() - new Date(exec.started_at).getTime()) / 1000).toFixed(1)}s`
                          : '-'}
                      </TableCell>
                    </TableRow>
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
    </div>
  );
}

