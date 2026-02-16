'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, Layers, AlertCircle, Settings2, ChevronDown, ChevronRight } from 'lucide-react';
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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { algoApi, signalsApi } from '@/lib/api';
import { ComponentParameterForm } from './ComponentParameterForm';
import type {
  CombineLogic,
  CompositeStrategyComponent,
  CompositeStrategyCreate,
  ScheduleType,
  PositionSizingMethod,
  StrategyProductType,
} from '@/types';

interface CompositeStrategyBuilderProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const combineLogicOptions: { value: CombineLogic; label: string; description: string }[] = [
  { value: 'AND', label: 'AND (All Agree)', description: 'All strategies must signal the same direction' },
  { value: 'OR', label: 'OR (Any)', description: 'Any strategy signal triggers action' },
  { value: 'MAJORITY', label: 'Majority Vote', description: 'More than half must agree' },
  { value: 'WEIGHTED', label: 'Weighted', description: 'Weighted combination of signals' },
];

const scheduleTypes: { value: ScheduleType; label: string }[] = [
  { value: 'MARKET_OPEN', label: 'Market Open' },
  { value: 'MARKET_CLOSE', label: 'Market Close' },
  { value: 'INTERVAL', label: 'Fixed Interval' },
  { value: 'CONTINUOUS', label: 'Continuous' },
];

const positionSizingMethods: { value: PositionSizingMethod; label: string }[] = [
  { value: 'PERCENT_OF_PORTFOLIO', label: '% of Portfolio' },
  { value: 'FIXED_AMOUNT', label: 'Fixed Amount' },
  { value: 'FIXED_QUANTITY', label: 'Fixed Quantity' },
];

const productTypes: { value: StrategyProductType; label: string }[] = [
  { value: 'DELIVERY', label: 'Delivery (CNC)' },
  { value: 'INTRADAY', label: 'Intraday (MIS)' },
  { value: 'MARGIN', label: 'Margin (MTF)' },
];

