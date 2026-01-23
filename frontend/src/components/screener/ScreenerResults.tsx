'use client';

import { useState } from 'react';
import { ArrowUpDown, TrendingUp, Eye, Bell, ShoppingCart, Plus, Download, ChevronDown, ChevronUp, Layers, Zap } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { cn, formatPercent } from '@/lib/utils';
import type { ScreenerResultItem, FilterConfig } from '@/lib/api';

interface ScreenerResultsProps {
  results: ScreenerResultItem[];
  isLoading?: boolean;
  totalScreened?: number;
  duration?: number;
  screenerConfig?: {
    universe: string;
    filters: FilterConfig[];
    min_score?: number;
    top_n?: number;
  };
  onAddToWatchlist?: (symbol: string) => void;
  onViewChart?: (symbol: string) => void;
  onCreateAlert?: (symbol: string) => void;
  onQuickTrade?: (symbol: string, side: 'buy' | 'sell') => void;
  onCreateUniverse?: (data: { name: string; description?: string; symbols: string[]; screenerConfig?: object; isDynamic: boolean }) => void;
}

export function ScreenerResults({
  results,
  isLoading,
  totalScreened,
  duration,
  screenerConfig,
  onAddToWatchlist,
  onViewChart,
  onCreateAlert,
  onQuickTrade,
  onCreateUniverse,
}: ScreenerResultsProps) {
  const [sortField, setSortField] = useState<'rank' | 'score' | 'symbol'>('rank');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [showUniverseDialog, setShowUniverseDialog] = useState(false);
  const [universeName, setUniverseName] = useState('');
  const [universeDescription, setUniverseDescription] = useState('');
  const [isDynamic, setIsDynamic] = useState(false);

  const passedSymbols = results.filter((r) => r.passed).map((r) => r.symbol);

  const sortedResults = [...results].sort((a, b) => {
    const mul = sortDir === 'asc' ? 1 : -1;
    if (sortField === 'rank') return (a.rank - b.rank) * mul;
    if (sortField === 'score') return (a.score - b.score) * mul;
    return a.symbol.localeCompare(b.symbol) * mul;
  });

  const toggleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };

  const exportToCsv = () => {
    const headers = ['Rank', 'Symbol', 'Score', 'Passed', 'Reasons'];
    const rows = results.map((r) => [r.rank, r.symbol, r.score.toFixed(2), r.passed ? 'Yes' : 'No', r.reasons.join('; ')]);
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `screener-results-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleCreateUniverse = () => {
    if (!universeName.trim() || passedSymbols.length === 0) return;
    onCreateUniverse?.({
      name: universeName.trim(),
      description: universeDescription.trim() || undefined,
      symbols: passedSymbols,
      screenerConfig: isDynamic ? screenerConfig : undefined,
      isDynamic,
    });
    setShowUniverseDialog(false);
    setUniverseName('');
    setUniverseDescription('');
    setIsDynamic(false);
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Screening...</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 bg-muted rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingUp className="h-5 w-5" />
            Results
          </CardTitle>
          {totalScreened !== undefined && (
            <p className="text-sm text-muted-foreground mt-1">
              {results.length} passed out of {totalScreened} screened
              {duration !== undefined && ` (${duration}ms)`}
            </p>
          )}
        </div>
        <div className="flex gap-2">
          {onCreateUniverse && passedSymbols.length > 0 && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  <Zap className="h-4 w-4 mr-1" />
                  Actions
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => setShowUniverseDialog(true)}>
                  <Layers className="h-4 w-4 mr-2" />
                  Create Universe ({passedSymbols.length} symbols)
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={exportToCsv}>
                  <Download className="h-4 w-4 mr-2" />
                  Export to CSV
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
          {!onCreateUniverse && (
            <Button variant="outline" size="sm" onClick={exportToCsv} disabled={results.length === 0}>
              <Download className="h-4 w-4 mr-1" />
              Export
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {results.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            No results yet. Configure filters and run the screener.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full" role="table">
              <thead>
                <tr className="border-b text-sm text-muted-foreground">
                  <th className="text-left py-3 px-2 cursor-pointer" onClick={() => toggleSort('rank')}>
                    <div className="flex items-center gap-1">Rank <ArrowUpDown className="h-3 w-3" /></div>
                  </th>
                  <th className="text-left py-3 px-2 cursor-pointer" onClick={() => toggleSort('symbol')}>
                    <div className="flex items-center gap-1">Symbol <ArrowUpDown className="h-3 w-3" /></div>
                  </th>
                  <th className="text-right py-3 px-2 cursor-pointer" onClick={() => toggleSort('score')}>
                    <div className="flex items-center justify-end gap-1">Score <ArrowUpDown className="h-3 w-3" /></div>
                  </th>
                  <th className="text-left py-3 px-2">Reasons</th>
                  <th className="text-right py-3 px-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedResults.map((result) => (
                  <>
                    <tr key={result.symbol} className="border-b last:border-0 hover:bg-muted/30 cursor-pointer" onClick={() => setExpandedRow(expandedRow === result.symbol ? null : result.symbol)}>
                      <td className="py-3 px-2">
                        <Badge variant={result.rank <= 3 ? 'default' : 'secondary'}>{result.rank}</Badge>
                      </td>
                      <td className="py-3 px-2 font-medium">{result.symbol}</td>
                      <td className="text-right py-3 px-2">
                        <span className={cn('font-medium', result.score >= 0.7 ? 'text-profit' : result.score >= 0.5 ? 'text-warning' : 'text-muted-foreground')}>
                          {formatPercent(result.score * 100)}
                        </span>
                      </td>
                      <td className="py-3 px-2 max-w-[200px] truncate text-sm text-muted-foreground">{result.reasons[0]}</td>
                      <td className="text-right py-3 px-2">
                        <div className="flex justify-end gap-1">
                          <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); onAddToWatchlist?.(result.symbol); }} title="Add to Watchlist">
                            <Plus className="h-4 w-4" />
                          </Button>
                          <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); onViewChart?.(result.symbol); }} title="View Chart">
                            <Eye className="h-4 w-4" />
                          </Button>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                              <Button size="sm" variant="ghost"><ShoppingCart className="h-4 w-4" /></Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent>
                              <DropdownMenuItem onClick={() => onQuickTrade?.(result.symbol, 'buy')}>Buy</DropdownMenuItem>
                              <DropdownMenuItem onClick={() => onQuickTrade?.(result.symbol, 'sell')}>Sell</DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </td>
                    </tr>
                    {expandedRow === result.symbol && (
                      <tr className="bg-muted/20">
                        <td colSpan={5} className="px-4 py-3">
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <p className="font-medium mb-1">Filter Scores</p>
                              {Object.entries(result.filter_scores).map(([k, v]) => (
                                <p key={k} className="text-muted-foreground">{k}: {(v as number * 100).toFixed(0)}%</p>
                              ))}
                            </div>
                            <div>
                              <p className="font-medium mb-1">All Reasons</p>
                              {result.reasons.map((r, i) => <p key={i} className="text-muted-foreground">• {r}</p>)}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>

      {/* Create Universe Dialog */}
      <Dialog open={showUniverseDialog} onOpenChange={setShowUniverseDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Trading Universe</DialogTitle>
            <DialogDescription>
              Create a universe from {passedSymbols.length} screener results to use in algo strategies.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="universe-name">Universe Name</Label>
              <Input
                id="universe-name"
                placeholder="e.g., Momentum Leaders Q1 2026"
                value={universeName}
                onChange={(e) => setUniverseName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="universe-description">Description (optional)</Label>
              <Input
                id="universe-description"
                placeholder="Brief description of the universe"
                value={universeDescription}
                onChange={(e) => setUniverseDescription(e.target.value)}
              />
            </div>
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="dynamic-universe">Dynamic Universe</Label>
                <p className="text-sm text-muted-foreground">
                  Re-run screener to refresh symbols automatically
                </p>
              </div>
              <Switch
                id="dynamic-universe"
                checked={isDynamic}
                onCheckedChange={setIsDynamic}
                disabled={!screenerConfig}
              />
            </div>
            {!screenerConfig && isDynamic && (
              <p className="text-sm text-warning">
                Screener configuration not available for dynamic refresh
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowUniverseDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateUniverse} disabled={!universeName.trim()}>
              <Layers className="h-4 w-4 mr-2" />
              Create Universe
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

