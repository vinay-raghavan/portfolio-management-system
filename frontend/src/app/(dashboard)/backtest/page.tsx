'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Play,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Calendar,
  DollarSign,
  Percent,
  Activity,
  Trash2,
  Eye,
  RefreshCw,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { backtestApi, BacktestResult, BacktestListItem } from '@/lib/api';
import { formatPercent, safeToFixed, cn } from '@/lib/utils';
import { useCurrency } from '@/hooks';
import { EquityCurveChart } from '@/components/charts/EquityCurveChart';
import { BrandedSpinner, SkeletonTable, ProgressIndicator } from '@/components/shared';

export default function BacktestPage() {
  const { format: formatPrice } = useCurrency();
  const queryClient = useQueryClient();
  const [selectedBacktest, setSelectedBacktest] = useState<BacktestResult | null>(null);

  // Form state
  const [symbol, setSymbol] = useState('AAPL');
  const [strategyName, setStrategyName] = useState('');
  const [startDate, setStartDate] = useState(
    new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  );
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [initialCapital, setInitialCapital] = useState('100000');

  const { data: backtests, isLoading: backtestsLoading } = useQuery({
    queryKey: ['backtests'],
    queryFn: () => backtestApi.getBacktests().then((res) => res.data),
  });

  const { data: strategies } = useQuery({
    queryKey: ['backtest-strategies'],
    queryFn: () => backtestApi.getStrategies().then((res) => res.data),
  });

  const runMutation = useMutation({
    mutationFn: () =>
      backtestApi.runBacktest({
        symbol: symbol.toUpperCase(),
        strategy_name: strategyName,
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
        initial_capital: parseFloat(initialCapital),
      }),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['backtests'] });
      setSelectedBacktest(response.data);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => backtestApi.deleteBacktest(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backtests'] });
    },
  });

  const viewBacktest = async (id: string) => {
    const response = await backtestApi.getBacktest(id);
    setSelectedBacktest(response.data);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Backtesting</h1>
        <p className="text-muted-foreground">
          Test trading strategies on historical data
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Configuration Form */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg">Run Backtest</CardTitle>
            <CardDescription>Configure and run a new backtest</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="symbol">Symbol</Label>
              <Input
                id="symbol"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                placeholder="e.g., AAPL"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="strategy">Strategy</Label>
              <Select value={strategyName} onValueChange={setStrategyName}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a strategy" />
                </SelectTrigger>
                <SelectContent>
                  {strategies?.map((s) => (
                    <SelectItem key={s.name} value={s.name}>
                      {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="startDate">Start Date</Label>
                <Input
                  id="startDate"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="endDate">End Date</Label>
                <Input
                  id="endDate"
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="capital">Initial Capital</Label>
              <Input
                id="capital"
                type="number"
                value={initialCapital}
                onChange={(e) => setInitialCapital(e.target.value)}
              />
            </div>

            <Button
              className="w-full"
              onClick={() => runMutation.mutate()}
              disabled={runMutation.isPending || !strategyName || !symbol}
            >
              {runMutation.isPending ? (
                <RefreshCw className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              Run Backtest
            </Button>

            {runMutation.isError && (
              <p className="text-sm text-destructive">
                Error: {(runMutation.error as Error).message}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Results Display */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">
              {selectedBacktest ? `Results: ${selectedBacktest.symbol}` : 'Backtest Results'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {selectedBacktest ? (
              <div className="space-y-6">
                {/* Performance Metrics */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center p-4 bg-muted rounded-lg">
                    <div className="text-sm text-muted-foreground">Total Return</div>
                    <div
                      className={cn(
                        'text-2xl font-bold',
                        (selectedBacktest.performance.total_return ?? 0) >= 0
                          ? 'text-profit'
                          : 'text-loss'
                      )}
                    >
                      {formatPercent(selectedBacktest.performance.total_return ?? 0)}
                    </div>
                  </div>
                  <div className="text-center p-4 bg-muted rounded-lg">
                    <div className="text-sm text-muted-foreground">Sharpe Ratio</div>
                    <div className="text-2xl font-bold">
                      {selectedBacktest.performance.sharpe_ratio != null
                        ? safeToFixed(selectedBacktest.performance.sharpe_ratio, 2)
                        : 'N/A'}
                    </div>
                  </div>
                  <div className="text-center p-4 bg-muted rounded-lg">
                    <div className="text-sm text-muted-foreground">Max Drawdown</div>
                    <div className="text-2xl font-bold text-loss">
                      {formatPercent(-(selectedBacktest.performance.max_drawdown ?? 0))}
                    </div>
                  </div>
                  <div className="text-center p-4 bg-muted rounded-lg">
                    <div className="text-sm text-muted-foreground">Win Rate</div>
                    <div className="text-2xl font-bold">
                      {formatPercent((selectedBacktest.trade_stats.win_rate ?? 0) * 100)}
                    </div>
                  </div>
                </div>

                {/* Equity Curve */}
                {selectedBacktest.equity_curve && selectedBacktest.equity_curve.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium mb-2">Equity Curve</h4>
                    <EquityCurveChart
                      data={selectedBacktest.equity_curve}
                      initialCapital={selectedBacktest.initial_capital}
                    />
                  </div>
                )}

                {/* Trade Statistics */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">Total Trades:</span>
                    <span className="ml-2 font-medium">
                      {selectedBacktest.trade_stats.total_trades ?? 0}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Winners:</span>
                    <span className="ml-2 font-medium text-profit">
                      {selectedBacktest.trade_stats.winning_trades ?? 0}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Losers:</span>
                    <span className="ml-2 font-medium text-loss">
                      {selectedBacktest.trade_stats.losing_trades ?? 0}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Profit Factor:</span>
                    <span className="ml-2 font-medium">
                      {selectedBacktest.trade_stats.profit_factor != null
                        ? safeToFixed(selectedBacktest.trade_stats.profit_factor, 2)
                        : 'N/A'}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Avg Trade:</span>
                    <span className="ml-2 font-medium">
                      {selectedBacktest.trade_stats.avg_trade
                        ? formatPrice(selectedBacktest.trade_stats.avg_trade)
                        : 'N/A'}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Run a backtest to see results here</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Backtest History */}
      <Card>
        <CardHeader>
          <CardTitle>Backtest History</CardTitle>
        </CardHeader>
        <CardContent>
          {backtestsLoading ? (
            <SkeletonTable rows={3} columns={6} />
          ) : !backtests || backtests.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No backtests yet. Run your first backtest above.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Strategy</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Total Return</TableHead>
                  <TableHead>Sharpe</TableHead>
                  <TableHead>Trades</TableHead>
                  <TableHead>Win Rate</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {backtests.map((bt) => (
                  <TableRow key={bt.id}>
                    <TableCell className="font-medium">{bt.symbol}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{bt.strategy_name}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge
                        className={cn(
                          bt.status === 'COMPLETED' && 'bg-green-500/10 text-green-500',
                          bt.status === 'FAILED' && 'bg-red-500/10 text-red-500',
                          bt.status === 'RUNNING' && 'bg-blue-500/10 text-blue-500'
                        )}
                      >
                        {bt.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span
                        className={cn(
                          'font-medium',
                          (bt.total_return ?? 0) >= 0 ? 'text-profit' : 'text-loss'
                        )}
                      >
                        {bt.total_return != null ? formatPercent(bt.total_return) : '-'}
                      </span>
                    </TableCell>
                    <TableCell>{bt.sharpe_ratio != null ? safeToFixed(bt.sharpe_ratio, 2) : '-'}</TableCell>
                    <TableCell>{bt.total_trades ?? '-'}</TableCell>
                    <TableCell>
                      {bt.win_rate != null ? formatPercent(bt.win_rate * 100) : '-'}
                    </TableCell>
                    <TableCell>{formatDate(bt.created_at)}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => viewBacktest(bt.id)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          disabled={deleteMutation.isPending}
                          onClick={() => deleteMutation.mutate(bt.id)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

