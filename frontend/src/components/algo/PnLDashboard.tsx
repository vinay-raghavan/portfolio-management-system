'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  BarChart3,
  Calendar,
  Target,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
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
import { AlgoProfitBookingDialog } from './AlgoProfitBookingDialog';
import type { StrategyPnL, AlgoDailyPnL, UnrealizedPnLPosition } from '@/types';

interface PnLDashboardProps {
  className?: string;
}

export function PnLDashboard({ className }: PnLDashboardProps) {
  const { format: formatPrice } = useCurrency();
  const [profitBookingPosition, setProfitBookingPosition] = useState<UnrealizedPnLPosition | null>(null);

  // Fetch P&L summary
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['algo-pnl-summary'],
    queryFn: () => algoApi.getPnLSummary().then((res) => res.data),
    refetchInterval: 30000,
  });

  // Fetch P&L by strategy
  const { data: byStrategy, isLoading: strategyLoading } = useQuery({
    queryKey: ['algo-pnl-by-strategy'],
    queryFn: () => algoApi.getPnLByStrategy().then((res) => res.data),
    refetchInterval: 30000,
  });

  // Fetch P&L history
  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ['algo-pnl-history'],
    queryFn: () => algoApi.getPnLHistory(30).then((res) => res.data),
    refetchInterval: 60000,
  });

  // Fetch unrealized P&L
  const { data: unrealized, isLoading: unrealizedLoading } = useQuery({
    queryKey: ['algo-pnl-unrealized'],
    queryFn: () => algoApi.getUnrealizedPnL().then((res) => res.data),
    refetchInterval: 30000,
  });

  const isLoading = summaryLoading || strategyLoading;

  if (isLoading) {
    return (
      <div className={cn('space-y-4', className)}>
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-32" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <SummaryCard
          title="Total P&L"
          value={summary?.total_pnl ?? 0}
          formatPrice={formatPrice}
          icon={DollarSign}
        />
        <SummaryCard
          title="Realized P&L"
          value={summary?.total_realized_pnl ?? 0}
          formatPrice={formatPrice}
          icon={Target}
        />
        <SummaryCard
          title="Unrealized P&L"
          value={summary?.total_unrealized_pnl ?? 0}
          formatPrice={formatPrice}
          icon={BarChart3}
        />
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {Number(summary?.win_rate ?? 0).toFixed(1)}%
            </div>
            <p className="text-xs text-muted-foreground">
              {summary?.winning_trades ?? 0}W / {summary?.losing_trades ?? 0}L
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs for different views */}
      <Tabs defaultValue="by-strategy" className="space-y-4">
        <TabsList>
          <TabsTrigger value="by-strategy">By Strategy</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
          <TabsTrigger value="positions">Open Positions</TabsTrigger>
        </TabsList>

        <TabsContent value="by-strategy">
          <StrategyPnLTable strategies={byStrategy?.strategies ?? []} formatPrice={formatPrice} />
        </TabsContent>

        <TabsContent value="history">
          <PnLHistoryTable
            dailyPnl={history?.daily_pnl ?? []}
            formatPrice={formatPrice}
            profitableDays={history?.profitable_days ?? 0}
            losingDays={history?.losing_days ?? 0}
          />
        </TabsContent>

        <TabsContent value="positions">
          <UnrealizedPositionsTable
            positions={unrealized?.positions ?? []}
            formatPrice={formatPrice}
            totalUnrealized={unrealized?.total_unrealized_pnl ?? 0}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// Summary Card Component
function SummaryCard({
  title,
  value,
  formatPrice,
  icon: Icon,
}: {
  title: string;
  value: number;
  formatPrice: (v: number) => string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  const isPositive = value >= 0;
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className={cn('text-2xl font-bold', isPositive ? 'text-green-600' : 'text-red-600')}>
          {isPositive ? '+' : ''}{formatPrice(value)}
        </div>
      </CardContent>
    </Card>
  );
}

// Strategy P&L Table
function StrategyPnLTable({
  strategies,
  formatPrice,
}: {
  strategies: StrategyPnL[];
  formatPrice: (v: number) => string;
}) {
  if (strategies.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No strategy P&L data available
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>P&L by Strategy</CardTitle>
        <CardDescription>Performance breakdown for each trading strategy</CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Strategy</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Realized</TableHead>
              <TableHead className="text-right">Unrealized</TableHead>
              <TableHead className="text-right">Total P&L</TableHead>
              <TableHead className="text-right">Win Rate</TableHead>
              <TableHead className="text-right">Trades</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {strategies.map((s) => (
              <TableRow key={s.strategy_id}>
                <TableCell className="font-medium">{s.strategy_name}</TableCell>
                <TableCell>
                  <Badge variant={s.status === 'ACTIVE' ? 'default' : 'secondary'}>
                    {s.status}
                  </Badge>
                </TableCell>
                <TableCell className={cn('text-right', s.realized_pnl >= 0 ? 'text-green-600' : 'text-red-600')}>
                  {formatPrice(s.realized_pnl)}
                </TableCell>
                <TableCell className={cn('text-right', s.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600')}>
                  {formatPrice(s.unrealized_pnl)}
                </TableCell>
                <TableCell className={cn('text-right font-medium', s.total_pnl >= 0 ? 'text-green-600' : 'text-red-600')}>
                  {formatPrice(s.total_pnl)}
                </TableCell>
                <TableCell className="text-right">{Number(s.win_rate ?? 0).toFixed(1)}%</TableCell>
                <TableCell className="text-right">{s.total_trades}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

// P&L History Table
function PnLHistoryTable({
  dailyPnl,
  formatPrice,
  profitableDays,
  losingDays,
}: {
  dailyPnl: AlgoDailyPnL[];
  formatPrice: (v: number) => string;
  profitableDays: number;
  losingDays: number;
}) {
  // Show last 10 days in reverse order (most recent first)
  const recentDays = [...dailyPnl].reverse().slice(0, 10);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Calendar className="h-5 w-5" />
          Daily P&L History
        </CardTitle>
        <CardDescription>
          {profitableDays} profitable days, {losingDays} losing days
        </CardDescription>
      </CardHeader>
      <CardContent>
        {recentDays.length === 0 ? (
          <p className="text-center text-muted-foreground py-8">No P&L history available</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead className="text-right">Realized P&L</TableHead>
                <TableHead className="text-right">Trades Opened</TableHead>
                <TableHead className="text-right">Trades Closed</TableHead>
                <TableHead className="text-right">Cumulative P&L</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recentDays.map((day) => (
                <TableRow key={day.date}>
                  <TableCell>{new Date(day.date).toLocaleDateString()}</TableCell>
                  <TableCell className={cn('text-right', day.realized_pnl >= 0 ? 'text-green-600' : 'text-red-600')}>
                    {day.realized_pnl !== 0 ? formatPrice(day.realized_pnl) : '-'}
                  </TableCell>
                  <TableCell className="text-right">{day.trades_opened || '-'}</TableCell>
                  <TableCell className="text-right">{day.trades_closed || '-'}</TableCell>
                  <TableCell className={cn('text-right font-medium', day.cumulative_pnl >= 0 ? 'text-green-600' : 'text-red-600')}>
                    {formatPrice(day.cumulative_pnl)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

// Unrealized Positions Table
function UnrealizedPositionsTable({
  positions,
  formatPrice,
  totalUnrealized,
}: {
  positions: UnrealizedPnLPosition[];
  formatPrice: (v: number) => string;
  totalUnrealized: number;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Open Positions
        </CardTitle>
        <CardDescription>
          {positions.length} open positions with{' '}
          <span className={totalUnrealized >= 0 ? 'text-green-600' : 'text-red-600'}>
            {formatPrice(totalUnrealized)}
          </span>{' '}
          unrealized P&L
        </CardDescription>
      </CardHeader>
      <CardContent>
        {positions.length === 0 ? (
          <p className="text-center text-muted-foreground py-8">No open positions</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Symbol</TableHead>
                <TableHead>Side</TableHead>
                <TableHead className="text-right">Qty</TableHead>
                <TableHead className="text-right">Entry Price</TableHead>
                <TableHead className="text-right">Current Price</TableHead>
                <TableHead className="text-right">Unrealized P&L</TableHead>
                <TableHead className="text-right">P&L %</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {positions.map((p) => (
                <TableRow key={p.position_id}>
                  <TableCell className="font-medium">{p.symbol}</TableCell>
                  <TableCell>
                    <Badge variant={p.side === 'LONG' ? 'default' : 'destructive'}>
                      {p.side}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">{p.quantity}</TableCell>
                  <TableCell className="text-right">{formatPrice(p.entry_price)}</TableCell>
                  <TableCell className="text-right">{formatPrice(p.current_price)}</TableCell>
                  <TableCell className={cn('text-right font-medium', (p.unrealized_pnl ?? 0) >= 0 ? 'text-green-600' : 'text-red-600')}>
                    {formatPrice(p.unrealized_pnl ?? 0)}
                  </TableCell>
                  <TableCell className={cn('text-right', Number(p.unrealized_pnl_percent ?? 0) >= 0 ? 'text-green-600' : 'text-red-600')}>
                    {Number(p.unrealized_pnl_percent ?? 0) >= 0 ? '+' : ''}{Number(p.unrealized_pnl_percent ?? 0).toFixed(2)}%
                  </TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="outline" onClick={() => setProfitBookingPosition(p)}>
                      <Target className="h-3 w-3" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
      <AlgoProfitBookingDialog
        position={profitBookingPosition}
        open={!!profitBookingPosition}
        onOpenChange={(open) => !open && setProfitBookingPosition(null)}
      />
    </Card>
  );
}
