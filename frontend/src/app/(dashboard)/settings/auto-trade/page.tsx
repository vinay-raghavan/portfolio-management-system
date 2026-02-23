'use client';

import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bot, Settings2, Zap, Clock, Sliders, ChevronRight, AlertTriangle, Bookmark, TrendingUp, BarChart3, Newspaper, Sparkles, Shield, Star, Target } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Input } from '@/components/ui/input';
import { useToast } from '@/components/ui/use-toast';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { autoTradeApi, screenerApi, CustomScreener } from '@/lib/api';
import { BrandedSpinner } from '@/components/shared';
import type { AutoTradeConfig, ConfirmationMode, StrategyTemplate, ScreenerSourceType } from '@/types';
import Link from 'next/link';
import { cn } from '@/lib/utils';

// Weight presets for quick configuration
const WEIGHT_PRESETS = [
  { name: 'Balanced', tech: 40, fund: 40, sent: 20, icon: Sparkles, description: 'Equal focus on technical and fundamental' },
  { name: 'Technical', tech: 60, fund: 25, sent: 15, icon: TrendingUp, description: 'Emphasis on price action and trends' },
  { name: 'Fundamental', tech: 25, fund: 60, sent: 15, icon: BarChart3, description: 'Focus on company fundamentals' },
  { name: 'Sentiment', tech: 30, fund: 30, sent: 40, icon: Newspaper, description: 'Higher weight on market sentiment' },
];

// Confidence level options
const CONFIDENCE_LEVELS = [
  { value: 40, label: 'Low', description: 'Include more trades with lower confidence', stars: 1, color: 'text-yellow-500' },
  { value: 60, label: 'Medium', description: 'Balanced confidence threshold', stars: 2, color: 'text-blue-500' },
  { value: 80, label: 'High', description: 'Only high-confidence opportunities', stars: 3, color: 'text-green-500' },
];

const CATEGORIES = [
  { value: 'momentum', label: 'Momentum', description: 'High momentum stocks with strong price trends' },
  { value: 'breakout', label: 'Breakout', description: 'Stocks breaking out of consolidation patterns' },
  { value: 'pullback', label: 'Pullback/Value', description: 'Oversold stocks for mean reversion plays' },
  { value: 'sector', label: 'Sector Rotation', description: 'Strong sector leaders based on rotation strategy' },
];

const CONFIRMATION_MODES: { value: ConfirmationMode; label: string; description: string }[] = [
  { value: 'AUTO', label: 'Automatic', description: 'Execute trades automatically without confirmation' },
  { value: 'NOTIFY', label: 'Notify', description: 'Create pending trades and notify for approval' },
  { value: 'DISABLED', label: 'Disabled', description: 'Do not create any auto-trades for this category' },
];

