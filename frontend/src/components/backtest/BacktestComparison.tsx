'use client';

import { useState, useMemo } from 'react';
import { useQuery, useQueries } from '@tanstack/react-query';
import { GitCompare, Download, FileText, X, Plus, TrendingUp, TrendingDown } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { backtestApi, BacktestResult, BacktestListItem } from '@/lib/api';
import { formatPercent, safeToFixed, cn } from '@/lib/utils';
import { useCurrency } from '@/hooks';
import { EquityCurveChart } from '@/components/charts/EquityCurveChart';
import { BrandedSpinner } from '@/components/shared';

interface BacktestComparisonProps {
  className?: string;
}

const COMPARISON_COLORS = ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b'];

const METRIC_ROWS = [
  { key: 'total_return', label: 'Total Return', format: 'percent', highlight: true },
  { key: 'annualized_return', label: 'Annualized Return', format: 'percent' },
  { key: 'sharpe_ratio', label: 'Sharpe Ratio', format: 'decimal' },
  { key: 'sortino_ratio', label: 'Sortino Ratio', format: 'decimal' },
  { key: 'max_drawdown', label: 'Max Drawdown', format: 'percent', inverted: true },
  { key: 'calmar_ratio', label: 'Calmar Ratio', format: 'decimal' },
  { key: 'total_trades', label: 'Total Trades', format: 'number' },
  { key: 'win_rate', label: 'Win Rate', format: 'percent' },
  { key: 'profit_factor', label: 'Profit Factor', format: 'decimal' },
  { key: 'avg_win', label: 'Avg Win', format: 'currency' },
  { key: 'avg_loss', label: 'Avg Loss', format: 'currency' },
  { key: 'largest_win', label: 'Largest Win', format: 'currency' },
  { key: 'largest_loss', label: 'Largest Loss', format: 'currency' },
];

