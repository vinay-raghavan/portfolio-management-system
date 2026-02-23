'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bot, Settings2, Zap, Clock, Sliders, ChevronRight, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Input } from '@/components/ui/input';
import { useToast } from '@/components/ui/use-toast';
import { autoTradeApi } from '@/lib/api';
import { BrandedSpinner } from '@/components/shared';
import type { AutoTradeConfig, ConfirmationMode, StrategyTemplate } from '@/types';
import Link from 'next/link';

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

function AutoTradeConfigCard({ 
  category, 
  config, 
  templates, 
  onUpdate 
}: { 
  category: typeof CATEGORIES[0]; 
  config: AutoTradeConfig | undefined;
  templates: StrategyTemplate[];
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
        <div className="grid gap-4 md:grid-cols-2">
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
        </div>
        <WeightConfigPanel category={category.value} config={config} onUpdate={onUpdate} />
      </CardContent>
    </Card>
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

  const updateMutation = useMutation({
    mutationFn: () => autoTradeApi.updateWeights(category, {
      weight_technical: weights.technical,
      weight_fundamental: weights.fundamental,
      weight_sentiment: weights.sentiment,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auto-trade-configs'] });
      toast({ title: 'Weights updated', description: 'Multi-factor weights saved successfully' });
      onUpdate();
    },
    onError: () => toast({ title: 'Error', description: 'Failed to update weights', variant: 'destructive' }),
  });

  const total = weights.technical + weights.fundamental + weights.sentiment;
  const isValid = total === 100;

  return (
    <div className="space-y-3 pt-4 border-t">
      <div className="flex items-center justify-between">
        <Label className="flex items-center gap-2">
          <Sliders className="h-4 w-4" />
          Multi-Factor Weights
        </Label>
        <Badge variant={isValid ? 'outline' : 'destructive'}>
          Total: {total}%
        </Badge>
      </div>
      <div className="grid gap-3">
        <div className="flex items-center gap-3">
          <Label className="w-24 text-sm">Technical</Label>
          <Slider
            value={[weights.technical]}
            min={0} max={100} step={5}
            className="flex-1"
            onValueChange={(v) => setWeights(prev => ({ ...prev, technical: v[0] }))}
          />
          <span className="w-12 text-right text-sm">{weights.technical}%</span>
        </div>
        <div className="flex items-center gap-3">
          <Label className="w-24 text-sm">Fundamental</Label>
          <Slider
            value={[weights.fundamental]}
            min={0} max={100} step={5}
            className="flex-1"
            onValueChange={(v) => setWeights(prev => ({ ...prev, fundamental: v[0] }))}
          />
          <span className="w-12 text-right text-sm">{weights.fundamental}%</span>
        </div>
        <div className="flex items-center gap-3">
          <Label className="w-24 text-sm">Sentiment</Label>
          <Slider
            value={[weights.sentiment]}
            min={0} max={100} step={5}
            className="flex-1"
            onValueChange={(v) => setWeights(prev => ({ ...prev, sentiment: v[0] }))}
          />
          <span className="w-12 text-right text-sm">{weights.sentiment}%</span>
        </div>
      </div>
      {!isValid && (
        <p className="text-sm text-destructive flex items-center gap-1">
          <AlertTriangle className="h-3 w-3" />
          Weights must sum to 100%
        </p>
      )}
      <Button
        size="sm"
        onClick={() => updateMutation.mutate()}
        disabled={!isValid || updateMutation.isPending}
      >
        Save Weights
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

  const configs = configsData?.configs || [];
  const templates = templatesData?.templates || [];

  const getConfigForCategory = (category: string) =>
    configs.find(c => c.category === category);

  if (configsLoading || templatesLoading) {
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
        <div className="flex gap-2">
          <Link href="/algo/templates">
            <Button variant="outline" className="gap-2">
              <Settings2 className="h-4 w-4" />
              Manage Templates
              <ChevronRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link href="/dashboard">
            <Button variant="outline" className="gap-2">
              <Clock className="h-4 w-4" />
              View Pending Trades
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
            onUpdate={() => queryClient.invalidateQueries({ queryKey: ['auto-trade-configs'] })}
          />
        ))}
      </div>
    </div>
  );
}

