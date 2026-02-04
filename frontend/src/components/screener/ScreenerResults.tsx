'use client';

import { useState } from 'react';
import { ArrowUpDown, TrendingUp, Eye, Bell, ShoppingCart, Plus, Download, ChevronDown, ChevronUp, Layers, Zap, BarChart3, Activity, Target, CheckCircle2, AlertCircle, Info, Brain } from 'lucide-react';
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
import type { ScreenerResultItem, FilterConfig, InferStrategyResponse } from '@/lib/api';
import { StrategyRecommendationCard } from './StrategyRecommendationCard';

interface ScreenerResultsProps {
  results: ScreenerResultItem[];
  isLoading?: boolean;
  totalScreened?: number;
  duration?: number;
  screenerConfig?: {
    universe: string;
    filters?: FilterConfig[];
    preset?: string;
    min_score?: number;
    top_n?: number;
  };
  onAddToWatchlist?: (symbol: string) => void;
  onViewChart?: (symbol: string) => void;
  onCreateAlert?: (symbol: string) => void;
  onQuickTrade?: (symbol: string, side: 'buy' | 'sell') => void;
  onCreateUniverse?: (data: { name: string; description?: string; symbols: string[]; screenerConfig?: Record<string, unknown>; isDynamic: boolean }) => void;
  onInferStrategy?: () => Promise<InferStrategyResponse | null>;
  onCreateSmartStrategy?: (data: {
    name: string;
    strategyType: string;
    params: Record<string, unknown>;
    productType: 'DELIVERY' | 'INTRADAY' | 'MARGIN';
    symbols: string[];
    filters?: FilterConfig[];
    isDynamic: boolean;
    screenerConfig?: Record<string, unknown>;
  }) => void;
  isInferring?: boolean;
  isCreatingStrategy?: boolean;
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
  onInferStrategy,
  onCreateSmartStrategy,
  isInferring,
  isCreatingStrategy,
}: ScreenerResultsProps) {
  const [sortField, setSortField] = useState<'rank' | 'score' | 'symbol'>('rank');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [showUniverseDialog, setShowUniverseDialog] = useState(false);
  const [universeName, setUniverseName] = useState('');
  const [universeDescription, setUniverseDescription] = useState('');
  const [isDynamic, setIsDynamic] = useState(false);
  const [showSmartStrategyDialog, setShowSmartStrategyDialog] = useState(false);
  const [strategyInference, setStrategyInference] = useState<InferStrategyResponse | null>(null);
  const [smartStrategyDynamic, setSmartStrategyDynamic] = useState(false);

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
      screenerConfig: isDynamic ? (screenerConfig as Record<string, unknown>) : undefined,
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
                {onInferStrategy && screenerConfig?.filters && (
                  <>
                    <DropdownMenuItem
                      onClick={async () => {
                        const inference = await onInferStrategy();
                        if (inference) {
                          setStrategyInference(inference);
                          setShowSmartStrategyDialog(true);
                        }
                      }}
                      disabled={isInferring}
                    >
                      <Brain className="h-4 w-4 mr-2" />
                      {isInferring ? 'Analyzing...' : 'Create Smart Strategy'}
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                  </>
                )}
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
                        <div className="flex items-center justify-end gap-2">
                          {result.grade && (
                            <Badge
                              variant={result.grade.startsWith('A') ? 'default' : result.grade === 'B' ? 'secondary' : 'outline'}
                              className={cn(
                                result.grade === 'A+' && 'bg-green-500',
                                result.grade === 'A' && 'bg-emerald-500',
                                result.grade === 'B' && 'bg-blue-500',
                              )}
                            >
                              {result.grade}
                            </Badge>
                          )}
                          <span className={cn('font-medium', result.score >= 70 ? 'text-profit' : result.score >= 50 ? 'text-warning' : 'text-muted-foreground')}>
                            {result.score.toFixed(0)}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-2 max-w-[200px] truncate text-sm text-muted-foreground" title={result.grade_description || ''}>
                        {result.grade_description || result.reasons[0]}
                      </td>
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
                      <tr className="bg-gradient-to-r from-muted/30 via-muted/20 to-muted/30">
                        <td colSpan={5} className="px-4 py-4">
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {/* Filter Scores Card */}
                            <div className="rounded-lg border bg-card p-3 shadow-sm">
                              <div className="flex items-center gap-2 mb-3">
                                <BarChart3 className="h-4 w-4 text-blue-500" />
                                <h4 className="font-semibold text-sm">Filter Scores</h4>
                              </div>
                              <div className="space-y-2">
                                {Object.entries(result.filter_scores).map(([k, v]) => {
                                  const score = v as number;
                                  const colorClass = score >= 80 ? 'bg-green-500' : score >= 60 ? 'bg-emerald-500' : score >= 40 ? 'bg-yellow-500' : 'bg-red-500';
                                  return (
                                    <div key={k} className="flex items-center justify-between gap-2">
                                      <span className="text-xs text-muted-foreground capitalize">{k.replace(/_/g, ' ')}</span>
                                      <div className="flex items-center gap-2">
                                        <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                                          <div className={cn('h-full rounded-full', colorClass)} style={{ width: `${Math.min(score, 100)}%` }} />
                                        </div>
                                        <span className={cn('text-xs font-medium w-8 text-right', score >= 70 ? 'text-green-600 dark:text-green-400' : score >= 50 ? 'text-yellow-600 dark:text-yellow-400' : 'text-muted-foreground')}>
                                          {score.toFixed(0)}%
                                        </span>
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>

                            {/* Technical Details Card */}
                            <div className="rounded-lg border bg-card p-3 shadow-sm">
                              <div className="flex items-center gap-2 mb-3">
                                <Activity className="h-4 w-4 text-purple-500" />
                                <h4 className="font-semibold text-sm">Technical Signals</h4>
                              </div>
                              <div className="space-y-1.5">
                                {result.reasons.map((r, i) => (
                                  <div key={i} className="flex items-start gap-2">
                                    <CheckCircle2 className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                                    <span className="text-xs text-muted-foreground leading-relaxed">{r}</span>
                                  </div>
                                ))}
                              </div>
                            </div>

                            {/* Analysis Card */}
                            <div className="rounded-lg border bg-card p-3 shadow-sm">
                              <div className="flex items-center gap-2 mb-3">
                                <Target className="h-4 w-4 text-orange-500" />
                                <h4 className="font-semibold text-sm">Detailed Analysis</h4>
                              </div>
                              <div className="space-y-1.5">
                                {(result.reasons_detailed || []).length > 0 ? (
                                  result.reasons_detailed.map((r, i) => {
                                    // Determine icon based on content
                                    const isPositive = r.toLowerCase().includes('strong') || r.toLowerCase().includes('bullish') || r.toLowerCase().includes('above') || r.toLowerCase().includes('high');
                                    const isWarning = r.toLowerCase().includes('moderate') || r.toLowerCase().includes('neutral');
                                    const IconComponent = isPositive ? TrendingUp : isWarning ? AlertCircle : Info;
                                    const iconColor = isPositive ? 'text-green-500' : isWarning ? 'text-yellow-500' : 'text-blue-500';
                                    return (
                                      <div key={i} className="flex items-start gap-2">
                                        <IconComponent className={cn('h-3.5 w-3.5 mt-0.5 shrink-0', iconColor)} />
                                        <span className="text-xs text-muted-foreground leading-relaxed">{r}</span>
                                      </div>
                                    );
                                  })
                                ) : (
                                  <p className="text-xs text-muted-foreground italic">No detailed analysis available</p>
                                )}
                              </div>
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

      {/* Smart Strategy Dialog */}
      <Dialog open={showSmartStrategyDialog} onOpenChange={setShowSmartStrategyDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              Create Smart Strategy
            </DialogTitle>
            <DialogDescription>
              AI-powered strategy recommendation based on your screener filters.
            </DialogDescription>
          </DialogHeader>
          {strategyInference && (
            <div className="py-2">
              <StrategyRecommendationCard
                inference={strategyInference}
                symbolCount={passedSymbols.length}
                onCreateStrategy={(data) => {
                  onCreateSmartStrategy?.({
                    name: data.name,
                    strategyType: data.strategyType,
                    params: data.params,
                    productType: data.productType,
                    symbols: passedSymbols,
                    filters: screenerConfig?.filters,
                    isDynamic: smartStrategyDynamic,
                    screenerConfig: smartStrategyDynamic ? (screenerConfig as Record<string, unknown>) : undefined,
                  });
                  setShowSmartStrategyDialog(false);
                  setStrategyInference(null);
                }}
                isCreating={isCreatingStrategy}
              />
              <div className="flex items-center justify-between mt-4 pt-4 border-t">
                <div className="space-y-0.5">
                  <Label htmlFor="smart-dynamic" className="text-sm">Dynamic Universe</Label>
                  <p className="text-xs text-muted-foreground">
                    Auto-refresh symbols when screener is re-run
                  </p>
                </div>
                <Switch
                  id="smart-dynamic"
                  checked={smartStrategyDynamic}
                  onCheckedChange={setSmartStrategyDynamic}
                  disabled={!screenerConfig}
                />
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  );
}