export function BacktestComparison({ className }: BacktestComparisonProps) {
  const { format: formatPrice } = useCurrency();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Fetch list of backtests
  const { data: backtests, isLoading: listLoading } = useQuery({
    queryKey: ['backtests'],
    queryFn: () => backtestApi.getBacktests().then((res) => res.data),
  });

  // Fetch full details for selected backtests
  const detailQueries = useQueries({
    queries: selectedIds.map((id) => ({
      queryKey: ['backtest', id],
      queryFn: () => backtestApi.getBacktest(id).then((res) => res.data),
      enabled: !!id,
      staleTime: 5 * 60 * 1000,
    })),
  });

  const selectedBacktests = detailQueries
    .filter((q) => q.data)
    .map((q) => q.data as BacktestResult);

  const isLoadingDetails = detailQueries.some((q) => q.isLoading);

  // Available backtests (completed only)
  const availableBacktests = useMemo(
    () => backtests?.filter((bt) => bt.status === 'COMPLETED') || [],
    [backtests]
  );

  const toggleBacktest = (id: string) => {
    setSelectedIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((i) => i !== id);
      }
      if (prev.length >= 4) return prev; // Max 4 selections
      return [...prev, id];
    });
  };

  const removeBacktest = (id: string) => {
    setSelectedIds((prev) => prev.filter((i) => i !== id));
  };

  const clearSelection = () => setSelectedIds([]);

  // Get metric value from backtest
  const getMetricValue = (backtest: BacktestResult, key: string): number | null => {
    if (key in backtest.performance) {
      return (backtest.performance as unknown as Record<string, number | null>)[key];
    }
    if (key in backtest.trade_stats) {
      return (backtest.trade_stats as unknown as Record<string, number | null>)[key];
    }
    return null;
  };

  // Format value based on type
  const formatValue = (value: number | null, format: string): string => {
    if (value === null || value === undefined) return '-';
    switch (format) {
      case 'percent':
        return formatPercent(value);
      case 'decimal':
        return safeToFixed(value, 2);
      case 'number':
        return value.toString();
      case 'currency':
        return formatPrice(value);
      default:
        return String(value);
    }
  };

  // Find best value for highlighting
  const findBestIndex = (key: string, inverted: boolean = false): number => {
    if (selectedBacktests.length < 2) return -1;
    const values = selectedBacktests.map((bt) => getMetricValue(bt, key));
    const validValues = values.map((v, i) => (v !== null ? { value: v, index: i } : null)).filter(Boolean);
    if (validValues.length < 2) return -1;
    const best = validValues.reduce((a, b) => {
      if (!a || !b) return a || b;
      return inverted ? (a.value < b.value ? a : b) : (a.value > b.value ? a : b);
    });
    return best?.index ?? -1;
  };

  // Export functions (continued below)
  const exportToCSV = () => {
    if (selectedBacktests.length === 0) return;
    const headers = ['Metric', ...selectedBacktests.map((bt) => `${bt.symbol} - ${bt.strategy_name}`)];
    const rows = METRIC_ROWS.map((row) => [
      row.label,
      ...selectedBacktests.map((bt) => formatValue(getMetricValue(bt, row.key), row.format)),
    ]);
    const csv = [headers, ...rows].map((r) => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const timestamp = new Date().toISOString().slice(0, 10);
    a.download = `backtest-comparison-${timestamp}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Export to PDF (simplified - uses browser print)
  const exportToPDF = () => {
    window.print();
  };

  if (listLoading) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center py-12">
          <BrandedSpinner size="lg" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn(className, 'print:shadow-none')}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <GitCompare className="h-5 w-5" />
            Compare Backtests
            {selectedIds.length > 0 && (
              <Badge variant="secondary">{selectedIds.length} selected</Badge>
            )}
          </CardTitle>
          {selectedIds.length >= 2 && (
            <div className="flex gap-2 print:hidden">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Download className="h-4 w-4 mr-2" />
                    Export
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={exportToCSV}>
                    <FileText className="h-4 w-4 mr-2" />
                    Export CSV
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={exportToPDF}>
                    <FileText className="h-4 w-4 mr-2" />
                    Print / PDF
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              <Button variant="ghost" size="sm" onClick={clearSelection}>
                <X className="h-4 w-4 mr-2" />
                Clear
              </Button>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Selection UI */}
        <div className="print:hidden">
          <p className="text-sm text-muted-foreground mb-3">
            Select 2-4 completed backtests to compare side-by-side
          </p>
          <div className="flex flex-wrap gap-2">
            {availableBacktests.map((bt) => {
              const isSelected = selectedIds.includes(bt.id);
              const colorIndex = selectedIds.indexOf(bt.id);
              return (
                <Button
                  key={bt.id}
                  variant={isSelected ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => toggleBacktest(bt.id)}
                  disabled={!isSelected && selectedIds.length >= 4}
                  style={isSelected ? { backgroundColor: COMPARISON_COLORS[colorIndex] } : {}}
                  className={cn(isSelected && 'text-white')}
                >
                  {isSelected && <X className="h-3 w-3 mr-1" />}
                  {bt.symbol} - {bt.strategy_name}
                </Button>
              );
            })}
          </div>
          {availableBacktests.length === 0 && (
            <p className="text-muted-foreground text-center py-4">
              No completed backtests available. Run some backtests first.
            </p>
          )}
        </div>

        {/* Loading state */}
        {isLoadingDetails && selectedIds.length > 0 && (
          <div className="flex items-center justify-center py-8">
            <BrandedSpinner size="md" />
          </div>
        )}

        {/* Comparison Table */}
        {selectedBacktests.length >= 2 && !isLoadingDetails && (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[180px]">Metric</TableHead>
                  {selectedBacktests.map((bt, idx) => (
                    <TableHead key={bt.id} className="text-center min-w-[150px]">
                      <div
                        className="flex items-center justify-center gap-2"
                        style={{ color: COMPARISON_COLORS[idx] }}
                      >
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: COMPARISON_COLORS[idx] }}
                        />
                        <span className="font-semibold">{bt.symbol}</span>
                      </div>
                      <div className="text-xs text-muted-foreground">{bt.strategy_name}</div>
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {METRIC_ROWS.map((row) => {
                  const bestIdx = findBestIndex(row.key, row.inverted);
                  return (
                    <TableRow key={row.key} className={row.highlight ? 'bg-muted/50' : ''}>
                      <TableCell className="font-medium">{row.label}</TableCell>
                      {selectedBacktests.map((bt, idx) => {
                        const value = getMetricValue(bt, row.key);
                        const isBest = idx === bestIdx;
                        const isPositive = row.format === 'percent' && value !== null && value > 0;
                        const isNegative = row.format === 'percent' && value !== null && value < 0;
                        return (
                          <TableCell
                            key={bt.id}
                            className={cn(
                              'text-center',
                              isBest && 'font-bold',
                              isPositive && !row.inverted && 'text-profit',
                              isNegative && !row.inverted && 'text-loss',
                              isPositive && row.inverted && 'text-loss',
                              isNegative && row.inverted && 'text-profit'
                            )}
                          >
                            {formatValue(value, row.format)}
                            {isBest && <TrendingUp className="inline h-3 w-3 ml-1 text-profit" />}
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}

        {/* Prompt to select more */}
        {selectedIds.length === 1 && (
          <div className="text-center py-8 text-muted-foreground">
            <Plus className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>Select at least one more backtest to compare</p>
          </div>
        )}

        {selectedIds.length === 0 && availableBacktests.length > 0 && (
          <div className="text-center py-8 text-muted-foreground">
            <GitCompare className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>Select backtests above to start comparing</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
