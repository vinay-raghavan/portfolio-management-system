'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Code2, AlertCircle, Play, Info, FlaskConical, Beaker, MousePointer2 } from 'lucide-react';
import Editor, { Monaco } from '@monaco-editor/react';
import type { editor, languages, IRange, Position } from 'monaco-editor';
import {
  VisualRuleBuilder,
  EntryRule,
  ExitConfig,
  rulesToConditionString,
} from './VisualRuleBuilder';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
import { Badge } from '@/components/ui/badge';
import { algoApi } from '@/lib/api';
import type {
  DSLStrategyCreate,
  DSLStrategyDefinition,
  ScheduleType,
  PositionSizingMethod,
  StrategyProductType,
} from '@/types';

// DSL functions for auto-complete
const DSL_FUNCTIONS = [
  { name: 'rsi', signature: 'rsi(period)', description: 'Relative Strength Index - momentum oscillator (0-100)' },
  { name: 'sma', signature: 'sma(period)', description: 'Simple Moving Average' },
  { name: 'ema', signature: 'ema(period)', description: 'Exponential Moving Average' },
  { name: 'macd', signature: 'macd', description: 'MACD line value' },
  { name: 'macd_signal', signature: 'macd_signal', description: 'MACD signal line' },
  { name: 'macd_histogram', signature: 'macd_histogram', description: 'MACD histogram (macd - signal)' },
  { name: 'bbands_upper', signature: 'bbands_upper(period, std)', description: 'Bollinger Bands upper band' },
  { name: 'bbands_lower', signature: 'bbands_lower(period, std)', description: 'Bollinger Bands lower band' },
  { name: 'bbands_middle', signature: 'bbands_middle(period)', description: 'Bollinger Bands middle band (SMA)' },
  { name: 'atr', signature: 'atr(period)', description: 'Average True Range - volatility indicator' },
  { name: 'volume_sma', signature: 'volume_sma(period)', description: 'Volume Simple Moving Average' },
];

const DSL_VARIABLES = [
  { name: 'close', description: 'Current closing price' },
  { name: 'open', description: 'Current opening price' },
  { name: 'high', description: 'Current high price' },
  { name: 'low', description: 'Current low price' },
  { name: 'volume', description: 'Current volume' },
  { name: 'previous_close', description: 'Previous bar closing price' },
  { name: 'previous_open', description: 'Previous bar opening price' },
  { name: 'previous_high', description: 'Previous bar high price' },
  { name: 'previous_low', description: 'Previous bar low price' },
];

