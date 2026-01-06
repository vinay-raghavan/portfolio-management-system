'use client';

import { useQuery } from '@tanstack/react-query';
import { Bot, TrendingUp, TrendingDown, Activity, AlertTriangle } from 'lucide-react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { algoApi } from '@/lib/api';
import { useCurrency } from '@/hooks';
import { cn } from '@/lib/utils';

export function AlgoSummary() {
  const { format: formatPrice } = useCurrency();

  const { data: strategies, isLoading: strategiesLoading } = useQuery({
    queryKey: ['algo-strategies'],
    queryFn: () => algoApi.getStrategies().then((res) => res.data),
    refetchInterval: 30000,
  });

  const { data: pnlSummary, isLoading: pnlLoading } = useQuery({
    queryKey: ['algo-pnl-summary'],
    queryFn: () => algoApi.getPnLSummary().then((res) => res.data),
    refetchInterval: 30000,
  });

  const { data: killSwitch } = useQuery({
    queryKey: ['algo-kill-switch'],
    queryFn: () => algoApi.getKillSwitchStatus().then((res) => res.data),
    refetchInterval: 30000,
  });

  const isLoading = strategiesLoading || pnlLoading;
  const activeCount = strategies?.filter((s) => s.status === 'ACTIVE').length ?? 0;
  const totalStrategies = strategies?.length ?? 0;

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            Algo Trading
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-4 w-40" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            Algo Trading
          </CardTitle>
          <CardDescription>Automated trading performance</CardDescription>
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link href="/algo">View All</Link>
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Kill Switch Warning */}
        {killSwitch?.is_active && (
          <div className="flex items-center gap-2 p-2 bg-destructive/10 rounded-md text-destructive text-sm">
            <AlertTriangle className="h-4 w-4" />
            <span>Kill switch is active - all trading paused</span>
          </div>
        )}

        {/* Summary Stats */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Active Strategies</span>
            </div>
            <p className="text-2xl font-bold">{activeCount} / {totalStrategies}</p>
          </div>
          <div>
            <div className="flex items-center gap-2">
              {(pnlSummary?.total_pnl ?? 0) >= 0 ? (
                <TrendingUp className="h-4 w-4 text-green-500" />
              ) : (
                <TrendingDown className="h-4 w-4 text-red-500" />
              )}
              <span className="text-sm text-muted-foreground">Total P&L</span>
            </div>
            <p className={cn(
              'text-2xl font-bold',
              (pnlSummary?.total_pnl ?? 0) >= 0 ? 'text-green-500' : 'text-red-500'
            )}>
              {formatPrice(pnlSummary?.total_pnl ?? 0)}
            </p>
          </div>
        </div>

        {/* P&L Breakdown */}
        <div className="flex gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Realized: </span>
            <span className={cn(
              'font-medium',
              (pnlSummary?.total_realized_pnl ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'
            )}>
              {formatPrice(pnlSummary?.total_realized_pnl ?? 0)}
            </span>
          </div>
          <div>
            <span className="text-muted-foreground">Unrealized: </span>
            <span className={cn(
              'font-medium',
              (pnlSummary?.total_unrealized_pnl ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'
            )}>
              {formatPrice(pnlSummary?.total_unrealized_pnl ?? 0)}
            </span>
          </div>
        </div>

        {/* Trade Stats */}
        <div className="flex gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Trades: </span>
            <span className="font-medium">{pnlSummary?.total_trades ?? 0}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Win Rate: </span>
            <span className="font-medium">
              {pnlSummary?.win_rate !== undefined
                ? Number(pnlSummary.win_rate).toFixed(1)
                : '0.0'}%
            </span>
          </div>
          <div>
            <Badge variant="outline" className="text-xs">
              {pnlSummary?.open_positions ?? 0} open positions
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