export function CompositeStrategyBuilder({ open, onOpenChange }: CompositeStrategyBuilderProps) {
  const queryClient = useQueryClient();

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [combineLogic, setCombineLogic] = useState<CombineLogic>('AND');
  const [minAgreementPct, setMinAgreementPct] = useState('0.5');
  const [components, setComponents] = useState<CompositeStrategyComponent[]>([
    { strategy: '', weight: 1.0, required: false, params: {} },
    { strategy: '', weight: 1.0, required: false, params: {} },
  ]);
  // Track which component's parameter form is expanded
  const [expandedParams, setExpandedParams] = useState<number | null>(null);
  
  // Execution settings
  const [symbols, setSymbols] = useState('');
  const [scheduleType, setScheduleType] = useState<ScheduleType>('MARKET_OPEN');
  const [intervalSeconds, setIntervalSeconds] = useState('300');
  const [positionSizingMethod, setPositionSizingMethod] = useState<PositionSizingMethod>('PERCENT_OF_PORTFOLIO');
  const [positionSizeValue, setPositionSizeValue] = useState('5');
  const [maxDailyLoss, setMaxDailyLoss] = useState('5000');
  const [isPaperTrading, setIsPaperTrading] = useState(true);
  const [productType, setProductType] = useState<StrategyProductType>('DELIVERY');

  // Fetch available strategies
  const { data: availableStrategies } = useQuery({
    queryKey: ['signal-strategies'],
    queryFn: () => signalsApi.getStrategies().then((res) => res.data),
  });

  // Get base strategies (non-composite)
  const baseStrategies = availableStrategies?.strategies?.filter(
    (s) => !s.parameters?.components
  ) || [];

  const createMutation = useMutation({
    mutationFn: (data: CompositeStrategyCreate) => algoApi.createCompositeStrategy(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['algo-strategies'] });
      queryClient.invalidateQueries({ queryKey: ['signal-strategies'] });
      onOpenChange(false);
      resetForm();
    },
    onError: (error) => {
      console.error('Failed to create composite strategy:', error);
    },
  });

  const resetForm = () => {
    setName('');
    setDescription('');
    setCombineLogic('AND');
    setMinAgreementPct('0.5');
    setComponents([
      { strategy: '', weight: 1.0, required: false, params: {} },
      { strategy: '', weight: 1.0, required: false, params: {} },
    ]);
    setExpandedParams(null);
    setSymbols('');
    setScheduleType('MARKET_OPEN');
    setIntervalSeconds('300');
    setPositionSizingMethod('PERCENT_OF_PORTFOLIO');
    setPositionSizeValue('5');
    setMaxDailyLoss('5000');
    setIsPaperTrading(true);
    setProductType('DELIVERY');
  };

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
    const newComponents = [...components];
    newComponents[index] = { ...newComponents[index], [field]: value };
    setComponents(newComponents);
  };

  const handleSubmit = () => {
    const validComponents = components.filter((c) => c.strategy);
    if (validComponents.length < 2) return;

    const data: CompositeStrategyCreate = {
      name,
      description: description || undefined,
      components: validComponents,
      combine_logic: combineLogic,
      min_agreement_pct: combineLogic === 'MAJORITY' ? parseFloat(minAgreementPct) : undefined,
      symbols: symbols ? symbols.split(',').map((s) => s.trim().toUpperCase()) : undefined,
      schedule_type: scheduleType,
      interval_seconds: scheduleType === 'INTERVAL' ? parseInt(intervalSeconds) : undefined,
      position_sizing_method: positionSizingMethod,
      position_size_value: parseFloat(positionSizeValue),
      max_daily_loss: parseFloat(maxDailyLoss),
      is_paper_trading: isPaperTrading,
      product_type: productType,
    };

    createMutation.mutate(data);
  };

  const validComponentCount = components.filter((c) => c.strategy).length;
  const canSubmit = name.trim() && validComponentCount >= 2;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Layers className="h-5 w-5 text-purple-500" />
            Create Composite Strategy
          </DialogTitle>
          <DialogDescription>
            Combine 2-5 strategies to create a more robust trading signal
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Basic Info */}
          <div className="grid grid-cols-1 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">Strategy Name *</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., RSI + MACD Momentum"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe your composite strategy..."
                rows={2}
              />
            </div>
          </div>

          {/* Combine Logic */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Signal Combination Logic</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-2">
                {combineLogicOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setCombineLogic(option.value)}
                    className={`p-3 rounded-lg border text-left transition-colors ${
                      combineLogic === option.value
                        ? 'border-purple-500 bg-purple-50 dark:bg-purple-950'
                        : 'border-border hover:border-purple-300'
                    }`}
                  >
                    <div className="font-medium text-sm">{option.label}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{option.description}</div>
                  </button>
                ))}
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
                </div>
              )}
            </CardContent>
          </Card>

          {/* Component Strategies */}
          <Card>
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-medium">
                Component Strategies ({validComponentCount}/5)
              </CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={addComponent}
                disabled={components.length >= 5}
              >
                <Plus className="h-4 w-4 mr-1" /> Add
              </Button>
            </CardHeader>
            <CardContent className="space-y-3">
              {components.map((comp, index) => {
                const isExpanded = expandedParams === index;
                const hasCustomParams = comp.params && Object.keys(comp.params).length > 0;
                return (
                  <div key={index} className="rounded-lg border bg-muted/30">
                    <div className="flex items-center gap-2 p-2">
                      <Badge variant="outline" className="w-6 h-6 flex items-center justify-center p-0 shrink-0">
                        {index + 1}
                      </Badge>
                      <Select
                        value={comp.strategy}
                        onValueChange={(value) => {
                          updateComponent(index, 'strategy', value);
                          // Reset params when strategy changes
                          updateComponent(index, 'params', {});
                        }}
                      >
                        <SelectTrigger className="flex-1">
                          <SelectValue placeholder="Select strategy" />
                        </SelectTrigger>
                        <SelectContent>
                          {baseStrategies.map((s) => (
                            <SelectItem
                              key={s.name}
                              value={s.name}
                              disabled={components.some((c, i) => i !== index && c.strategy === s.name)}
                            >
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
                          className="w-20"
                          placeholder="Weight"
                        />
                      )}
                      {comp.strategy && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setExpandedParams(isExpanded ? null : index)}
                          className={`h-8 w-8 shrink-0 ${hasCustomParams ? 'text-blue-500' : ''}`}
                          title="Customize parameters"
                        >
                          <Settings2 className="h-4 w-4" />
                          {isExpanded ? (
                            <ChevronDown className="h-3 w-3 ml-0.5" />
                          ) : (
                            <ChevronRight className="h-3 w-3 ml-0.5" />
                          )}
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeComponent(index)}
                        disabled={components.length <= 2}
                        className="h-8 w-8 shrink-0"
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                    {/* Parameter customization panel */}
                    {isExpanded && comp.strategy && (
                      <div className="px-3 pb-3 border-t bg-background/50">
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
              {validComponentCount < 2 && (
                <Alert variant="destructive" className="mt-2">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>Select at least 2 strategies to combine</AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* Execution Settings */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Execution Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Symbols (comma-separated)</Label>
                <Input
                  value={symbols}
                  onChange={(e) => setSymbols(e.target.value)}
                  placeholder="RELIANCE, TCS, INFY"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Schedule</Label>
                  <Select value={scheduleType} onValueChange={(v) => setScheduleType(v as ScheduleType)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {scheduleTypes.map((t) => (
                        <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                {scheduleType === 'INTERVAL' && (
                  <div className="space-y-2">
                    <Label>Interval (seconds)</Label>
                    <Input
                      type="number"
                      value={intervalSeconds}
                      onChange={(e) => setIntervalSeconds(e.target.value)}
                    />
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Position Sizing</Label>
                  <Select value={positionSizingMethod} onValueChange={(v) => setPositionSizingMethod(v as PositionSizingMethod)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {positionSizingMethods.map((m) => (
                        <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Size Value</Label>
                  <Input
                    type="number"
                    value={positionSizeValue}
                    onChange={(e) => setPositionSizeValue(e.target.value)}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Product Type</Label>
                  <Select value={productType} onValueChange={(v) => setProductType(v as StrategyProductType)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {productTypes.map((p) => (
                        <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Max Daily Loss (₹)</Label>
                  <Input
                    type="number"
                    value={maxDailyLoss}
                    onChange={(e) => setMaxDailyLoss(e.target.value)}
                  />
                </div>
              </div>

              <div className="flex items-center justify-between rounded-lg border p-3">
                <div>
                  <Label className="font-medium">Paper Trading Mode</Label>
                  <p className="text-xs text-muted-foreground">Test without real money</p>
                </div>
                <Switch checked={isPaperTrading} onCheckedChange={setIsPaperTrading} />
              </div>
            </CardContent>
          </Card>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit || createMutation.isPending}>
            {createMutation.isPending ? 'Creating...' : 'Create Composite Strategy'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
