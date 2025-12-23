'use client';

import { useQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { algoApi } from '@/lib/api';
import { useCurrency } from '@/hooks';
import type { AlgoStrategy } from '@/types';

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

  const losingTrades = strategy.total_trades - strategy.winning_trades;
  const winRate = strategy.total_trades > 0
    ? ((strategy.winning_trades / strategy.total_trades) * 100).toFixed(1)
    : '0.0';

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

      {/* Performance Stats */}
      <div>
        <h4 className="text-sm font-medium text-muted-foreground mb-2">Performance</h4>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Total Trades:</span>{' '}
            <span className="font-medium">{strategy.total_trades}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Winning:</span>{' '}
            <span className="font-medium text-green-500">{strategy.winning_trades}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Losing:</span>{' '}
            <span className="font-medium text-red-500">{losingTrades}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Win Rate:</span>{' '}
            <span className="font-medium">{winRate}%</span>
          </div>
          <div>
            <span className="text-muted-foreground">Total P&L:</span>{' '}
            <span className={`font-medium ${strategy.total_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {formatPrice(strategy.total_pnl)}
            </span>
          </div>
        </div>
      </div>

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

