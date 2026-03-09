'use client';

import React, { useState, useEffect, useRef } from 'react';
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
            <p className="text-muted-foreground">{screener.preset ? 'Preset' : 'Filters'}</p>
            <p className="font-medium capitalize">{screener.preset || (screener.filters?.length ?? 0)}</p>
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

// Auto-trade settings modal - comprehensive all-in-one configuration
const RUN_FREQUENCIES: { value: RunFrequency; label: string; description: string }[] = [
  { value: 'daily', label: 'Daily', description: 'Scan once per day at specified time' },
  { value: 'hourly', label: 'Hourly', description: 'Scan every hour during market hours' },
  { value: 'manual', label: 'Manual Only', description: 'Only scan when you click "Run Now"' },
];

const CONFIRMATION_MODES = [
  { value: 'auto', label: 'Auto-Execute', description: 'Create and activate strategies immediately' },
  { value: 'notify', label: 'Require Approval', description: 'Create pending trades for your review' },
] as const;

const CONFIDENCE_LEVELS = [
  { value: 'low', label: 'Low (40%)', description: 'More trades, lower confidence' },
  { value: 'medium', label: 'Medium (60%)', description: 'Balanced approach' },
  { value: 'high', label: 'High (80%)', description: 'Fewer trades, higher confidence' },
] as const;

