'use client';

import { useQuery } from '@tanstack/react-query';
import { TrendingUp, TrendingDown, Activity, AlertTriangle } from 'lucide-react';
import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { algoApi } from '@/lib/api';
import { useCurrency } from '@/hooks';
import { cn } from '@/lib/utils';

/**
 * AlgoSummaryContent - The inner content of AlgoSummary, usable inside the AlgoCarousel.
 * Does not include Card wrapper - that's provided by the parent.
 */
export function AlgoSummaryContent() {
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
      <div className="space-y-3 py-2">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-4 w-40" />
      </div>
    );
  }

  return (
    <div className="space-y-3 py-2">
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
            <span className="text-sm text-muted-foreground">Active</span>
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

      {/* Trade Stats & View All Link */}
      <div className="flex items-center justify-between">
        <div className="flex gap-4 text-sm">
          <span>
            <span className="text-muted-foreground">Win Rate: </span>
            <span className="font-medium">
              {pnlSummary?.win_rate !== undefined
                ? Number(pnlSummary.win_rate).toFixed(1)
                : '0.0'}%
            </span>
          </span>
          <Badge variant="outline" className="text-xs">
            {pnlSummary?.open_positions ?? 0} open
          </Badge>
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link href="/algo">View All</Link>
        </Button>
      </div>
    </div>
  );
}