// Source type selector (Preset vs Custom screener)
function SourceSelector({
  sourceType,
  screenerId,
  customScreeners,
  categoryValue,
  onSourceChange,
  onScreenerChange,
}: {
  sourceType: ScreenerSourceType;
  screenerId: string | null;
  customScreeners: CustomScreener[];
  categoryValue: string;
  onSourceChange: (type: ScreenerSourceType) => void;
  onScreenerChange: (id: string | null) => void;
}) {
  const selectedScreener = customScreeners.find(s => s.id === screenerId);

  return (
    <div className="space-y-3 p-3 border rounded-lg bg-muted/30">
      <Label className="flex items-center gap-2 text-sm font-medium">
        <Target className="h-4 w-4" />
        Screener Source
      </Label>

      <RadioGroup
        value={sourceType}
        onValueChange={(v) => onSourceChange(v as ScreenerSourceType)}
        className="grid grid-cols-2 gap-2"
      >
        <div className="flex items-center">
          <RadioGroupItem value="PRESET" id={`source-preset-${categoryValue}`} className="peer sr-only" />
          <Label
            htmlFor={`source-preset-${categoryValue}`}
            className={cn(
              'flex flex-col items-center w-full p-3 border rounded-lg cursor-pointer transition-all',
              'hover:bg-accent peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-primary/5'
            )}
          >
            <Sparkles className="h-4 w-4 mb-1" />
            <span className="font-medium text-sm">Daily Presets</span>
            <span className="text-[10px] text-muted-foreground">Use built-in screeners</span>
          </Label>
        </div>
        <div className="flex items-center">
          <RadioGroupItem value="CUSTOM" id={`source-custom-${categoryValue}`} className="peer sr-only" />
          <Label
            htmlFor={`source-custom-${categoryValue}`}
            className={cn(
              'flex flex-col items-center w-full p-3 border rounded-lg cursor-pointer transition-all',
              'hover:bg-accent peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-primary/5'
            )}
          >
            <Bookmark className="h-4 w-4 mb-1" />
            <span className="font-medium text-sm">Custom Screener</span>
            <span className="text-[10px] text-muted-foreground">Use your saved screener</span>
          </Label>
        </div>
      </RadioGroup>

      {sourceType === 'CUSTOM' && (
        <div className="space-y-2">
          <Select
            value={screenerId || 'none'}
            onValueChange={(v) => onScreenerChange(v === 'none' ? null : v)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select a saved screener" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">No screener selected</SelectItem>
              {customScreeners.map((s) => (
                <SelectItem key={s.id} value={s.id}>
                  <div className="flex items-center gap-2">
                    <span>{s.name}</span>
                    {s.is_auto_trade_enabled && (
                      <Badge variant="secondary" className="text-[10px]">Auto-Trade</Badge>
                    )}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {selectedScreener && (
            <div className="text-xs text-muted-foreground p-2 bg-muted/50 rounded">
              <p><strong>Universe:</strong> {selectedScreener.universe}</p>
              <p><strong>Filters:</strong> {selectedScreener.filters.length}</p>
              {selectedScreener.run_frequency && (
                <p><strong>Schedule:</strong> {selectedScreener.run_frequency} {selectedScreener.run_time && `at ${selectedScreener.run_time}`}</p>
              )}
            </div>
          )}
          {customScreeners.length === 0 && (
            <p className="text-xs text-muted-foreground">
              No saved screeners found. <Link href="/screener/saved" className="text-primary hover:underline">Create one</Link>
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function AutoTradeConfigCard({
  category,
  config,
  templates,
  customScreeners,
  onUpdate
}: {
  category: typeof CATEGORIES[0];
  config: AutoTradeConfig | undefined;
  templates: StrategyTemplate[];
  customScreeners: CustomScreener[];
  onUpdate: () => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  
  const createMutation = useMutation({
    mutationFn: () => autoTradeApi.createConfig({ category: category.value }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auto-trade-configs'] });
      toast({ title: 'Config created', description: `Auto-trade enabled for ${category.label}` });
    },
    onError: () => toast({ title: 'Error', description: 'Failed to create config', variant: 'destructive' }),
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<AutoTradeConfig>) => autoTradeApi.updateConfig(category.value, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auto-trade-configs'] });
      onUpdate();
    },
    onError: () => toast({ title: 'Error', description: 'Failed to update config', variant: 'destructive' }),
  });

  if (!config) {
    return (
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-muted-foreground" />
            {category.label}
          </CardTitle>
          <CardDescription>{category.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
            {createMutation.isPending ? 'Enabling...' : 'Enable Auto-Trade'}
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Bot className={`h-5 w-5 ${config.is_enabled ? 'text-green-500' : 'text-muted-foreground'}`} />
            {category.label}
          </CardTitle>
          <div className="flex items-center gap-2">
            <Switch
              checked={config.is_enabled}
              onCheckedChange={(checked) => updateMutation.mutate({ is_enabled: checked })}
            />
            <Badge variant={config.is_enabled ? 'default' : 'secondary'}>
              {config.is_enabled ? 'Active' : 'Inactive'}
            </Badge>
          </div>
        </div>
        <CardDescription>{category.description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label>Confirmation Mode</Label>
            <Select
              value={config.confirmation_mode}
              onValueChange={(v) => updateMutation.mutate({ confirmation_mode: v as ConfirmationMode })}
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {CONFIRMATION_MODES.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    <div className="flex flex-col"><span>{m.label}</span></div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Strategy Template</Label>
            <Select
              value={config.strategy_template_id || 'none'}
              onValueChange={(v) => updateMutation.mutate({ strategy_template_id: v === 'none' ? null : v })}
            >
              <SelectTrigger><SelectValue placeholder="Select template" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No template (auto-infer)</SelectItem>
                {templates.map((t) => (
                  <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Source Selection (Preset vs Custom Screener) */}
        <SourceSelector
          sourceType={config.source_type || 'PRESET'}
          screenerId={config.screener_id}
          customScreeners={customScreeners}
          categoryValue={category.value}
          onSourceChange={(type) => updateMutation.mutate({ source_type: type, screener_id: type === 'PRESET' ? null : config.screener_id })}
          onScreenerChange={(id) => updateMutation.mutate({ screener_id: id })}
        />
        <div className="grid gap-4 md:grid-cols-3">
          <div className="space-y-2">
            <Label>Max Trades Per Day</Label>
            <Input
              type="number"
              min={1}
              max={20}
              value={config.max_trades_per_day}
              onChange={(e) => updateMutation.mutate({ max_trades_per_day: parseInt(e.target.value) || 5 })}
            />
          </div>
          <div className="space-y-2">
            <Label>Min Confidence (%)</Label>
            <Slider
              value={[config.min_confidence]}
              min={0}
              max={100}
              step={5}
              onValueCommit={(v) => updateMutation.mutate({ min_confidence: v[0] })}
            />
            <p className="text-sm text-muted-foreground">{config.min_confidence}%</p>
          </div>
          <div className="space-y-2">
            <Label className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Run Time (IST)
            </Label>
            <Input
              type="time"
              value={config.run_time || '09:20'}
              onChange={(e) => updateMutation.mutate({ run_time: e.target.value })}
            />
            <p className="text-sm text-muted-foreground">Daily screener scan time</p>
          </div>
        </div>
        <WeightConfigPanel category={category.value} config={config} onUpdate={onUpdate} />
      </CardContent>
    </Card>
  );
}

// Mini bar chart for score breakdown visualization
function ScoreBreakdownChart({ weights }: { weights: { technical: number; fundamental: number; sentiment: number } }) {
  const total = weights.technical + weights.fundamental + weights.sentiment;
  if (total === 0) return null;

  return (
    <div className="flex h-2 rounded-full overflow-hidden bg-muted">
      <div
        className="bg-blue-500 transition-all duration-200"
        style={{ width: `${weights.technical}%` }}
        title={`Technical: ${weights.technical}%`}
      />
      <div
        className="bg-purple-500 transition-all duration-200"
        style={{ width: `${weights.fundamental}%` }}
        title={`Fundamental: ${weights.fundamental}%`}
      />
      <div
        className="bg-orange-500 transition-all duration-200"
        style={{ width: `${weights.sentiment}%` }}
        title={`Sentiment: ${weights.sentiment}%`}
      />
    </div>
  );
}

// Preset grid for quick weight selection
function PresetGrid({
  onSelect,
  currentWeights
}: {
  onSelect: (tech: number, fund: number, sent: number) => void;
  currentWeights: { technical: number; fundamental: number; sentiment: number };
}) {
  const isPresetActive = (preset: typeof WEIGHT_PRESETS[0]) =>
    preset.tech === currentWeights.technical &&
    preset.fund === currentWeights.fundamental &&
    preset.sent === currentWeights.sentiment;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
      {WEIGHT_PRESETS.map((preset) => {
        const Icon = preset.icon;
        const isActive = isPresetActive(preset);
        return (
          <TooltipProvider key={preset.name}>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant={isActive ? 'default' : 'outline'}
                  size="sm"
                  className={cn('flex flex-col h-auto py-2 gap-1', isActive && 'ring-2 ring-primary')}
                  onClick={() => onSelect(preset.tech, preset.fund, preset.sent)}
                >
                  <Icon className="h-4 w-4" />
                  <span className="text-xs">{preset.name}</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p className="font-medium">{preset.description}</p>
                <p className="text-xs text-muted-foreground">
                  Tech: {preset.tech}% | Fund: {preset.fund}% | Sent: {preset.sent}%
                </p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        );
      })}
    </div>
  );
}

// Confidence level selector with visual stars
function ConfidenceSelector({
  value,
  onChange,
}: {
  value: number;
  onChange: (value: number) => void;
}) {
  // Find closest confidence level
  const getClosestLevel = (v: number) => {
    return CONFIDENCE_LEVELS.reduce((prev, curr) =>
      Math.abs(curr.value - v) < Math.abs(prev.value - v) ? curr : prev
    );
  };

  const currentLevel = getClosestLevel(value);

  return (
    <div className="space-y-2">
      <Label className="flex items-center gap-2">
        <Shield className="h-4 w-4" />
        Minimum Confidence Level
      </Label>
      <RadioGroup
        value={currentLevel.value.toString()}
        onValueChange={(v) => onChange(parseInt(v))}
        className="grid grid-cols-3 gap-2"
      >
        {CONFIDENCE_LEVELS.map((level) => (
          <div key={level.value} className="flex items-center">
            <RadioGroupItem
              value={level.value.toString()}
              id={`confidence-${level.value}`}
              className="peer sr-only"
            />
            <Label
              htmlFor={`confidence-${level.value}`}
              className={cn(
                'flex flex-col items-center w-full p-3 border rounded-lg cursor-pointer transition-all',
                'hover:bg-accent peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-primary/5'
              )}
            >
              <div className="flex gap-0.5 mb-1">
                {Array.from({ length: level.stars }).map((_, i) => (
                  <Star key={i} className={cn('h-3 w-3 fill-current', level.color)} />
                ))}
              </div>
              <span className="font-medium text-sm">{level.label}</span>
              <span className="text-[10px] text-muted-foreground text-center">{level.value}%+</span>
            </Label>
          </div>
        ))}
      </RadioGroup>
      <p className="text-xs text-muted-foreground">{currentLevel.description}</p>
    </div>
  );
}

function WeightConfigPanel({
  category,
  config,
  onUpdate
}: {
  category: string;
  config: AutoTradeConfig;
  onUpdate: () => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [weights, setWeights] = useState({
    technical: config.weight_technical,
    fundamental: config.weight_fundamental,
    sentiment: config.weight_sentiment,
  });
  const [minConfidence, setMinConfidence] = useState(config.min_confidence);

  const updateMutation = useMutation({
    mutationFn: () => autoTradeApi.updateWeights(category, {
      weight_technical: weights.technical,
      weight_fundamental: weights.fundamental,
      weight_sentiment: weights.sentiment,
      min_confidence: minConfidence,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auto-trade-configs'] });
      toast({ title: 'Settings updated', description: 'Multi-factor weights and confidence saved' });
      onUpdate();
    },
    onError: () => toast({ title: 'Error', description: 'Failed to update settings', variant: 'destructive' }),
  });

  const total = weights.technical + weights.fundamental + weights.sentiment;
  const isValid = total === 100;

  // Auto-normalize: when one slider changes, adjust others proportionally
  const handleWeightChange = useCallback((key: 'technical' | 'fundamental' | 'sentiment', newValue: number) => {
    setWeights(prev => {
      const oldValue = prev[key];
      const diff = newValue - oldValue;
      const others = (['technical', 'fundamental', 'sentiment'] as const).filter(k => k !== key);

      // Calculate remaining to distribute
      const otherTotal = others.reduce((sum, k) => sum + prev[k], 0);

      if (otherTotal === 0) {
        // If others are 0, just set the value
        return { ...prev, [key]: Math.min(100, Math.max(0, newValue)) };
      }

      // Distribute the difference proportionally among others
      const newWeights = { ...prev, [key]: newValue };
      let remainingDiff = -diff;

      others.forEach((otherKey, idx) => {
        if (idx === others.length - 1) {
          // Last one gets the remainder to ensure sum is 100
          newWeights[otherKey] = 100 - newValue - newWeights[others[0]];
        } else {
          const proportion = prev[otherKey] / otherTotal;
          const adjustment = Math.round(remainingDiff * proportion);
          newWeights[otherKey] = Math.max(0, Math.min(100, prev[otherKey] + adjustment));
        }
      });

      // Ensure non-negative and valid
      others.forEach(k => {
        newWeights[k] = Math.max(0, newWeights[k]);
      });

      return newWeights;
    });
  }, []);

  // Apply preset
  const applyPreset = useCallback((tech: number, fund: number, sent: number) => {
    setWeights({ technical: tech, fundamental: fund, sentiment: sent });
  }, []);

  return (
    <div className="space-y-4 pt-4 border-t">
      {/* Header with total badge */}
      <div className="flex items-center justify-between">
        <Label className="flex items-center gap-2 text-base font-medium">
          <Sliders className="h-4 w-4" />
          Multi-Factor Scoring
        </Label>
        <Badge variant={isValid ? 'outline' : 'destructive'}>
          Total: {total}%
        </Badge>
      </div>

      {/* Score breakdown visualization */}
      <ScoreBreakdownChart weights={weights} />

      {/* Preset grid */}
      <div className="space-y-2">
        <Label className="text-xs text-muted-foreground">Quick Presets</Label>
        <PresetGrid onSelect={applyPreset} currentWeights={weights} />
      </div>

      {/* Weight sliders with icons */}
      <div className="grid gap-3 pt-2">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 w-28">
            <TrendingUp className="h-4 w-4 text-blue-500" />
            <Label className="text-sm">Technical</Label>
          </div>
          <Slider
            value={[weights.technical]}
            min={0} max={100} step={5}
            className="flex-1"
            onValueChange={(v) => handleWeightChange('technical', v[0])}
          />
          <span className="w-12 text-right text-sm font-mono">{weights.technical}%</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 w-28">
            <BarChart3 className="h-4 w-4 text-purple-500" />
            <Label className="text-sm">Fundamental</Label>
          </div>
          <Slider
            value={[weights.fundamental]}
            min={0} max={100} step={5}
            className="flex-1"
            onValueChange={(v) => handleWeightChange('fundamental', v[0])}
          />
          <span className="w-12 text-right text-sm font-mono">{weights.fundamental}%</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 w-28">
            <Newspaper className="h-4 w-4 text-orange-500" />
            <Label className="text-sm">Sentiment</Label>
          </div>
          <Slider
            value={[weights.sentiment]}
            min={0} max={100} step={5}
            className="flex-1"
            onValueChange={(v) => handleWeightChange('sentiment', v[0])}
          />
          <span className="w-12 text-right text-sm font-mono">{weights.sentiment}%</span>
        </div>
      </div>

      {!isValid && (
        <p className="text-sm text-destructive flex items-center gap-1">
          <AlertTriangle className="h-3 w-3" />
          Weights must sum to 100%
        </p>
      )}

      {/* Confidence selector */}
      <ConfidenceSelector value={minConfidence} onChange={setMinConfidence} />

      {/* Save button */}
      <Button
        onClick={() => updateMutation.mutate()}
        disabled={!isValid || updateMutation.isPending}
        className="w-full"
      >
        {updateMutation.isPending ? 'Saving...' : 'Save Multi-Factor Settings'}
      </Button>
    </div>
  );
}

export default function AutoTradeSettingsPage() {
  const queryClient = useQueryClient();

  const { data: configsData, isLoading: configsLoading } = useQuery({
    queryKey: ['auto-trade-configs'],
    queryFn: () => autoTradeApi.getConfigs().then(r => r.data),
  });

  const { data: templatesData, isLoading: templatesLoading } = useQuery({
    queryKey: ['strategy-templates'],
    queryFn: () => autoTradeApi.getTemplates().then(r => r.data),
  });

  const { data: screenersData, isLoading: screenersLoading } = useQuery({
    queryKey: ['custom-screeners'],
    queryFn: () => screenerApi.getCustomScreeners().then(r => r.data),
  });

  const configs = configsData?.configs || [];
  const templates = templatesData?.templates || [];
  const customScreeners = screenersData?.screeners || [];

  const getConfigForCategory = (category: string) =>
    configs.find(c => c.category === category);

  if (configsLoading || templatesLoading || screenersLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <BrandedSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Zap className="h-8 w-8" />
            Auto-Trade Settings
          </h1>
          <p className="text-muted-foreground">
            Configure automatic trading from screener recommendations
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Link href="/screener/saved">
            <Button variant="outline" className="gap-2">
              <Bookmark className="h-4 w-4" />
              Saved Screeners
              <ChevronRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link href="/algo/templates">
            <Button variant="outline" className="gap-2">
              <Settings2 className="h-4 w-4" />
              Templates
              <ChevronRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link href="/dashboard">
            <Button variant="outline" className="gap-2">
              <Clock className="h-4 w-4" />
              Pending Trades
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid gap-6">
        {CATEGORIES.map((category) => (
          <AutoTradeConfigCard
            key={category.value}
            category={category}
            config={getConfigForCategory(category.value)}
            templates={templates}
            customScreeners={customScreeners}
            onUpdate={() => queryClient.invalidateQueries({ queryKey: ['auto-trade-configs'] })}
          />
        ))}
      </div>
    </div>
  );
}