const DSL_OPERATORS = ['>', '<', '>=', '<=', '==', '!=', 'AND', 'OR', 'NOT', '+', '-', '*', '/'];
const DSL_ACTIONS = ['BUY', 'SELL', 'HOLD'];

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
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<Monaco | null>(null);

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

  // Backtest state
  const [backtestPassed, setBacktestPassed] = useState(false);
  const [isBacktesting, setIsBacktesting] = useState(false);
  const [backtestResult, setBacktestResult] = useState<{
    totalReturn: number;
    winRate: number;
    trades: number;
    maxDrawdown: number;
  } | null>(null);
  const [requireBacktest, setRequireBacktest] = useState(true);
  const [paperTradingDays, setPaperTradingDays] = useState('7');

  // Visual builder state
  const [editorMode, setEditorMode] = useState<'json' | 'visual'>('json');
  const [visualEntryRules, setVisualEntryRules] = useState<EntryRule[]>([]);
  const [visualExitConfig, setVisualExitConfig] = useState<ExitConfig>({
    stopLossPct: 2.0,
    takeProfitPct: 4.0,
  });
  const [visualFilters, setVisualFilters] = useState<string[]>([]);

  // Sync visual builder to JSON
  const syncVisualToJson = useCallback(() => {
    const definition: DSLStrategyDefinition = {
      name: name || 'Visual Strategy',
      version: 1,
      description: description,
      timeframe: '1d',
      rules: {
        entry: visualEntryRules.map((rule) => ({
          condition: rulesToConditionString(rule.conditions),
          action: rule.action,
          confidence: rule.confidence,
          strength: rule.strength,
        })),
        exit: {
          stop_loss_pct: visualExitConfig.stopLossPct,
          take_profit_pct: visualExitConfig.takeProfitPct,
          trailing_stop_pct: visualExitConfig.trailingStopPct,
        },
        filters: visualFilters,
      },
      indicators: [],
    };
    setDslJson(JSON.stringify(definition, null, 2));
  }, [name, description, visualEntryRules, visualExitConfig, visualFilters]);

  // Auto-sync when switching from visual to JSON mode
  useEffect(() => {
    if (editorMode === 'json' && visualEntryRules.length > 0) {
      syncVisualToJson();
    }
  }, [editorMode, syncVisualToJson, visualEntryRules.length]);

  // Configure Monaco editor with auto-complete
  const handleEditorWillMount = (monaco: Monaco) => {
    monacoRef.current = monaco;

    // Register completion provider for JSON
    monaco.languages.registerCompletionItemProvider('json', {
      triggerCharacters: ['"', '(', ' '],
      provideCompletionItems: (
        model: editor.ITextModel,
        position: Position
      ): languages.ProviderResult<languages.CompletionList> => {
        const word = model.getWordUntilPosition(position);
        const range: IRange = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn,
        };

        const lineContent = model.getLineContent(position.lineNumber);
        const suggestions: languages.CompletionItem[] = [];

        // Check if we're in a condition string
        if (lineContent.includes('condition') || lineContent.includes('filters')) {
          // Add function suggestions
          DSL_FUNCTIONS.forEach((fn) => {
            suggestions.push({
              label: fn.name,
              kind: monaco.languages.CompletionItemKind.Function,
              insertText: fn.signature,
              documentation: fn.description,
              range,
            } as languages.CompletionItem);
          });

          // Add variable suggestions
          DSL_VARIABLES.forEach((v) => {
            suggestions.push({
              label: v.name,
              kind: monaco.languages.CompletionItemKind.Variable,
              insertText: v.name,
              documentation: v.description,
              range,
            } as languages.CompletionItem);
          });

          // Add operator suggestions
          DSL_OPERATORS.forEach((op) => {
            suggestions.push({
              label: op,
              kind: monaco.languages.CompletionItemKind.Operator,
              insertText: op,
              range,
            } as languages.CompletionItem);
          });
        }

        // Check if we're in an action field
        if (lineContent.includes('action')) {
          DSL_ACTIONS.forEach((action) => {
            suggestions.push({
              label: action,
              kind: monaco.languages.CompletionItemKind.Enum,
              insertText: action,
              range,
            } as languages.CompletionItem);
          });
        }

        return { suggestions };
      },
    });
  };

  const handleEditorDidMount = (editorInstance: editor.IStandaloneCodeEditor) => {
    editorRef.current = editorInstance;
  };

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
    setBacktestPassed(false);
    setBacktestResult(null);
    setRequireBacktest(true);
    setPaperTradingDays('7');
    // Reset visual builder state
    setEditorMode('json');
    setVisualEntryRules([]);
    setVisualExitConfig({ stopLossPct: 2.0, takeProfitPct: 4.0 });
    setVisualFilters([]);
  };

  // Pure validation without state updates (for isValid check)
  const parseJson = useCallback((): DSLStrategyDefinition | null => {
    try {
      const parsed = JSON.parse(dslJson);
      if (!parsed.name || !parsed.rules?.entry || !parsed.rules?.exit) {
        return null;
      }
      return parsed as DSLStrategyDefinition;
    } catch {
      return null;
    }
  }, [dslJson]);

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

  // Simulated backtest function (in production, this would call an API)
  const runBacktest = async () => {
    const definition = validateJson();
    if (!definition) return;

    setIsBacktesting(true);
    setBacktestResult(null);

    // Simulate a backtest API call
    await new Promise((resolve) => setTimeout(resolve, 2000));

    // Generate mock backtest results
    const mockResult = {
      totalReturn: Math.random() * 30 - 5, // -5% to 25%
      winRate: 40 + Math.random() * 30, // 40% to 70%
      trades: Math.floor(20 + Math.random() * 80), // 20 to 100 trades
      maxDrawdown: Math.random() * 15, // 0% to 15%
    };

    setBacktestResult(mockResult);
    setIsBacktesting(false);

    // Pass backtest if return > 0 and win rate > 45%
    if (mockResult.totalReturn > 0 && mockResult.winRate > 45) {
      setBacktestPassed(true);
    }
  };

  // Reset backtest when DSL changes
  useEffect(() => {
    setBacktestPassed(false);
    setBacktestResult(null);
  }, [dslJson]);

  const handleSubmit = () => {
    const definition = validateJson();
    if (!definition) return;

    // Check if backtest is required and passed
    if (requireBacktest && !backtestPassed) {
      setParseError('Please run a backtest before creating the strategy');
      return;
    }

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
      is_paper_trading: isPaperTrading || parseInt(paperTradingDays) > 0,
      product_type: productType,
    };

    createMutation.mutate(data);
  };

  const isValid = (name.trim().length > 0 || !!parseJson()?.name) && (!requireBacktest || backtestPassed);

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

          {/* Editor Mode Tabs */}
          <Tabs value={editorMode} onValueChange={(v) => setEditorMode(v as 'json' | 'visual')}>
            <div className="flex items-center justify-between mb-2">
              <TabsList className="h-8">
                <TabsTrigger value="json" className="text-xs h-7 px-3">
                  <Code2 className="h-3 w-3 mr-1" />
                  JSON Editor
                </TabsTrigger>
                <TabsTrigger value="visual" className="text-xs h-7 px-3">
                  <MousePointer2 className="h-3 w-3 mr-1" />
                  Visual Builder
                </TabsTrigger>
              </TabsList>
              <div className="flex gap-2">
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
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={runBacktest}
                  disabled={isBacktesting}
                  className="h-7 text-xs"
                >
                  <FlaskConical className="h-3 w-3 mr-1" />
                  {isBacktesting ? 'Running...' : 'Run Backtest'}
                </Button>
              </div>
            </div>

            {/* JSON Editor Tab */}
            <TabsContent value="json" className="mt-0">
              <div className="space-y-2">
                <div className="border rounded-md overflow-hidden">
                  <Editor
                    height="280px"
                    defaultLanguage="json"
                    value={dslJson}
                    onChange={(value) => {
                      setDslJson(value || '');
                      setParseError(null);
                    }}
                    beforeMount={handleEditorWillMount}
                    onMount={handleEditorDidMount}
                    options={{
                      minimap: { enabled: false },
                      fontSize: 13,
                      lineNumbers: 'on',
                      scrollBeyondLastLine: false,
                      wordWrap: 'on',
                      automaticLayout: true,
                      tabSize: 2,
                      suggestOnTriggerCharacters: true,
                      quickSuggestions: true,
                      formatOnPaste: true,
                      formatOnType: true,
                    }}
                    theme="vs-dark"
                  />
                </div>
              </div>
            </TabsContent>

            {/* Visual Builder Tab */}
            <TabsContent value="visual" className="mt-0">
              <div className="border rounded-md p-4 bg-muted/20 max-h-[320px] overflow-y-auto">
                <VisualRuleBuilder
                  entryRules={visualEntryRules}
                  exitConfig={visualExitConfig}
                  filters={visualFilters}
                  onEntryRulesChange={setVisualEntryRules}
                  onExitConfigChange={setVisualExitConfig}
                  onFiltersChange={setVisualFilters}
                />
              </div>
              {visualEntryRules.length > 0 && (
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={syncVisualToJson}
                  className="mt-2 h-7 text-xs"
                >
                  <Code2 className="h-3 w-3 mr-1" />
                  Generate JSON from Visual
                </Button>
              )}
            </TabsContent>
          </Tabs>

          {/* Errors and Results */}
          {parseError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{parseError}</AlertDescription>
            </Alert>
          )}

          {/* Backtest Results */}
          {backtestResult && (
            <Alert variant={backtestPassed ? 'default' : 'destructive'} className="mt-2">
              <FlaskConical className="h-4 w-4" />
              <AlertDescription>
                <div className="font-semibold mb-1">
                  Backtest Results {backtestPassed ? '✅ Passed' : '⚠️ Warning'}
                </div>
                <div className="grid grid-cols-4 gap-2 text-xs">
                  <div>
                    <span className="text-muted-foreground">Return:</span>{' '}
                    <Badge variant={backtestResult.totalReturn > 0 ? 'default' : 'destructive'}>
                      {backtestResult.totalReturn.toFixed(2)}%
                    </Badge>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Win Rate:</span>{' '}
                    <Badge variant={backtestResult.winRate > 50 ? 'default' : 'secondary'}>
                      {backtestResult.winRate.toFixed(1)}%
                    </Badge>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Trades:</span>{' '}
                    <Badge variant="outline">{backtestResult.trades}</Badge>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Max DD:</span>{' '}
                    <Badge variant={backtestResult.maxDrawdown < 10 ? 'outline' : 'destructive'}>
                      {backtestResult.maxDrawdown.toFixed(1)}%
                    </Badge>
                  </div>
                </div>
                {!backtestPassed && (
                  <p className="text-xs mt-2 text-muted-foreground">
                    Strategy didn&apos;t meet minimum criteria (positive return &amp; &gt;45% win rate). You can still create it but consider reviewing your rules.
                  </p>
                )}
              </AlertDescription>
            </Alert>
          )}

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
                  <div className="flex items-center space-x-2 pt-2">
                    <Switch
                      id="requireBacktest"
                      checked={requireBacktest}
                      onCheckedChange={setRequireBacktest}
                    />
                    <Label htmlFor="requireBacktest" className="flex items-center gap-1">
                      <FlaskConical className="h-3 w-3" />
                      Require Backtest Before Activation
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2 pt-2">
                    <Switch
                      id="paperTrading"
                      checked={isPaperTrading}
                      onCheckedChange={setIsPaperTrading}
                    />
                    <Label htmlFor="paperTrading">Paper Trading Mode</Label>
                  </div>
                  {isPaperTrading && (
                    <div className="space-y-2 pl-6 border-l-2 border-muted">
                      <Label className="flex items-center gap-1">
                        <Beaker className="h-3 w-3" />
                        Paper Trading Trial Period (days)
                      </Label>
                      <Input
                        type="number"
                        min="1"
                        max="90"
                        value={paperTradingDays}
                        onChange={(e) => setPaperTradingDays(e.target.value)}
                        placeholder="7"
                      />
                      <p className="text-xs text-muted-foreground">
                        Strategy will run in paper trading mode for this many days before going live
                      </p>
                    </div>
                  )}
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

