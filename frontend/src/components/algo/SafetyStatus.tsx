'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Shield, AlertTriangle, RefreshCw, CheckCircle, XCircle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { algoApi } from '@/lib/api';
import { useCurrency } from '@/hooks';
import type { AlgoStrategy } from '@/types';

interface SafetyStatusProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  strategy: AlgoStrategy | null;
}

export function SafetyStatus({ open, onOpenChange, strategy }: SafetyStatusProps) {
  const { format: formatPrice } = useCurrency();
  const queryClient = useQueryClient();

  const { data: circuitBreaker, isLoading } = useQuery({
    queryKey: ['circuit-breaker', strategy?.id],
    queryFn: () => algoApi.getCircuitBreakerStatus(strategy!.id).then((res) => res.data),
    enabled: !!strategy?.id && open,
    refetchInterval: 5000,
  });

  const resetMutation = useMutation({
    mutationFn: () => algoApi.resetCircuitBreaker(strategy!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['circuit-breaker', strategy?.id] });
    },
  });

  // Helper to safely convert to number
  const toNum = (val: unknown): number => {
    const num = Number(val);
    return Number.isFinite(num) ? num : 0;
  };

  const dailyLossPercent = circuitBreaker && toNum(circuitBreaker.max_daily_loss) > 0
    ? (toNum(circuitBreaker.daily_loss) / toNum(circuitBreaker.max_daily_loss)) * 100
    : 0;

  const consecutiveLossPercent = circuitBreaker && toNum(circuitBreaker.max_consecutive_losses) > 0
    ? (toNum(circuitBreaker.consecutive_losses) / toNum(circuitBreaker.max_consecutive_losses)) * 100
    : 0;

  const drawdownPercent = circuitBreaker && toNum(circuitBreaker.max_drawdown_percent) > 0
    ? (toNum(circuitBreaker.current_drawdown_percent) / toNum(circuitBreaker.max_drawdown_percent)) * 100
    : 0;

  const dailyProfitPercent = circuitBreaker && circuitBreaker.max_daily_profit && toNum(circuitBreaker.max_daily_profit) > 0
    ? (toNum(circuitBreaker.daily_profit) / toNum(circuitBreaker.max_daily_profit)) * 100
    : 0;

  const overallProfitPercent = circuitBreaker && circuitBreaker.overall_profit_target && toNum(circuitBreaker.overall_profit_target) > 0
    ? (toNum(circuitBreaker.overall_profit) / toNum(circuitBreaker.overall_profit_target)) * 100
    : 0;

  const currentDrawdownPct = toNum(circuitBreaker?.current_drawdown_percent);
  const maxDrawdownPct = toNum(circuitBreaker?.max_drawdown_percent);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Safety Controls
          </DialogTitle>
          <DialogDescription>
            {strategy?.name} - Circuit breaker and risk limits
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-4">
            {/* Circuit Breaker Status */}
            <Card className={circuitBreaker?.is_triggered ? 'border-destructive' : ''}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    {circuitBreaker?.is_triggered ? (
                      <XCircle className="h-4 w-4 text-destructive" />
                    ) : (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    )}
                    Circuit Breaker
                  </span>
                  <Badge variant={circuitBreaker?.is_triggered ? 'destructive' : 'default'}>
                    {circuitBreaker?.is_triggered ? 'TRIGGERED' : 'OK'}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {circuitBreaker?.is_triggered && (
                  <div className="bg-destructive/10 border border-destructive rounded p-3">
                    <p className="text-sm font-medium text-destructive">
                      {circuitBreaker.trigger_reason}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Triggered at: {circuitBreaker.triggered_at
                        ? new Date(circuitBreaker.triggered_at).toLocaleString()
                        : 'Unknown'}
                    </p>
                  </div>
                )}

                {/* Daily Loss Progress */}
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Daily Loss</span>
                    <span className={dailyLossPercent >= 80 ? 'text-destructive' : ''}>
                      {formatPrice(circuitBreaker?.daily_loss ?? 0)} / {formatPrice(circuitBreaker?.max_daily_loss ?? 0)}
                    </span>
                  </div>
                  <Progress
                    value={Math.min(dailyLossPercent, 100)}
                    className={dailyLossPercent >= 80 ? '[&>div]:bg-destructive' : ''}
                  />
                </div>

                {/* Consecutive Losses Progress */}
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Consecutive Losses</span>
                    <span className={consecutiveLossPercent >= 80 ? 'text-destructive' : ''}>
                      {circuitBreaker?.consecutive_losses ?? 0} / {circuitBreaker?.max_consecutive_losses ?? 0}
                    </span>
                  </div>
                  <Progress
                    value={Math.min(consecutiveLossPercent, 100)}
                    className={consecutiveLossPercent >= 80 ? '[&>div]:bg-destructive' : ''}
                  />
                </div>

                {/* Drawdown Progress */}
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Drawdown</span>
                    <span className={drawdownPercent >= 80 ? 'text-destructive' : ''}>
                      {currentDrawdownPct.toFixed(1)}% / {maxDrawdownPct.toFixed(1)}%
                    </span>
                  </div>
                  <Progress
                    value={Math.min(drawdownPercent, 100)}
                    className={drawdownPercent >= 80 ? '[&>div]:bg-destructive' : ''}
                  />
                </div>

                {/* Daily Profit Progress (if profit cutoff is configured) */}
                {circuitBreaker?.max_daily_profit != null && circuitBreaker.max_daily_profit > 0 && (
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Daily Profit</span>
                      <span className={circuitBreaker.profit_cutoff_triggered ? 'text-amber-500' : 'text-green-500'}>
                        {formatPrice(circuitBreaker?.daily_profit ?? 0)} / {formatPrice(circuitBreaker.max_daily_profit)}
                      </span>
                    </div>
                    <Progress
                      value={Math.min(dailyProfitPercent, 100)}
                      className={circuitBreaker.profit_cutoff_triggered ? '[&>div]:bg-amber-500' : '[&>div]:bg-green-500'}
                    />
                  </div>
                )}

                {/* Overall Profit Progress (if profit target is configured) */}
                {circuitBreaker?.overall_profit_target != null && circuitBreaker.overall_profit_target > 0 && (
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Overall Profit</span>
                      <span className={circuitBreaker.profit_cutoff_triggered ? 'text-amber-500' : 'text-green-500'}>
                        {formatPrice(circuitBreaker?.overall_profit ?? 0)} / {formatPrice(circuitBreaker.overall_profit_target)}
                      </span>
                    </div>
                    <Progress
                      value={Math.min(overallProfitPercent, 100)}
                      className={circuitBreaker.profit_cutoff_triggered ? '[&>div]:bg-amber-500' : '[&>div]:bg-green-500'}
                    />
                  </div>
                )}

                {/* Profit Cutoff Status */}
                {circuitBreaker?.profit_cutoff_triggered && (
                  <div className="bg-amber-500/10 border border-amber-500 rounded p-3">
                    <p className="text-sm font-medium text-amber-600">
                      Profit cutoff triggered - Strategy paused to lock in gains
                    </p>
                  </div>
                )}

                {/* Reset Button */}
                {circuitBreaker?.is_triggered && (
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => resetMutation.mutate()}
                    disabled={resetMutation.isPending}
                  >
                    <RefreshCw className={`h-4 w-4 mr-2 ${resetMutation.isPending ? 'animate-spin' : ''}`} />
                    Reset Circuit Breaker
                  </Button>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

