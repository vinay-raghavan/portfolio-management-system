'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { algoApi, signalsApi } from '@/lib/api';
import type { AlgoStrategy, AlgoStrategyCreate, ScheduleType, PositionSizingMethod, ProfitCutoffAction } from '@/types';

interface StrategyDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  strategy?: AlgoStrategy | null;
}

const scheduleTypes: { value: ScheduleType; label: string }[] = [
  { value: 'INTERVAL', label: 'Fixed Interval' },
  { value: 'CRON', label: 'Cron Expression' },
  { value: 'MARKET_OPEN', label: 'Market Open' },
  { value: 'MARKET_CLOSE', label: 'Market Close' },
  { value: 'CONTINUOUS', label: 'Continuous' },
];

const positionSizingMethods: { value: PositionSizingMethod; label: string }[] = [
  { value: 'FIXED_QUANTITY', label: 'Fixed Quantity' },
  { value: 'FIXED_AMOUNT', label: 'Fixed Amount' },
  { value: 'PERCENT_OF_PORTFOLIO', label: '% of Portfolio' },
  { value: 'RISK_BASED', label: 'Risk-Based' },
  { value: 'VOLATILITY_ADJUSTED', label: 'Volatility Adjusted' },
];

const profitCutoffActions: { value: ProfitCutoffAction; label: string; description: string }[] = [
  { value: 'PAUSE_STRATEGY', label: 'Pause Strategy', description: 'Stop trading for the day' },
  { value: 'CLOSE_POSITIONS_AND_PAUSE', label: 'Close & Pause', description: 'Close all positions and pause' },
  { value: 'NOTIFY_ONLY', label: 'Notify Only', description: 'Send notification but continue trading' },
];

