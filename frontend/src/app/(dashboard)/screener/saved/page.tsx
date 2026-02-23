'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { formatDistanceToNow, format } from 'date-fns';
import {
  Bookmark, ArrowLeft, Play, Trash2, Settings2, Bot, Clock, RefreshCw, MoreVertical,
  ExternalLink, Eye, Zap, TrendingUp, BarChart3, CheckCircle2, XCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { useToast } from '@/components/ui/use-toast';
import { screenerApi, autoTradeApi, type CustomScreener, type ScreenerRunResponse, type RunFrequency } from '@/lib/api';
import { BrandedSpinner } from '@/components/shared';

function SavedScreenerCard({
  screener,
  onRun,
  onRunAutoTrade,
  onDelete,
  onViewResults,
  onSettings,
  isRunning,
}: {
  screener: CustomScreener;
  onRun: () => void;
  onRunAutoTrade: () => void;
  onDelete: () => void;
  onViewResults: () => void;
  onSettings: () => void;
  isRunning: boolean;
}) {
  const hasAutoTrade = screener.is_auto_trade_enabled;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="flex items-center gap-2 text-lg">
              {screener.name}
              {hasAutoTrade && (
                <Badge variant="default" className="ml-2 text-xs">
                  <Bot className="h-3 w-3 mr-1" /> Auto-Trade
                </Badge>
              )}
            </CardTitle>
            <CardDescription className="mt-1">
              {screener.description || 'No description'}
            </CardDescription>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onRun}>
                <Play className="h-4 w-4 mr-2" /> Run Screener
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onViewResults}>
                <Eye className="h-4 w-4 mr-2" /> View Results
              </DropdownMenuItem>
              {hasAutoTrade && (
                <DropdownMenuItem onClick={onRunAutoTrade}>
                  <Bot className="h-4 w-4 mr-2" /> Run Auto-Trade
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={onSettings}>
                <Zap className="h-4 w-4 mr-2" /> Auto-Trade Settings
              </DropdownMenuItem>
              <Link href={`/screener?load=${screener.id}`}>
                <DropdownMenuItem>
                  <ExternalLink className="h-4 w-4 mr-2" /> Edit Filters
                </DropdownMenuItem>
              </Link>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={onDelete} className="text-destructive">
                <Trash2 className="h-4 w-4 mr-2" /> Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4 text-sm mb-4">
          <div>
            <p className="text-muted-foreground">Filters</p>
            <p className="font-medium">{screener.filters.length}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Universe</p>
            <p className="font-medium">{screener.universe}</p>
          </div>
        </div>

        {hasAutoTrade && (
          <div className="border-t pt-3 mt-3 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Schedule:</span>
              <Badge variant="outline" className="capitalize">{screener.run_frequency}</Badge>
            </div>
            {screener.inferred_strategy_type && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Strategy:</span>
                <Badge variant="secondary">{screener.inferred_strategy_type}</Badge>
              </div>
            )}
            {screener.last_run_at && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Last run:</span>
                <span>{formatDistanceToNow(new Date(screener.last_run_at), { addSuffix: true })}</span>
              </div>
            )}
            {screener.next_run_at && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground flex items-center gap-1">
                  <Clock className="h-3 w-3" /> Next run:
                </span>
                <span>{format(new Date(screener.next_run_at), 'MMM d, HH:mm')}</span>
              </div>
            )}
          </div>
        )}

        <div className="flex gap-2 mt-4">
          <Button variant="outline" size="sm" onClick={onRun} disabled={isRunning} className="flex-1">
            {isRunning ? <RefreshCw className="h-4 w-4 mr-1 animate-spin" /> : <Play className="h-4 w-4 mr-1" />}
            Run
          </Button>
          {hasAutoTrade && (
            <Button variant="default" size="sm" onClick={onRunAutoTrade} disabled={isRunning} className="flex-1">
              <Bot className="h-4 w-4 mr-1" /> Auto-Trade
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// View Results Modal - shows last run results
function ViewResultsModal({
  screener,
  open,
  onClose,
}: {
  screener: CustomScreener | null;
  open: boolean;
  onClose: () => void;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ['screener-run', screener?.id],
    queryFn: () => screenerApi.runCustomScreener(screener!.id),
    enabled: open && !!screener,
    staleTime: 60000, // Cache for 1 minute
  });

  const results = data?.data;

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Eye className="h-5 w-5" />
            Results: {screener?.name}
          </DialogTitle>
          <DialogDescription>
            {screener?.last_run_at
              ? `Last run: ${formatDistanceToNow(new Date(screener.last_run_at), { addSuffix: true })}`
              : 'Run screener to see results'}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <BrandedSpinner size="lg" />
            </div>
          ) : results ? (
            <div className="space-y-4">
              {/* Summary stats */}
              <div className="grid grid-cols-3 gap-4 p-3 bg-muted/50 rounded-lg">
                <div className="text-center">
                  <p className="text-2xl font-bold">{results.passed_count}</p>
                  <p className="text-xs text-muted-foreground">Passed</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold">{results.total_screened}</p>
                  <p className="text-xs text-muted-foreground">Screened</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold">{results.duration_ms}ms</p>
                  <p className="text-xs text-muted-foreground">Duration</p>
                </div>
              </div>

              {/* Results table */}
              {results.results.length > 0 ? (
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="text-left p-2 font-medium">Rank</th>
                        <th className="text-left p-2 font-medium">Symbol</th>
                        <th className="text-center p-2 font-medium">Score</th>
                        <th className="text-center p-2 font-medium">Grade</th>
                        <th className="text-center p-2 font-medium">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.results.slice(0, 15).map((item) => (
                        <tr key={item.symbol} className="border-t">
                          <td className="p-2 font-mono text-muted-foreground">{item.rank}</td>
                          <td className="p-2 font-medium">{item.symbol}</td>
                          <td className="p-2 text-center">
                            <Badge variant="outline">{item.score.toFixed(1)}</Badge>
                          </td>
                          <td className="p-2 text-center">
                            <Badge variant="secondary">{item.grade}</Badge>
                          </td>
                          <td className="p-2 text-center">
                            {item.passed ? (
                              <CheckCircle2 className="h-4 w-4 text-green-500 inline" />
                            ) : (
                              <XCircle className="h-4 w-4 text-muted-foreground inline" />
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {results.results.length > 15 && (
                    <p className="text-xs text-muted-foreground p-2 border-t text-center">
                      Showing top 15 of {results.results.length} results
                    </p>
                  )}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  No stocks passed the filters
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              Run the screener to see results
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Auto-trade settings modal for quick configuration
const RUN_FREQUENCIES: { value: RunFrequency; label: string }[] = [
  { value: 'daily', label: 'Daily' },
  { value: 'hourly', label: 'Hourly' },
  { value: 'manual', label: 'Manual' },
];

function AutoTradeSettingsModal({
  screener,
  open,
  onClose,
  onSaved,
}: {
  screener: CustomScreener | null;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { toast } = useToast();
  const [isEnabled, setIsEnabled] = useState(screener?.is_auto_trade_enabled ?? false);
  const [frequency, setFrequency] = useState<RunFrequency>((screener?.run_frequency as RunFrequency) ?? 'daily');
  const [runTime, setRunTime] = useState(screener?.run_time ?? '09:20');

  // Reset state when screener changes
  useState(() => {
    if (screener) {
      setIsEnabled(screener.is_auto_trade_enabled);
      setFrequency((screener.run_frequency as RunFrequency) || 'daily');
      setRunTime(screener.run_time || '09:20');
    }
  });

  const linkMutation = useMutation({
    mutationFn: () => screenerApi.linkAutoTrade(screener!.id, {
      run_frequency: frequency,
      run_time: frequency === 'daily' ? runTime : undefined,
    }),
    onSuccess: () => {
      toast({ title: 'Auto-trade enabled', description: `Schedule set to ${frequency}` });
      onSaved();
      onClose();
    },
    onError: () => toast({ title: 'Error', description: 'Failed to update settings', variant: 'destructive' }),
  });

  const unlinkMutation = useMutation({
    mutationFn: () => screenerApi.unlinkAutoTrade(screener!.id),
    onSuccess: () => {
      toast({ title: 'Auto-trade disabled' });
      onSaved();
      onClose();
    },
    onError: () => toast({ title: 'Error', description: 'Failed to disable auto-trade', variant: 'destructive' }),
  });

  const handleSave = () => {
    if (isEnabled) {
      linkMutation.mutate();
    } else {
      unlinkMutation.mutate();
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            Auto-Trade Settings
          </DialogTitle>
          <DialogDescription>
            Configure auto-trading for &quot;{screener?.name}&quot;
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Enable toggle */}
          <div className="flex items-center justify-between">
            <div>
              <Label>Enable Auto-Trade</Label>
              <p className="text-sm text-muted-foreground">Automatically create trades from this screener</p>
            </div>
            <Switch checked={isEnabled} onCheckedChange={setIsEnabled} />
          </div>

          {isEnabled && (
            <>
              {/* Frequency */}
              <div className="space-y-2">
                <Label>Run Frequency</Label>
                <Select value={frequency} onValueChange={(v) => setFrequency(v as RunFrequency)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {RUN_FREQUENCIES.map((f) => (
                      <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Run time (for daily) */}
              {frequency === 'daily' && (
                <div className="space-y-2">
                  <Label>Run Time</Label>
                  <Input
                    type="time"
                    value={runTime}
                    onChange={(e) => setRunTime(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">Time to run the screener daily</p>
                </div>
              )}

              {/* Strategy info */}
              {screener?.inferred_strategy_type && (
                <div className="p-3 bg-muted/50 rounded-lg">
                  <div className="flex items-center gap-2 text-sm">
                    <TrendingUp className="h-4 w-4" />
                    <span className="text-muted-foreground">Strategy:</span>
                    <Badge variant="secondary">{screener.inferred_strategy_type}</Badge>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave} disabled={linkMutation.isPending || unlinkMutation.isPending}>
            {linkMutation.isPending || unlinkMutation.isPending ? 'Saving...' : 'Save Settings'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function SavedScreenersPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [deleteScreener, setDeleteScreener] = useState<CustomScreener | null>(null);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [viewResultsScreener, setViewResultsScreener] = useState<CustomScreener | null>(null);
  const [settingsScreener, setSettingsScreener] = useState<CustomScreener | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['customScreeners'],
    queryFn: () => screenerApi.getCustomScreeners().then(res => res.data),
  });

  const runMutation = useMutation({
    mutationFn: (id: string) => {
      setRunningId(id);
      return screenerApi.runCustomScreener(id);
    },
    onSuccess: (res) => {
      toast({
        title: 'Screener Complete',
        description: `Found ${res.data.passed_count} stocks out of ${res.data.total_screened}`,
      });
      setRunningId(null);
    },
    onError: (error: any) => {
      toast({ title: 'Error', description: error.response?.data?.detail || 'Failed to run screener', variant: 'destructive' });
      setRunningId(null);
    },
  });

  const runAutoTradeMutation = useMutation({
    mutationFn: (id: string) => {
      setRunningId(id);
      return screenerApi.runAutoTrade(id);
    },
    onSuccess: (res) => {
      toast({
        title: 'Auto-Trade Complete',
        description: `Created ${res.data.trades_created} trades, ${res.data.pending_trades_created} pending`,
      });
      setRunningId(null);
    },
    onError: (error: any) => {
      toast({ title: 'Error', description: error.response?.data?.detail || 'Failed to run auto-trade', variant: 'destructive' });
      setRunningId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => screenerApi.deleteCustomScreener(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customScreeners'] });
      setDeleteScreener(null);
      toast({ title: 'Screener deleted' });
    },
    onError: (error: any) => {
      toast({ title: 'Error', description: error.response?.data?.detail || 'Failed to delete screener', variant: 'destructive' });
    },
  });

  const screeners = data?.screeners ?? [];
  const autoTradeScreeners = screeners.filter(s => s.is_auto_trade_enabled);
  const regularScreeners = screeners.filter(s => !s.is_auto_trade_enabled);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <BrandedSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/screener">
            <Button variant="ghost" size="icon"><ArrowLeft className="h-5 w-5" /></Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <Bookmark className="h-8 w-8" />
              Saved Screeners
            </h1>
            <p className="text-muted-foreground">Manage your saved screener configurations</p>
          </div>
        </div>
        <Link href="/settings/auto-trade">
          <Button variant="outline">
            <Settings2 className="h-4 w-4 mr-2" /> Auto-Trade Settings
          </Button>
        </Link>
      </div>

      {screeners.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Bookmark className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No saved screeners</h3>
            <p className="text-muted-foreground mb-4 text-center">
              Create custom filters and save them for quick access
            </p>
            <Link href="/screener">
              <Button>Go to Screener</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <>
          {autoTradeScreeners.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <Bot className="h-5 w-5" /> Auto-Trade Enabled ({autoTradeScreeners.length})
              </h2>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {autoTradeScreeners.map((screener) => (
                  <SavedScreenerCard
                    key={screener.id}
                    screener={screener}
                    onRun={() => runMutation.mutate(screener.id)}
                    onRunAutoTrade={() => runAutoTradeMutation.mutate(screener.id)}
                    onDelete={() => setDeleteScreener(screener)}
                    onViewResults={() => setViewResultsScreener(screener)}
                    onSettings={() => setSettingsScreener(screener)}
                    isRunning={runningId === screener.id}
                  />
                ))}
              </div>
            </div>
          )}

          {regularScreeners.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-xl font-semibold">
                Regular Screeners ({regularScreeners.length})
              </h2>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {regularScreeners.map((screener) => (
                  <SavedScreenerCard
                    key={screener.id}
                    screener={screener}
                    onRun={() => runMutation.mutate(screener.id)}
                    onRunAutoTrade={() => {}}
                    onDelete={() => setDeleteScreener(screener)}
                    onViewResults={() => setViewResultsScreener(screener)}
                    onSettings={() => setSettingsScreener(screener)}
                    isRunning={runningId === screener.id}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      )}

      <AlertDialog open={!!deleteScreener} onOpenChange={() => setDeleteScreener(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Screener</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &quot;{deleteScreener?.name}&quot;? This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground"
              onClick={() => deleteScreener && deleteMutation.mutate(deleteScreener.id)}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* View Results Modal */}
      <ViewResultsModal
        screener={viewResultsScreener}
        open={!!viewResultsScreener}
        onClose={() => setViewResultsScreener(null)}
      />

      {/* Auto-Trade Settings Modal */}
      <AutoTradeSettingsModal
        screener={settingsScreener}
        open={!!settingsScreener}
        onClose={() => setSettingsScreener(null)}
        onSaved={() => queryClient.invalidateQueries({ queryKey: ['customScreeners'] })}
      />
    </div>
  );
}

