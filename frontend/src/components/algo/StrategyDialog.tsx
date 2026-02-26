'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, TrendingDown, Target, Shield, DollarSign, Layers, Settings2, ChevronDown, ChevronRight, Lock } from 'lucide-react';
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
import { Badge } from '@/components/ui/badge';
import { algoApi, signalsApi } from '@/lib/api';
import { StrategyParameterForm } from './StrategyParameterForm';
import { ComponentParameterForm } from './ComponentParameterForm';
import { TimeWindowSection } from './TimeWindowSection';
import type { AlgoStrategy, AlgoStrategyCreate, CompositeStrategyCreate, CompositeStrategyComponent, CombineLogic, ScheduleType, PositionSizingMethod, ProfitCutoffAction, ProfitBookingRule, StrategyProductType } from '@/types';

type StrategyMode = 'single' | 'composite';

const combineLogicOptions: { value: CombineLogic; label: string; description: string }[] = [
  { value: 'AND', label: 'AND (All Agree)', description: 'All strategies must signal the same direction' },
  { value: 'OR', label: 'OR (Any)', description: 'Any strategy signal triggers action' },
  { value: 'MAJORITY', label: 'Majority Vote', description: 'More than half must agree' },
  { value: 'WEIGHTED', label: 'Weighted', description: 'Weighted combination of signals' },
];

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
  { value: 'CLOSE_POSITIONS_AND_CONTINUE', label: 'Close & Continue', description: 'Close positions but keep finding new trades' },
  { value: 'NOTIFY_ONLY', label: 'Notify Only', description: 'Send notification but continue trading' },
];

const productTypes: { value: StrategyProductType; label: string; description: string }[] = [
  { value: 'DELIVERY', label: 'Delivery (CNC)', description: 'Full payment, no shorting, hold indefinitely' },
  { value: 'INTRADAY', label: 'Intraday (MIS)', description: '25% margin, shorting allowed, same-day square off' },
  { value: 'MARGIN', label: 'Margin (MTF)', description: '50% margin, no shorting, leveraged buying' },
];