type ConfirmationModeValue = 'auto' | 'notify';
type ConfidenceLevelValue = 'low' | 'medium' | 'high';

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
  const queryClient = useQueryClient();

  // Fetch existing config for 'custom' category
  const { data: configsData, isLoading: configLoading } = useQuery({
    queryKey: ['autoTradeConfigs'],
    queryFn: () => autoTradeApi.getConfigs().then(res => res.data),
    enabled: open,
  });

  // Fetch available templates
  const { data: templatesData } = useQuery({
    queryKey: ['strategyTemplates'],
    queryFn: () => autoTradeApi.getTemplates().then(res => res.data),
    enabled: open,
  });

  const existingConfig = configsData?.configs?.find(c => c.category === 'custom');
  const templates = templatesData?.templates ?? [];

  // Form state
  const [isEnabled, setIsEnabled] = useState(false);
  const [frequency, setFrequency] = useState<RunFrequency>('daily');
  const [runTime, setRunTime] = useState('09:20');
  const [confirmationMode, setConfirmationMode] = useState<ConfirmationModeValue>('notify');
  const [templateId, setTemplateId] = useState<string | null>(null);
  const [minConfidence, setMinConfidence] = useState<ConfidenceLevelValue>('medium');
  const [maxPositions, setMaxPositions] = useState(3);
  const [productType, setProductType] = useState<'DELIVERY' | 'INTRADAY' | 'MARGIN' | 'SLB'>('INTRADAY');
  const [signalDirection, setSignalDirection] = useState<'LONG' | 'SHORT' | 'BOTH'>('LONG');

  // Track previous screener ID to detect changes
  const prevScreenerIdRef = useRef<string | undefined>(undefined);

  // Reset form when screener changes or dialog opens with new screener
  // This is an intentional synchronization of form state with props
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (screener && open && screener.id !== prevScreenerIdRef.current) {
      prevScreenerIdRef.current = screener.id;
      setIsEnabled(screener.is_auto_trade_enabled);
      setFrequency((screener.run_frequency as RunFrequency) || 'daily');
      setRunTime(screener.run_time || '09:20');
    }
  }, [screener, open]);

  // Track if config has been loaded to avoid re-setting on every render
  const configLoadedRef = useRef(false);

  // Populate from existing config when loaded
  // This is an intentional one-time initialization from server data
  useEffect(() => {
    if (existingConfig && !configLoadedRef.current) {
      configLoadedRef.current = true;
      setConfirmationMode((existingConfig.confirmation_mode?.toLowerCase() as ConfirmationModeValue) || 'notify');
      setTemplateId(existingConfig.strategy_template_id || null);
      setMinConfidence((existingConfig.min_confidence as ConfidenceLevelValue) || 'medium');
      setMaxPositions(existingConfig.max_positions_per_day || 3);
      setProductType((existingConfig.product_type as 'DELIVERY' | 'INTRADAY' | 'MARGIN' | 'SLB') || 'INTRADAY');
      setSignalDirection((existingConfig.signal_direction as 'LONG' | 'SHORT' | 'BOTH') || 'LONG');
    }
  }, [existingConfig]);
  /* eslint-enable react-hooks/set-state-in-effect */

  // Reset config loaded flag when dialog closes
  useEffect(() => {
    if (!open) {
      configLoadedRef.current = false;
    }
  }, [open]);

  // Create or update AutoTradeConfig
  const configMutation = useMutation({
    mutationFn: async () => {
      const configData = {
        category: 'custom',
        enabled: true,
        confirmation_mode: confirmationMode,
        strategy_template_id: templateId,
        max_positions_per_day: maxPositions,
        min_confidence: minConfidence,
        screener_source_type: 'custom' as const,
        saved_screener_id: screener!.id,
        run_time: runTime,
        product_type: productType,
        signal_direction: signalDirection,
        // Default weights
        weight_technical: 50,
        weight_fundamental: 30,
        weight_sentiment: 20,
      };

      if (existingConfig) {
        return autoTradeApi.updateConfig(existingConfig.id, configData);
      } else {
        return autoTradeApi.createConfig(configData);
      }
    },
  });

  const linkMutation = useMutation({
    mutationFn: () => screenerApi.linkAutoTrade(screener!.id, {
      run_frequency: frequency,
      run_time: frequency === 'daily' ? runTime : undefined,
    }),
  });

  const unlinkMutation = useMutation({
    mutationFn: () => screenerApi.unlinkAutoTrade(screener!.id),
    onSuccess: () => {
      toast({ title: 'Auto-trade disabled' });
      queryClient.invalidateQueries({ queryKey: ['autoTradeConfigs'] });
      onSaved();
      onClose();
    },
    onError: () => toast({ title: 'Error', description: 'Failed to disable auto-trade', variant: 'destructive' }),
  });

  const handleSave = async () => {
    if (!isEnabled) {
      unlinkMutation.mutate();
      return;
    }

    try {
      // First create/update the AutoTradeConfig
      await configMutation.mutateAsync();
      // Then link the screener
      await linkMutation.mutateAsync();

      toast({
        title: 'Auto-trade configured!',
        description: `${confirmationMode === 'auto' ? 'Strategies will be created automatically' : 'Trades will require your approval'}`
      });
      queryClient.invalidateQueries({ queryKey: ['autoTradeConfigs'] });
      onSaved();
      onClose();
    } catch {
      toast({ title: 'Error', description: 'Failed to save auto-trade settings', variant: 'destructive' });
    }
  };

  const isPending = configMutation.isPending || linkMutation.isPending || unlinkMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-primary" />
            Auto-Trade Settings
          </DialogTitle>
          <DialogDescription>
            Configure automatic trading for &quot;{screener?.name}&quot;
          </DialogDescription>
        </DialogHeader>

        {configLoading ? (
          <div className="flex justify-center py-8">
            <BrandedSpinner size="md" />
          </div>
        ) : (
          <div className="space-y-5 py-4">
            {/* Enable toggle */}
            <div className="flex items-center justify-between p-3 border rounded-lg bg-muted/30">
              <div>
                <Label className="text-base font-medium">Enable Auto-Trade</Label>
                <p className="text-sm text-muted-foreground">Create trades when screener finds matches</p>
              </div>
              <Switch checked={isEnabled} onCheckedChange={setIsEnabled} />
            </div>

            {isEnabled && (
              <>
                {/* Schedule Section - When to scan for stocks */}
                <div className="space-y-3 p-3 border rounded-lg bg-muted/30">
                  <div className="flex items-center gap-2 mb-1">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <Label className="font-medium">Screener Schedule</Label>
                  </div>
                  <p className="text-xs text-muted-foreground mb-3">
                    How often to scan for stocks matching your criteria. Found stocks become trading candidates.
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label className="text-xs text-muted-foreground">Scan Frequency</Label>
                      <Select value={frequency} onValueChange={(v) => setFrequency(v as RunFrequency)}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {RUN_FREQUENCIES.map((f) => (
                            <SelectItem key={f.value} value={f.value}>
                              <div className="flex flex-col items-start">
                                <span>{f.label}</span>
                                <span className="text-xs text-muted-foreground">{f.description}</span>
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    {frequency === 'daily' && (
                      <div className="space-y-1">
                        <Label className="text-xs text-muted-foreground">Scan Time (IST)</Label>
                        <Input type="time" value={runTime} onChange={(e) => setRunTime(e.target.value)} />
                      </div>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground italic">
                    💡 Tip: Daily at 09:20 AM runs before market opens, giving you time to review.
                  </p>
                </div>

                {/* Trading Behavior Section - What happens when stocks are found */}
                <div className="space-y-3 p-3 border rounded-lg bg-muted/30">
                  <div className="flex items-center gap-2 mb-1">
                    <Bot className="h-4 w-4 text-muted-foreground" />
                    <Label className="font-medium">Strategy Creation</Label>
                  </div>
                  <p className="text-xs text-muted-foreground mb-3">
                    What happens when the screener finds matching stocks. Created strategies run during market hours.
                  </p>

                  {/* Confirmation Mode */}
                  <div className="space-y-2">
                    <Label className="text-xs text-muted-foreground">When matches are found:</Label>
                    <div className="grid grid-cols-2 gap-2">
                      {CONFIRMATION_MODES.map((mode) => (
                        <button
                          key={mode.value}
                          type="button"
                          onClick={() => setConfirmationMode(mode.value)}
                          className={`p-3 border rounded-lg text-left transition-all ${
                            confirmationMode === mode.value
                              ? 'border-primary bg-primary/5 ring-1 ring-primary'
                              : 'hover:bg-muted/50'
                          }`}
                        >
                          <div className="font-medium text-sm">{mode.label}</div>
                          <div className="text-xs text-muted-foreground">{mode.description}</div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Strategy Template */}
                  <div className="space-y-1">
                    <Label className="text-xs text-muted-foreground">Strategy Template (controls how strategies trade)</Label>
                    <Select value={templateId || 'none'} onValueChange={(v) => setTemplateId(v === 'none' ? null : v)}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a template..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">
                          <span className="text-muted-foreground">Use inferred strategy</span>
                        </SelectItem>
                        {templates.map((t) => (
                          <SelectItem key={t.id} value={t.id}>
                            {t.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      Templates define position sizing, stop-loss, and execution timing for created strategies.
                    </p>
                    {templates.length === 0 && (
                      <p className="text-xs text-amber-600">
                        No templates yet. <Link href="/algo/templates" className="text-primary hover:underline">Create one</Link> to customize trading behavior.
                      </p>
                    )}
                  </div>

                  {/* Product Type & Signal Direction */}
                  <div className="grid grid-cols-2 gap-3 pt-2 border-t">
                    <div className="space-y-1">
                      <Label className="text-xs text-muted-foreground">Product Type</Label>
                      <Select value={productType} onValueChange={(v) => setProductType(v as 'DELIVERY' | 'INTRADAY' | 'MARGIN' | 'SLB')}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="INTRADAY">
                            <div className="flex flex-col items-start">
                              <span>Intraday (MIS)</span>
                              <span className="text-xs text-muted-foreground">25% margin, auto square-off</span>
                            </div>
                          </SelectItem>
                          <SelectItem value="DELIVERY">
                            <div className="flex flex-col items-start">
                              <span>Delivery (CNC)</span>
                              <span className="text-xs text-muted-foreground">Full payment, hold overnight</span>
                            </div>
                          </SelectItem>
                          <SelectItem value="MARGIN">
                            <div className="flex flex-col items-start">
                              <span>Margin (MTF)</span>
                              <span className="text-xs text-muted-foreground">50% margin, multi-day</span>
                            </div>
                          </SelectItem>
                          <SelectItem value="SLB">
                            <div className="flex flex-col items-start">
                              <span>SLB</span>
                              <span className="text-xs text-muted-foreground">50% margin, short selling</span>
                            </div>
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs text-muted-foreground">Signal Direction</Label>
                      <Select value={signalDirection} onValueChange={(v) => setSignalDirection(v as 'LONG' | 'SHORT' | 'BOTH')}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="LONG">
                            <div className="flex flex-col items-start">
                              <span>Long Only</span>
                              <span className="text-xs text-muted-foreground">Buy and hold positions</span>
                            </div>
                          </SelectItem>
                          <SelectItem value="SHORT" disabled={productType === 'DELIVERY' || productType === 'MARGIN'}>
                            <div className="flex flex-col items-start">
                              <span>Short Only</span>
                              <span className="text-xs text-muted-foreground">Sell first, buy later</span>
                            </div>
                          </SelectItem>
                          <SelectItem value="BOTH" disabled={productType === 'DELIVERY' || productType === 'MARGIN'}>
                            <div className="flex flex-col items-start">
                              <span>Both Directions</span>
                              <span className="text-xs text-muted-foreground">Long and short based on signals</span>
                            </div>
                          </SelectItem>
                        </SelectContent>
                      </Select>
                      {(productType === 'DELIVERY' || productType === 'MARGIN') && signalDirection !== 'LONG' && (
                        <p className="text-xs text-amber-600">
                          SHORT/BOTH requires INTRADAY or SLB product type
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Risk Controls Section - Filtering which stocks become strategies */}
                <div className="space-y-3 p-3 border rounded-lg bg-muted/30">
                  <div className="flex items-center gap-2 mb-1">
                    <BarChart3 className="h-4 w-4 text-muted-foreground" />
                    <Label className="font-medium">Filters &amp; Limits</Label>
                  </div>
                  <p className="text-xs text-muted-foreground mb-3">
                    Control which screener results become trading strategies.
                  </p>

                  <div className="grid grid-cols-2 gap-3">
                    {/* Min Confidence */}
                    <div className="space-y-1">
                      <Label className="text-xs text-muted-foreground">Min Score Required</Label>
                      <Select value={minConfidence} onValueChange={(v) => setMinConfidence(v as ConfidenceLevelValue)}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {CONFIDENCE_LEVELS.map((c) => (
                            <SelectItem key={c.value} value={c.value}>
                              <div className="flex flex-col items-start">
                                <span>{c.label}</span>
                                <span className="text-xs text-muted-foreground">{c.description}</span>
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Max Positions */}
                    <div className="space-y-1">
                      <Label className="text-xs text-muted-foreground">Max Strategies/Day</Label>
                      <Input
                        type="number"
                        min={1}
                        max={10}
                        value={maxPositions}
                        onChange={(e) => setMaxPositions(Math.max(1, Math.min(10, parseInt(e.target.value) || 1)))}
                      />
                      <p className="text-xs text-muted-foreground">
                        Limit new strategies created per day
                      </p>
                    </div>
                  </div>
                </div>

                {/* Strategy info */}
                {screener?.inferred_strategy_type && (
                  <div className="p-3 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg">
                    <div className="flex items-center gap-2 text-sm">
                      <TrendingUp className="h-4 w-4 text-blue-600" />
                      <span className="text-muted-foreground">Strategy Type:</span>
                      <Badge variant="secondary">{screener.inferred_strategy_type}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Strategies created from this screener will use {screener.inferred_strategy_type} trading logic.
                    </p>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave} disabled={isPending || configLoading}>
            {isPending ? 'Saving...' : isEnabled ? 'Enable Auto-Trade' : 'Disable Auto-Trade'}
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

