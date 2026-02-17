'use client';

import { useState, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Code2, AlertCircle, Play, Info } from 'lucide-react';
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
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { algoApi } from '@/lib/api';
import type {
  DSLStrategyCreate,
  DSLStrategyDefinition,
  ScheduleType,
  PositionSizingMethod,
  StrategyProductType,
} from '@/types';

interface DSLStrategyBuilderProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

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

const EXAMPLE_DSL = `{
  "name": "RSI Oversold Strategy",
  "version": 1,
  "description": "Buy when RSI is oversold with MACD confirmation",
  "timeframe": "1d",
  "rules": {
    "entry": [
      {
        "condition": "rsi(14) < 30 AND macd_histogram > 0",
        "action": "BUY",
        "confidence": 0.8,
        "strength": 0.7
      }
    ],
    "exit": {
      "stop_loss_pct": 2.0,
      "take_profit_pct": 4.0
    },
    "filters": ["close > sma(200)"]
  },
  "indicators": [
    {"rsi": {"period": 14}},
    {"macd": {"fast": 12, "slow": 26, "signal": 9}},
    {"sma": {"period": 200}}
  ]
}`;

export function DSLStrategyBuilder({ open, onOpenChange }: DSLStrategyBuilderProps) {
  const queryClient = useQueryClient();

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [dslJson, setDslJson] = useState(EXAMPLE_DSL);
  const [parseError, setParseError] = useState<string | null>(null);
  const [symbols, setSymbols] = useState('');
  const [scheduleType, setScheduleType] = useState<ScheduleType>('MARKET_OPEN');
  const [intervalSeconds, setIntervalSeconds] = useState('300');
  const [positionSizingMethod, setPositionSizingMethod] = useState<PositionSizingMethod>('PERCENT_OF_PORTFOLIO');
  const [positionSizeValue, setPositionSizeValue] = useState('5');
  const [maxDailyLoss, setMaxDailyLoss] = useState('5000');
  const [isPaperTrading, setIsPaperTrading] = useState(true);
  const [productType, setProductType] = useState<StrategyProductType>('DELIVERY');

  const createMutation = useMutation({
    mutationFn: (data: DSLStrategyCreate) => algoApi.createDSLStrategy(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['algo-strategies'] });
      queryClient.invalidateQueries({ queryKey: ['signal-strategies'] });
      onOpenChange(false);
      resetForm();
    },
    onError: (error: Error) => {
      setParseError(error.message || 'Failed to create DSL strategy');
    },
  });

  const resetForm = () => {
    setName('');
    setDescription('');
    setDslJson(EXAMPLE_DSL);
    setParseError(null);
    setSymbols('');
    setScheduleType('MARKET_OPEN');
    setIntervalSeconds('300');
    setPositionSizingMethod('PERCENT_OF_PORTFOLIO');
    setPositionSizeValue('5');
    setMaxDailyLoss('5000');
    setIsPaperTrading(true);
    setProductType('DELIVERY');
  };

  const validateJson = useCallback(() => {
    try {
      const parsed = JSON.parse(dslJson);
      if (!parsed.name || !parsed.rules?.entry || !parsed.rules?.exit) {
        setParseError('DSL must include name, rules.entry, and rules.exit');
        return null;
      }
      setParseError(null);
      return parsed as DSLStrategyDefinition;
    } catch (e) {
      setParseError(`Invalid JSON: ${(e as Error).message}`);
      return null;
    }
  }, [dslJson]);

  const handleValidate = () => {
    validateJson();
  };

  const handleSubmit = () => {
    const definition = validateJson();
    if (!definition) return;

    const data: DSLStrategyCreate = {
      name: name || definition.name,
      description: description || definition.description,
      definition,
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

  const isValid = name.trim().length > 0 || !!validateJson()?.name;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Code2 className="h-5 w-5" />
            Create Custom DSL Strategy
          </DialogTitle>
          <DialogDescription>
            Define a custom trading strategy using the DSL (Domain Specific Language)
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Name and Description */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">Strategy Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="My Custom Strategy"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional description"
              />
            </div>
          </div>

          {/* DSL Editor */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="dsl">DSL Definition (JSON)</Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleValidate}
                className="h-7 text-xs"
              >
                <Play className="h-3 w-3 mr-1" />
                Validate
              </Button>
            </div>
            <Textarea
              id="dsl"
              value={dslJson}
              onChange={(e) => {
                setDslJson(e.target.value);
                setParseError(null);
              }}
              className="font-mono text-sm h-64"
              placeholder="Enter DSL definition..."
            />
            {parseError && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{parseError}</AlertDescription>
              </Alert>
            )}
          </div>

          {/* DSL Help */}
          <Accordion type="single" collapsible className="w-full">
            <AccordionItem value="help">
              <AccordionTrigger className="text-sm">
                <div className="flex items-center gap-2">
                  <Info className="h-4 w-4" />
                  DSL Syntax Reference
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="text-xs space-y-2 bg-muted p-3 rounded-md">
                  <p><strong>Supported Functions:</strong></p>
                  <ul className="list-disc list-inside space-y-1 ml-2">
                    <li><code>rsi(period)</code> - Relative Strength Index</li>
                    <li><code>sma(period)</code>, <code>ema(period)</code> - Moving Averages</li>
                    <li><code>macd</code>, <code>macd_signal</code>, <code>macd_histogram</code></li>
                    <li><code>bbands_upper(period, std)</code>, <code>bbands_lower</code>, <code>bbands_middle</code></li>
                    <li><code>atr(period)</code> - Average True Range</li>
                    <li><code>volume_sma(period)</code> - Volume Moving Average</li>
                  </ul>
                  <p className="mt-2"><strong>Variables:</strong> <code>close</code>, <code>open</code>, <code>high</code>, <code>low</code>, <code>volume</code>, <code>previous_close</code>, etc.</p>
                  <p><strong>Operators:</strong> <code>&gt;</code>, <code>&lt;</code>, <code>&gt;=</code>, <code>&lt;=</code>, <code>==</code>, <code>!=</code>, <code>AND</code>, <code>OR</code>, <code>NOT</code></p>
                  <p><strong>Actions:</strong> <code>BUY</code>, <code>SELL</code>, <code>HOLD</code></p>
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>

          {/* Execution Settings */}
          <Accordion type="single" collapsible defaultValue="execution" className="w-full">
            <AccordionItem value="execution">
              <AccordionTrigger className="text-sm">Execution Settings</AccordionTrigger>
              <AccordionContent>
                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div className="space-y-2">
                    <Label>Symbols (comma-separated)</Label>
                    <Input
                      value={symbols}
                      onChange={(e) => setSymbols(e.target.value)}
                      placeholder="RELIANCE, TCS, INFY"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Schedule</Label>
                    <Select value={scheduleType} onValueChange={(v) => setScheduleType(v as ScheduleType)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {scheduleTypes.map((st) => (
                          <SelectItem key={st.value} value={st.value}>{st.label}</SelectItem>
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
                  <div className="space-y-2">
                    <Label>Position Sizing</Label>
                    <Select value={positionSizingMethod} onValueChange={(v) => setPositionSizingMethod(v as PositionSizingMethod)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {positionSizingMethods.map((ps) => (
                          <SelectItem key={ps.value} value={ps.value}>{ps.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Position Size Value</Label>
                    <Input
                      type="number"
                      value={positionSizeValue}
                      onChange={(e) => setPositionSizeValue(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Max Daily Loss</Label>
                    <Input
                      type="number"
                      value={maxDailyLoss}
                      onChange={(e) => setMaxDailyLoss(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Product Type</Label>
                    <Select value={productType} onValueChange={(v) => setProductType(v as StrategyProductType)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {productTypes.map((pt) => (
                          <SelectItem key={pt.value} value={pt.value}>{pt.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex items-center space-x-2 pt-6">
                    <Switch
                      id="paperTrading"
                      checked={isPaperTrading}
                      onCheckedChange={setIsPaperTrading}
                    />
                    <Label htmlFor="paperTrading">Paper Trading</Label>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!isValid || createMutation.isPending}
          >
            {createMutation.isPending ? 'Creating...' : 'Create Strategy'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