export function StrategyDialog({ open, onOpenChange, strategy }: StrategyDialogProps) {
  const queryClient = useQueryClient();
  const isEditing = !!strategy;

  // Strategy mode (single vs composite)
  const [strategyMode, setStrategyMode] = useState<StrategyMode>('single');

  // Form state - common fields
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
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
  // Product type state (CNC/MIS/MTF)
  const [productType, setProductType] = useState<StrategyProductType>('DELIVERY');
  // Strategy-level default trailing stop state
  const [defaultTrailingStopEnabled, setDefaultTrailingStopEnabled] = useState(false);
  const [defaultTrailingStopPct, setDefaultTrailingStopPct] = useState('5');
  // Strategy-level default profit booking state
  const [defaultProfitBookingEnabled, setDefaultProfitBookingEnabled] = useState(false);
  const [defaultProfitBookingRules, setDefaultProfitBookingRules] = useState<ProfitBookingRule[]>([
    { target_pct: 5, quantity_pct: 25 },
    { target_pct: 10, quantity_pct: 25 },
    { target_pct: 15, quantity_pct: 50 },
  ]);
  // Strategy-level profit lock state (locks stop loss at profit level once threshold is reached)
  const [defaultProfitLockEnabled, setDefaultProfitLockEnabled] = useState(false);
  // Trading time window state
  const [timeWindowEnabled, setTimeWindowEnabled] = useState(false);
  const [tradingStartTime, setTradingStartTime] = useState('09:15');
  const [tradingEndTime, setTradingEndTime] = useState('15:30');
  const [tradingTimezone, setTradingTimezone] = useState('Asia/Kolkata');
  const [activeTradingDays, setActiveTradingDays] = useState<number[]>([0, 1, 2, 3, 4]); // Mon-Fri

  // Single strategy specific state
  const [strategyType, setStrategyType] = useState('');
  const [strategyParams, setStrategyParams] = useState<Record<string, unknown>>({});
  const [paramsExpanded, setParamsExpanded] = useState(false);

  // Composite strategy specific state
  const [combineLogic, setCombineLogic] = useState<CombineLogic>('AND');
  const [minAgreementPct, setMinAgreementPct] = useState('0.5');
  const [components, setComponents] = useState<CompositeStrategyComponent[]>([
    { strategy: '', weight: 1.0, required: false, params: {} },
    { strategy: '', weight: 1.0, required: false, params: {} },
  ]);
  const [expandedParams, setExpandedParams] = useState<number | null>(null);

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
      // Product type
      setProductType(strategy.product_type || 'DELIVERY');
      // Strategy-level trailing stop and profit booking
      setDefaultTrailingStopEnabled(strategy.default_trailing_stop_enabled || false);
      setDefaultTrailingStopPct(strategy.default_trailing_stop_pct ? String(strategy.default_trailing_stop_pct * 100) : '5');
      if (strategy.default_profit_booking_rules) {
        setDefaultProfitBookingEnabled(strategy.default_profit_booking_rules.enabled);
        setDefaultProfitBookingRules(strategy.default_profit_booking_rules.rules || []);
      } else {
        setDefaultProfitBookingEnabled(false);
        setDefaultProfitBookingRules([
          { target_pct: 5, quantity_pct: 25 },
          { target_pct: 10, quantity_pct: 25 },
          { target_pct: 15, quantity_pct: 50 },
        ]);
      }
      // Profit lock setting
      setDefaultProfitLockEnabled(strategy.default_profit_lock_enabled || false);
      // Trading time window - convert HH:MM:SS to HH:MM for input
      const hasTimeWindow = Boolean(strategy.trading_start_time && strategy.trading_end_time);
      setTimeWindowEnabled(hasTimeWindow);
      setTradingStartTime(strategy.trading_start_time ? strategy.trading_start_time.slice(0, 5) : '09:15');
      setTradingEndTime(strategy.trading_end_time ? strategy.trading_end_time.slice(0, 5) : '15:30');
      setTradingTimezone(strategy.trading_timezone || 'Asia/Kolkata');
      setActiveTradingDays(strategy.active_trading_days || [0, 1, 2, 3, 4]);

      // Check if this is a composite strategy (has components in strategy_config)
      const config = strategy.strategy_config || {};
      const isComposite = Array.isArray(config.components) && config.components.length > 0;

      if (isComposite) {
        setStrategyMode('composite');
        setCombineLogic((config.combine_logic as CombineLogic) || 'AND');
        setMinAgreementPct(String(config.min_agreement_pct ?? 0.5));
        // Map components from strategy_config
        const mappedComponents = (config.components as CompositeStrategyComponent[]).map((c) => ({
          strategy: c.strategy || '',
          weight: c.weight ?? 1.0,
          required: c.required ?? false,
          params: c.params || {},
        }));
        setComponents(mappedComponents.length >= 2 ? mappedComponents : [
          ...mappedComponents,
          ...Array(2 - mappedComponents.length).fill({ strategy: '', weight: 1.0, required: false, params: {} }),
        ]);
        setExpandedParams(null);
        // For composite, we don't use strategyParams (individual params are in components)
        setStrategyParams({});
        setParamsExpanded(false);
      } else {
        setStrategyMode('single');
        // Strategy parameter customization for single strategies
        setStrategyParams(config);
        setParamsExpanded(Object.keys(config).length > 0);
        // Reset composite fields
        setCombineLogic('AND');
        setMinAgreementPct('0.5');
        setComponents([
          { strategy: '', weight: 1.0, required: false, params: {} },
          { strategy: '', weight: 1.0, required: false, params: {} },
        ]);
        setExpandedParams(null);
      }
    } else {
      // Reset to defaults
      setStrategyMode('single');
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
      // Product type default
      setProductType('DELIVERY');
      // Strategy-level trailing stop and profit booking defaults
      setDefaultTrailingStopEnabled(false);
      setDefaultTrailingStopPct('5');
      setDefaultProfitBookingEnabled(false);
      setDefaultProfitBookingRules([
        { target_pct: 5, quantity_pct: 25 },
        { target_pct: 10, quantity_pct: 25 },
        { target_pct: 15, quantity_pct: 50 },
      ]);
      // Trading time window defaults
      setTimeWindowEnabled(false);
      setTradingStartTime('09:15');
      setTradingEndTime('15:30');
      setTradingTimezone('Asia/Kolkata');
      setActiveTradingDays([0, 1, 2, 3, 4]);
      // Strategy parameter customization reset
      setStrategyParams({});
      setParamsExpanded(false);
      // Composite strategy reset
      setCombineLogic('AND');
      setMinAgreementPct('0.5');
      setComponents([
        { strategy: '', weight: 1.0, required: false, params: {} },
        { strategy: '', weight: 1.0, required: false, params: {} },
      ]);
      setExpandedParams(null);
    }
  }, [strategy, open]);

  // Get base strategies (non-composite) for composite component selection
  const baseStrategies = availableStrategies?.strategies?.filter(
    (s) => !s.parameters?.components
  ) || [];

  // Composite component helpers
  const addComponent = () => {
    if (components.length < 5) {
      setComponents([...components, { strategy: '', weight: 1.0, required: false, params: {} }]);
    }
  };

  const removeComponent = (index: number) => {
    if (components.length > 2) {
      setComponents(components.filter((_, i) => i !== index));
    }
  };

  const updateComponent = (index: number, field: keyof CompositeStrategyComponent, value: unknown) => {
    setComponents(prev => {
      const newComponents = [...prev];
      newComponents[index] = { ...newComponents[index], [field]: value };
      return newComponents;
    });
  };

  const updateComponentWithReset = (index: number, strategyValue: string) => {
    setComponents(prev => {
      const newComponents = [...prev];
      newComponents[index] = { ...newComponents[index], strategy: strategyValue, params: {} };
      return newComponents;
    });
  };

  const createMutation = useMutation({
    mutationFn: (data: AlgoStrategyCreate) => algoApi.createStrategy(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['algo-strategies'] });
      onOpenChange(false);
    },
    onError: (error) => {
      console.error('Failed to create strategy:', error);
    },
  });

  const createCompositeMutation = useMutation({
    mutationFn: (data: CompositeStrategyCreate) => algoApi.createCompositeStrategy(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['algo-strategies'] });
      onOpenChange(false);
    },
    onError: (error) => {
      console.error('Failed to create composite strategy:', error);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: AlgoStrategyCreate) => algoApi.updateStrategy(strategy!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['algo-strategies'] });
      onOpenChange(false);
    },
    onError: (error) => {
      console.error('Failed to update strategy:', error);
    },
  });

  const handleSubmit = () => {
    // Common fields for both strategy types
    const commonFields = {
      name,
      description: description || undefined,
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
      max_daily_profit: maxDailyProfit ? parseFloat(maxDailyProfit) : undefined,
      overall_profit_target: overallProfitTarget ? parseFloat(overallProfitTarget) : undefined,
      profit_cutoff_action: profitCutoffAction,
      is_paper_trading: isPaperTrading,
      product_type: productType,
      default_trailing_stop_enabled: defaultTrailingStopEnabled,
      default_trailing_stop_pct: defaultTrailingStopEnabled ? parseFloat(defaultTrailingStopPct) / 100 : undefined,
      default_profit_booking_rules: defaultProfitBookingEnabled
        ? {
            enabled: true,
            rules: defaultProfitBookingRules.sort((a, b) => Number(a.target_pct) - Number(b.target_pct)),
            executed: [],
          }
        : undefined,
      default_profit_lock_enabled: defaultProfitLockEnabled,
      // Trading time window fields - convert HH:MM to HH:MM:SS
      trading_start_time: timeWindowEnabled ? `${tradingStartTime}:00` : undefined,
      trading_end_time: timeWindowEnabled ? `${tradingEndTime}:00` : undefined,
      trading_timezone: timeWindowEnabled ? tradingTimezone : undefined,
      active_trading_days: timeWindowEnabled ? activeTradingDays : undefined,
    };

    if (strategyMode === 'composite') {
      // Validate components
      const validComponents = components.filter(c => c.strategy);
      if (validComponents.length < 2) {
        console.error('At least 2 strategies are required for a composite');
        return;
      }

      if (isEditing) {
        // For editing composite strategies, update via the regular update endpoint
        // with strategy_config containing the composite configuration
        const updateData: AlgoStrategyCreate = {
          ...commonFields,
          strategy_type: strategy!.strategy_type, // Keep the original strategy_type
          strategy_config: {
            components: validComponents,
            combine_logic: combineLogic,
            min_agreement_pct: combineLogic === 'MAJORITY' ? parseFloat(minAgreementPct) : 0.5,
          },
        };
        updateMutation.mutate(updateData);
      } else {
        // Create new composite strategy
        const compositeData: CompositeStrategyCreate = {
          ...commonFields,
          components: validComponents,
          combine_logic: combineLogic,
          min_agreement_pct: combineLogic === 'MAJORITY' ? parseFloat(minAgreementPct) : undefined,
        };
        createCompositeMutation.mutate(compositeData);
      }
    } else {
      // Single strategy
      const data: AlgoStrategyCreate = {
        ...commonFields,
        strategy_type: strategyType,
        strategy_config: Object.keys(strategyParams).length > 0 ? strategyParams : undefined,
      };

      if (isEditing) {
        updateMutation.mutate(data);
      } else {
        createMutation.mutate(data);
      }
    }
  };

  // Helper functions for profit booking rules
  const addProfitBookingRule = () => {
    setDefaultProfitBookingRules([...defaultProfitBookingRules, { target_pct: 20, quantity_pct: 25 }]);
  };

  const removeProfitBookingRule = (index: number) => {
    setDefaultProfitBookingRules(defaultProfitBookingRules.filter((_, i) => i !== index));
  };

  const updateProfitBookingRule = (index: number, field: keyof ProfitBookingRule, value: string) => {
    const newRules = [...defaultProfitBookingRules];
    newRules[index] = { ...newRules[index], [field]: parseFloat(value) || 0 };
    setDefaultProfitBookingRules(newRules);
  };

  // Get position size label based on method
  const getPositionSizeLabel = () => {
    switch (positionSizingMethod) {
      case 'FIXED_QUANTITY':
        return 'Quantity (shares)';
      case 'FIXED_AMOUNT':
        return 'Amount (₹)';
      case 'PERCENT_OF_PORTFOLIO':
        return 'Portfolio %';
      case 'RISK_BASED':
        return 'Risk per Trade %';
      case 'VOLATILITY_ADJUSTED':
        return 'ATR Multiplier';
      default:
        return 'Position Size Value';
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending || createCompositeMutation.isPending;

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
                rows={2}
              />
            </div>

            {/* Strategy Mode Toggle - only show when creating new strategy */}
            {!isEditing && (
              <div className="space-y-2">
                <Label>Strategy Mode</Label>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant={strategyMode === 'single' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setStrategyMode('single')}
                    className="flex-1"
                  >
                    Single Strategy
                  </Button>
                  <Button
                    type="button"
                    variant={strategyMode === 'composite' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setStrategyMode('composite')}
                    className="flex-1"
                  >
                    <Layers className="h-4 w-4 mr-1" />
                    Composite Strategy
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  {strategyMode === 'single'
                    ? 'Use a single trading strategy'
                    : 'Combine 2-5 strategies with custom logic (AND/OR/MAJORITY/WEIGHTED)'}
                </p>
              </div>
            )}

            {/* Single Strategy Selection */}
            {strategyMode === 'single' && (
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
                {strategyType && (
                  <StrategyParameterForm
                    strategyType={strategyType}
                    params={strategyParams}
                    onChange={setStrategyParams}
                    isOpen={paramsExpanded}
                    onOpenChange={setParamsExpanded}
                  />
                )}
              </div>
            )}

            {/* Composite Strategy Configuration */}
            {strategyMode === 'composite' && (
              <div className="space-y-4 border rounded-lg p-3 bg-muted/30">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Layers className="h-4 w-4 text-purple-500" />
                    <span className="text-sm font-medium">Composite Strategy Settings</span>
                  </div>
                  {isEditing && (
                    <Badge variant="secondary" className="text-xs">
                      {strategy?.strategy_type}
                    </Badge>
                  )}
                </div>

                {/* Combine Logic */}
                <div className="space-y-2">
                  <Label>Combine Logic</Label>
                  <Select value={combineLogic} onValueChange={(v) => setCombineLogic(v as CombineLogic)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {combineLogicOptions.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          <div className="flex flex-col">
                            <span>{opt.label}</span>
                            <span className="text-xs text-muted-foreground">{opt.description}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {combineLogic === 'MAJORITY' && (
                  <div className="space-y-2">
                    <Label>Minimum Agreement %</Label>
                    <Input
                      type="number"
                      min="0.1"
                      max="1"
                      step="0.1"
                      value={minAgreementPct}
                      onChange={(e) => setMinAgreementPct(e.target.value)}
                    />
                    <p className="text-xs text-muted-foreground">
                      0.5 = majority (more than half must agree)
                    </p>
                  </div>
                )}

                {/* Component Strategies */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Component Strategies ({components.length}/5)</Label>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={addComponent}
                      disabled={components.length >= 5}
                    >
                      <Plus className="h-3 w-3 mr-1" />
                      Add
                    </Button>
                  </div>

                  <div className="space-y-2 max-h-[200px] overflow-y-auto">
                    {components.map((comp, index) => {
                      const isExpanded = expandedParams === index;
                      const hasCustomParams = comp.params && Object.keys(comp.params).length > 0;

                      return (
                        <div key={index} className="rounded-lg border bg-background">
                          <div className="flex items-center gap-2 p-2">
                            <Badge variant="outline" className="w-6 h-6 flex items-center justify-center p-0 shrink-0">
                              {index + 1}
                            </Badge>
                            <Select
                              value={comp.strategy}
                              onValueChange={(value) => updateComponentWithReset(index, value)}
                            >
                              <SelectTrigger className="flex-1 h-8">
                                <SelectValue placeholder="Select strategy" />
                              </SelectTrigger>
                              <SelectContent position="popper" sideOffset={4} className="z-[100]">
                                {baseStrategies.map((s) => (
                                  <SelectItem key={s.name} value={s.name}>
                                    {s.name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            {combineLogic === 'WEIGHTED' && (
                              <Input
                                type="number"
                                min="0.1"
                                max="10"
                                step="0.1"
                                value={comp.weight}
                                onChange={(e) => updateComponent(index, 'weight', parseFloat(e.target.value))}
                                className="w-16 h-8"
                                placeholder="Wt"
                              />
                            )}
                            {comp.strategy && (
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                className={`h-8 w-8 p-0 ${hasCustomParams ? 'text-blue-500' : ''}`}
                                onClick={() => setExpandedParams(isExpanded ? null : index)}
                              >
                                {isExpanded ? <ChevronDown className="h-4 w-4" /> : <Settings2 className="h-4 w-4" />}
                              </Button>
                            )}
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => removeComponent(index)}
                              disabled={components.length <= 2}
                              className="h-8 w-8 p-0 text-destructive"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                          {isExpanded && comp.strategy && (
                            <div className="px-3 pb-3 border-t bg-muted/30">
                              <ComponentParameterForm
                                strategyType={comp.strategy}
                                params={comp.params || {}}
                                onChange={(newParams) => updateComponent(index, 'params', newParams)}
                              />
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            <div className="flex items-center space-x-2">
              <Switch
                id="paperTrading"
                checked={isPaperTrading}
                onCheckedChange={setIsPaperTrading}
              />
              <Label htmlFor="paperTrading">Paper Trading Mode</Label>
            </div>

            <div className="space-y-2">
              <Label htmlFor="productType">Product Type</Label>
              <Select value={productType} onValueChange={(v) => setProductType(v as StrategyProductType)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select product type" />
                </SelectTrigger>
                <SelectContent>
                  {productTypes.map((pt) => (
                    <SelectItem key={pt.value} value={pt.value}>
                      {pt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {productType && (
                <p className="text-xs text-muted-foreground">
                  {productTypes.find((pt) => pt.value === productType)?.description}
                </p>
              )}
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

            {/* Trading Time Window */}
            <div className="border-t pt-4">
              <TimeWindowSection
                enabled={timeWindowEnabled}
                onEnabledChange={setTimeWindowEnabled}
                startTime={tradingStartTime}
                onStartTimeChange={setTradingStartTime}
                endTime={tradingEndTime}
                onEndTimeChange={setTradingEndTime}
                timezone={tradingTimezone}
                onTimezoneChange={setTradingTimezone}
                activeDays={activeTradingDays}
                onActiveDaysChange={setActiveTradingDays}
              />
            </div>
          </TabsContent>

          <TabsContent value="risk" className="space-y-4 mt-4 max-h-[60vh] overflow-y-auto pr-2">
            {/* Section 1: Position Sizing */}
            <div className="border rounded-lg p-4 space-y-4">
              <div className="flex items-center gap-2 mb-2">
                <DollarSign className="h-4 w-4 text-blue-500" />
                <h4 className="text-sm font-medium">Position Sizing</h4>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="positionSizing">Sizing Method</Label>
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
                  <Label htmlFor="positionSize">{getPositionSizeLabel()}</Label>
                  <Input
                    id="positionSize"
                    type="number"
                    value={positionSizeValue}
                    onChange={(e) => setPositionSizeValue(e.target.value)}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="maxPosition">Max Position Value (₹)</Label>
                <Input
                  id="maxPosition"
                  type="number"
                  value={maxPositionValue}
                  onChange={(e) => setMaxPositionValue(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">Maximum value for any single position</p>
              </div>
            </div>

            {/* Section 2: Loss Protection */}
            <div className="border rounded-lg p-4 space-y-4">
              <div className="flex items-center gap-2 mb-2">
                <Shield className="h-4 w-4 text-red-500" />
                <h4 className="text-sm font-medium">Loss Protection</h4>
              </div>
              <div className="grid grid-cols-2 gap-4">
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
              </div>
              {/* Default Trailing Stop */}
              <div className="border-t pt-4 mt-2 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <TrendingDown className="h-4 w-4 text-orange-500" />
                    <Label htmlFor="defaultTrailingStop" className="font-medium">Default Trailing Stop</Label>
                  </div>
                  <Switch
                    id="defaultTrailingStop"
                    checked={defaultTrailingStopEnabled}
                    onCheckedChange={setDefaultTrailingStopEnabled}
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Applied to all positions unless overridden at position level
                </p>
                {defaultTrailingStopEnabled && (
                  <div className="space-y-2">
                    <Label htmlFor="trailingStopPct">Trailing Stop %</Label>
                    <Input
                      id="trailingStopPct"
                      type="number"
                      value={defaultTrailingStopPct}
                      onChange={(e) => setDefaultTrailingStopPct(e.target.value)}
                      min="0.1"
                      max="50"
                      step="0.1"
                    />
                  </div>
                )}
              </div>
            </div>

            {/* Section 3: Profit Taking */}
            <div className="border rounded-lg p-4 space-y-4">
              <div className="flex items-center gap-2 mb-2">
                <Target className="h-4 w-4 text-green-500" />
                <h4 className="text-sm font-medium">Profit Taking</h4>
              </div>
              {/* Default Profit Booking Rules */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label htmlFor="defaultProfitBooking" className="font-medium">Default Profit Booking</Label>
                  <Switch
                    id="defaultProfitBooking"
                    checked={defaultProfitBookingEnabled}
                    onCheckedChange={setDefaultProfitBookingEnabled}
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Automatically book profits at target levels. Applied to all positions unless overridden.
                </p>
                {defaultProfitBookingEnabled && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label className="text-xs">Target % → Book % of position</Label>
                      <Button type="button" variant="outline" size="sm" onClick={addProfitBookingRule}>
                        <Plus className="h-3 w-3 mr-1" />
                        Add
                      </Button>
                    </div>
                    <div className="space-y-2">
                      {defaultProfitBookingRules.map((rule, index) => (
                        <div key={index} className="flex items-center gap-2">
                          <Input
                            type="number"
                            className="w-20"
                            placeholder="Target"
                            value={rule.target_pct}
                            onChange={(e) => updateProfitBookingRule(index, 'target_pct', e.target.value)}
                          />
                          <span className="text-xs text-muted-foreground">%→</span>
                          <Input
                            type="number"
                            className="w-20"
                            placeholder="Book"
                            value={rule.quantity_pct}
                            onChange={(e) => updateProfitBookingRule(index, 'quantity_pct', e.target.value)}
                          />
                          <span className="text-xs text-muted-foreground">%</span>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => removeProfitBookingRule(index)}
                            disabled={defaultProfitBookingRules.length <= 1}
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              {/* Profit Lock */}
              <div className="border-t pt-4 mt-2 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Lock className="h-4 w-4 text-emerald-500" />
                    <Label htmlFor="defaultProfitLock" className="font-medium">Profit Lock</Label>
                  </div>
                  <Switch
                    id="defaultProfitLock"
                    checked={defaultProfitLockEnabled}
                    onCheckedChange={setDefaultProfitLockEnabled}
                    disabled={!defaultProfitBookingEnabled || !defaultTrailingStopEnabled}
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  When enabled, locks stop loss at a profit level once the first profit booking threshold is reached.
                  Uses trailing stop % as buffer below the activation price.
                  {!defaultProfitBookingEnabled && (
                    <span className="block mt-1 text-amber-500">Enable Profit Booking to use this feature.</span>
                  )}
                  {defaultProfitBookingEnabled && !defaultTrailingStopEnabled && (
                    <span className="block mt-1 text-amber-500">Enable Trailing Stop to use this feature.</span>
                  )}
                </p>
              </div>
              {/* Profit Cutoff */}
              <div className="border-t pt-4 mt-2 space-y-3">
                <Label className="font-medium">Profit Cutoff</Label>
                <p className="text-xs text-muted-foreground">
                  Stop trading when profit targets are reached to lock in gains.
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="maxDailyProfit">Daily Profit Limit (₹)</Label>
                    <Input
                      id="maxDailyProfit"
                      type="number"
                      value={maxDailyProfit}
                      onChange={(e) => setMaxDailyProfit(e.target.value)}
                      placeholder="Optional"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="overallProfitTarget">Overall Target (₹)</Label>
                    <Input
                      id="overallProfitTarget"
                      type="number"
                      value={overallProfitTarget}
                      onChange={(e) => setOverallProfitTarget(e.target.value)}
                      placeholder="Optional"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="profitCutoffAction">Action When Reached</Label>
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
              </div>
            </div>
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={
              isPending ||
              !name ||
              (strategyMode === 'single' ? !strategyType : components.filter(c => c.strategy).length < 2)
            }
          >
            {isPending ? 'Saving...' : isEditing ? 'Update Strategy' : 'Create Strategy'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