export function StrategyDialog({ open, onOpenChange, strategy }: StrategyDialogProps) {
  const queryClient = useQueryClient();
  const isEditing = !!strategy;

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [strategyType, setStrategyType] = useState('');
  const [universeId, setUniverseId] = useState<string>('');
  const [symbols, setSymbols] = useState('');
  const [scheduleType, setScheduleType] = useState<ScheduleType>('INTERVAL');
  const [intervalSeconds, setIntervalSeconds] = useState('300');
  const [cronExpression, setCronExpression] = useState('');
  const [positionSizingMethod, setPositionSizingMethod] = useState<PositionSizingMethod>('FIXED_QUANTITY');
  const [positionSizeValue, setPositionSizeValue] = useState('10');
  const [maxPositionValue, setMaxPositionValue] = useState('100000');
  const [maxDailyLoss, setMaxDailyLoss] = useState('10000');
  const [maxConsecutiveLosses, setMaxConsecutiveLosses] = useState('3');
  // Profit cutoff state
  const [maxDailyProfit, setMaxDailyProfit] = useState('');
  const [overallProfitTarget, setOverallProfitTarget] = useState('');
  const [profitCutoffAction, setProfitCutoffAction] = useState<ProfitCutoffAction>('PAUSE_STRATEGY');
  const [isPaperTrading, setIsPaperTrading] = useState(true);

  // Fetch available strategies and universes
  const { data: availableStrategies } = useQuery({
    queryKey: ['signal-strategies'],
    queryFn: () => signalsApi.getStrategies().then((res) => res.data),
  });

  const { data: universes } = useQuery({
    queryKey: ['universes'],
    queryFn: () => algoApi.getUniverses().then((res) => res.data),
  });

  // Reset form when dialog opens/closes or strategy changes
  useEffect(() => {
    if (strategy) {
      setName(strategy.name);
      setDescription(strategy.description || '');
      setStrategyType(strategy.strategy_type);
      setUniverseId(strategy.universe_id || '');
      setSymbols(strategy.symbols?.join(', ') || '');
      setScheduleType(strategy.schedule_type);
      setIntervalSeconds(String(strategy.interval_seconds || 300));
      setCronExpression(strategy.cron_expression || '');
      setPositionSizingMethod(strategy.position_sizing_method);
      setPositionSizeValue(String(strategy.position_size_value));
      setMaxPositionValue(String(strategy.max_position_value || 100000));
      setMaxDailyLoss(String(strategy.max_daily_loss));
      setMaxConsecutiveLosses(String(strategy.max_consecutive_losses));
      // Profit cutoff fields
      setMaxDailyProfit(strategy.max_daily_profit ? String(strategy.max_daily_profit) : '');
      setOverallProfitTarget(strategy.overall_profit_target ? String(strategy.overall_profit_target) : '');
      setProfitCutoffAction(strategy.profit_cutoff_action || 'PAUSE_STRATEGY');
      setIsPaperTrading(strategy.is_paper_trading);
    } else {
      // Reset to defaults
      setName('');
      setDescription('');
      setStrategyType('');
      setUniverseId('');
      setSymbols('');
      setScheduleType('INTERVAL');
      setIntervalSeconds('300');
      setCronExpression('');
      setPositionSizingMethod('FIXED_QUANTITY');
      setPositionSizeValue('10');
      setMaxPositionValue('100000');
      setMaxDailyLoss('10000');
      setMaxConsecutiveLosses('3');
      // Profit cutoff defaults
      setMaxDailyProfit('');
      setOverallProfitTarget('');
      setProfitCutoffAction('PAUSE_STRATEGY');
      setIsPaperTrading(true);
    }
  }, [strategy, open]);

  const createMutation = useMutation({
    mutationFn: (data: AlgoStrategyCreate) => algoApi.createStrategy(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['algo-strategies'] });
      onOpenChange(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: AlgoStrategyCreate) => algoApi.updateStrategy(strategy!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['algo-strategies'] });
      onOpenChange(false);
    },
  });

  const handleSubmit = () => {
    const data: AlgoStrategyCreate = {
      name,
      description: description || undefined,
      strategy_type: strategyType,
      universe_id: universeId || undefined,
      symbols: symbols ? symbols.split(',').map((s) => s.trim().toUpperCase()) : undefined,
      schedule_type: scheduleType,
      interval_seconds: scheduleType === 'INTERVAL' ? parseInt(intervalSeconds) : undefined,
      cron_expression: scheduleType === 'CRON' ? cronExpression : undefined,
      position_sizing_method: positionSizingMethod,
      position_size_value: parseFloat(positionSizeValue),
      max_position_value: parseFloat(maxPositionValue),
      max_daily_loss: parseFloat(maxDailyLoss),
      max_consecutive_losses: parseInt(maxConsecutiveLosses),
      // Profit cutoff fields
      max_daily_profit: maxDailyProfit ? parseFloat(maxDailyProfit) : undefined,
      overall_profit_target: overallProfitTarget ? parseFloat(overallProfitTarget) : undefined,
      profit_cutoff_action: profitCutoffAction,
      is_paper_trading: isPaperTrading,
    };

    if (isEditing) {
      updateMutation.mutate(data);
    } else {
      createMutation.mutate(data);
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit Strategy' : 'Create New Strategy'}</DialogTitle>
          <DialogDescription>
            Configure your automated trading strategy parameters
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="basic" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="basic">Basic</TabsTrigger>
            <TabsTrigger value="universe">Universe</TabsTrigger>
            <TabsTrigger value="schedule">Schedule</TabsTrigger>
            <TabsTrigger value="risk">Risk</TabsTrigger>
          </TabsList>

          <TabsContent value="basic" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="name">Strategy Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="My Trading Strategy"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe your strategy..."
                rows={3}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="strategyType">Strategy Type</Label>
              <Select value={strategyType} onValueChange={setStrategyType}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a strategy" />
                </SelectTrigger>
                <SelectContent className="max-h-[300px]">
                  {/* Group combined/composite strategies */}
                  {availableStrategies?.strategies?.some((s) => s.parameters?.components) && (
                    <>
                      <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                        Combined Strategies ⭐
                      </div>
                      {availableStrategies?.strategies
                        ?.filter((s) => s.parameters?.components)
                        .map((s) => (
                          <SelectItem key={s.name} value={s.name}>
                            <div className="flex items-center gap-2">
                              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200">
                                combo
                              </span>
                              <span>{s.name}</span>
                            </div>
                          </SelectItem>
                        ))}
                    </>
                  )}
                  {/* Group intraday strategies */}
                  <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground mt-2">
                    Intraday Strategies (5m)
                  </div>
                  {availableStrategies?.strategies
                    ?.filter((s) => s.default_timeframe === '5m' && !s.parameters?.components)
                    .map((s) => (
                      <SelectItem key={s.name} value={s.name}>
                        <div className="flex items-center gap-2">
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                            5m
                          </span>
                          <span>{s.name}</span>
                        </div>
                      </SelectItem>
                    ))}
                  {/* Group swing/daily strategies */}
                  <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground mt-2">
                    Swing/Position Strategies (1d)
                  </div>
                  {availableStrategies?.strategies
                    ?.filter((s) => (s.default_timeframe === '1d' || !s.default_timeframe) && !s.parameters?.components)
                    .map((s) => (
                      <SelectItem key={s.name} value={s.name}>
                        <div className="flex items-center gap-2">
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                            1d
                          </span>
                          <span>{s.name}</span>
                        </div>
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
              {strategyType && (
                <p className="text-xs text-muted-foreground">
                  {availableStrategies?.strategies?.find((s) => s.name === strategyType)?.description}
                </p>
              )}
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="paperTrading"
                checked={isPaperTrading}
                onCheckedChange={setIsPaperTrading}
              />
              <Label htmlFor="paperTrading">Paper Trading Mode</Label>
            </div>
          </TabsContent>

          <TabsContent value="universe" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="universe">Universe</Label>
              <Select value={universeId || 'none'} onValueChange={(v) => setUniverseId(v === 'none' ? '' : v)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a universe (optional)" />
                </SelectTrigger>
                <SelectContent className="max-h-[300px]">
                  <SelectItem value="none">None (use custom symbols)</SelectItem>
                  {/* System universes */}
                  <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground mt-2">
                    Index Universes
                  </div>
                  {universes
                    ?.filter((u) => u.is_system)
                    .map((u) => (
                      <SelectItem key={u.id} value={u.id}>
                        <div className="flex items-center justify-between gap-4 w-full">
                          <span>{u.name}</span>
                          <span className="text-[10px] text-muted-foreground">
                            {u.symbols?.length || 0} stocks
                          </span>
                        </div>
                      </SelectItem>
                    ))}
                  {/* Custom universes */}
                  {universes?.some((u) => !u.is_system) && (
                    <>
                      <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground mt-2">
                        Custom Universes
                      </div>
                      {universes
                        ?.filter((u) => !u.is_system)
                        .map((u) => (
                          <SelectItem key={u.id} value={u.id}>
                            <div className="flex items-center justify-between gap-4 w-full">
                              <span>{u.name}</span>
                              <span className="text-[10px] text-muted-foreground">
                                {u.symbols?.length || 0} stocks
                              </span>
                            </div>
                          </SelectItem>
                        ))}
                    </>
                  )}
                </SelectContent>
              </Select>
              {universeId && universes?.find((u) => u.id === universeId)?.description && (
                <p className="text-xs text-muted-foreground">
                  {universes.find((u) => u.id === universeId)?.description}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="symbols">Custom Symbols (comma-separated)</Label>
              <Input
                id="symbols"
                value={symbols}
                onChange={(e) => setSymbols(e.target.value)}
                placeholder="RELIANCE, TCS, INFY"
              />
              <p className="text-xs text-muted-foreground">
                {universeId
                  ? 'Add additional symbols to the universe'
                  : 'Enter symbols to trade (required if no universe selected)'}
              </p>
            </div>
          </TabsContent>

          <TabsContent value="schedule" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="scheduleType">Schedule Type</Label>
              <Select value={scheduleType} onValueChange={(v) => setScheduleType(v as ScheduleType)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {scheduleTypes.map((s) => (
                    <SelectItem key={s.value} value={s.value}>
                      {s.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {scheduleType === 'INTERVAL' && (
              <div className="space-y-2">
                <Label htmlFor="interval">Interval (seconds)</Label>
                <Input
                  id="interval"
                  type="number"
                  value={intervalSeconds}
                  onChange={(e) => setIntervalSeconds(e.target.value)}
                  min="60"
                />
                <p className="text-xs text-muted-foreground">
                  Minimum 60 seconds. Common: 300 (5 min), 900 (15 min), 3600 (1 hour)
                </p>
              </div>
            )}

            {scheduleType === 'CRON' && (
              <div className="space-y-2">
                <Label htmlFor="cron">Cron Expression</Label>
                <Input
                  id="cron"
                  value={cronExpression}
                  onChange={(e) => setCronExpression(e.target.value)}
                  placeholder="0 9 * * 1-5"
                />
                <p className="text-xs text-muted-foreground">
                  Example: &quot;0 9 * * 1-5&quot; runs at 9 AM on weekdays
                </p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="risk" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="positionSizing">Position Sizing Method</Label>
              <Select
                value={positionSizingMethod}
                onValueChange={(v) => setPositionSizingMethod(v as PositionSizingMethod)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {positionSizingMethods.map((m) => (
                    <SelectItem key={m.value} value={m.value}>
                      {m.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="positionSize">Position Size Value</Label>
              <Input
                id="positionSize"
                type="number"
                value={positionSizeValue}
                onChange={(e) => setPositionSizeValue(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="maxPosition">Max Position Value (₹)</Label>
              <Input
                id="maxPosition"
                type="number"
                value={maxPositionValue}
                onChange={(e) => setMaxPositionValue(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="maxDailyLoss">Max Daily Loss (₹)</Label>
              <Input
                id="maxDailyLoss"
                type="number"
                value={maxDailyLoss}
                onChange={(e) => setMaxDailyLoss(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="maxConsecutiveLosses">Max Consecutive Losses</Label>
              <Input
                id="maxConsecutiveLosses"
                type="number"
                value={maxConsecutiveLosses}
                onChange={(e) => setMaxConsecutiveLosses(e.target.value)}
                min="1"
              />
            </div>

            {/* Profit Cutoff Section */}
            <div className="col-span-2 border-t pt-4 mt-2">
              <h4 className="text-sm font-medium mb-3">Profit Cutoff Settings</h4>
              <p className="text-xs text-muted-foreground mb-4">
                Automatically stop trading when profit targets are reached to lock in gains.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="maxDailyProfit">Max Daily Profit (₹)</Label>
              <Input
                id="maxDailyProfit"
                type="number"
                value={maxDailyProfit}
                onChange={(e) => setMaxDailyProfit(e.target.value)}
                placeholder="e.g., 20000"
              />
              <p className="text-xs text-muted-foreground">
                Stop trading for the day after reaching this profit. Leave empty to disable.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="overallProfitTarget">Overall Profit Target (₹)</Label>
              <Input
                id="overallProfitTarget"
                type="number"
                value={overallProfitTarget}
                onChange={(e) => setOverallProfitTarget(e.target.value)}
                placeholder="e.g., 100000"
              />
              <p className="text-xs text-muted-foreground">
                Lifetime profit target for this strategy. Leave empty to disable.
              </p>
            </div>

            <div className="space-y-2 col-span-2">
              <Label htmlFor="profitCutoffAction">Action When Target Reached</Label>
              <Select
                value={profitCutoffAction}
                onValueChange={(value: ProfitCutoffAction) => setProfitCutoffAction(value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {profitCutoffActions.map((action) => (
                    <SelectItem key={action.value} value={action.value}>
                      <div className="flex flex-col">
                        <span>{action.label}</span>
                        <span className="text-xs text-muted-foreground">{action.description}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isPending || !name || !strategyType}>
            {isPending ? 'Saving...' : isEditing ? 'Update Strategy' : 'Create Strategy'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

