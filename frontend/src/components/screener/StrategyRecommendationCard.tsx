'use client';

import { useState } from 'react';
import { Brain, Sparkles, ChevronDown, ChevronUp, Zap, Target, TrendingUp, BarChart3, Activity, Check, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { cn } from '@/lib/utils';
import type { InferStrategyResponse, StrategyRecommendation } from '@/lib/api';

interface StrategyRecommendationCardProps {
  inference: InferStrategyResponse;
  symbolCount: number;
  onCreateStrategy: (data: {
    name: string;
    strategyType: string;
    params: Record<string, unknown>;
    productType: 'DELIVERY' | 'INTRADAY' | 'MARGIN';
  }) => void;
  isCreating?: boolean;
}

const intentIcons: Record<string, React.ReactNode> = {
  momentum: <TrendingUp className="h-4 w-4" />,
  mean_reversion: <Activity className="h-4 w-4" />,
  breakout: <Zap className="h-4 w-4" />,
  trend_following: <BarChart3 className="h-4 w-4" />,
  swing: <Target className="h-4 w-4" />,
};

const intentColors: Record<string, string> = {
  momentum: 'bg-green-500/10 text-green-600 border-green-500/20',
  mean_reversion: 'bg-blue-500/10 text-blue-600 border-blue-500/20',
  breakout: 'bg-orange-500/10 text-orange-600 border-orange-500/20',
  trend_following: 'bg-purple-500/10 text-purple-600 border-purple-500/20',
  swing: 'bg-cyan-500/10 text-cyan-600 border-cyan-500/20',
};

export function StrategyRecommendationCard({
  inference,
  symbolCount,
  onCreateStrategy,
  isCreating,
}: StrategyRecommendationCardProps) {
  const [strategyName, setStrategyName] = useState('');
  const [selectedStrategy, setSelectedStrategy] = useState<StrategyRecommendation>(
    inference.recommended_strategy
  );
  const [productType, setProductType] = useState<'DELIVERY' | 'INTRADAY' | 'MARGIN'>('INTRADAY');
  const [showAlternatives, setShowAlternatives] = useState(false);
  const [showParams, setShowParams] = useState(false);
  const [editedParams, setEditedParams] = useState<Record<string, unknown>>(
    inference.recommended_strategy.suggested_params
  );

  const { filter_analysis } = inference;
  const confidencePercent = Math.round(selectedStrategy.confidence * 100);

  const handleSelectStrategy = (strategy: StrategyRecommendation) => {
    setSelectedStrategy(strategy);
    setEditedParams(strategy.suggested_params);
  };

  const handleParamChange = (key: string, value: string) => {
    const numValue = parseFloat(value);
    setEditedParams((prev) => ({
      ...prev,
      [key]: isNaN(numValue) ? value : numValue,
    }));
  };

  const handleCreate = () => {
    if (!strategyName.trim()) return;
    onCreateStrategy({
      name: strategyName.trim(),
      strategyType: selectedStrategy.strategy_type,
      params: editedParams,
      productType,
    });
  };

  return (
    <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Brain className="h-5 w-5 text-primary" />
          Smart Strategy Recommendation
          <Badge variant="outline" className="ml-auto text-xs">
            <Sparkles className="h-3 w-3 mr-1" />
            AI Powered
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Filter Analysis */}
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline" className={cn('border', intentColors[filter_analysis.primary_intent])}>
            {intentIcons[filter_analysis.primary_intent]}
            <span className="ml-1 capitalize">{filter_analysis.primary_intent.replace('_', ' ')}</span>
          </Badge>
          <Badge variant="outline" className="capitalize">
            {filter_analysis.risk_profile} Risk
          </Badge>
          {filter_analysis.detected_patterns.slice(0, 2).map((pattern, i) => (
            <Badge key={i} variant="secondary" className="text-xs">
              {pattern}
            </Badge>
          ))}
        </div>

        {/* Recommended Strategy */}
        <div className="p-3 rounded-lg bg-background border">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold">{selectedStrategy.strategy_name}</span>
                <Badge variant={confidencePercent >= 80 ? 'default' : 'secondary'}>
                  {confidencePercent}% match
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground mt-1">{selectedStrategy.description}</p>
            </div>
          </div>

          {/* Reasoning */}
          <div className="mt-3 space-y-1">
            {selectedStrategy.reasoning.slice(0, 3).map((reason, i) => (
              <div key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                <Check className="h-3 w-3 mt-0.5 text-green-500 shrink-0" />
                <span>{reason}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Alternatives */}
        {inference.alternative_strategies.length > 0 && (
          <Collapsible open={showAlternatives} onOpenChange={setShowAlternatives}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" className="w-full justify-between">
                <span className="text-xs text-muted-foreground">
                  {inference.alternative_strategies.length} alternative strategies
                </span>
                {showAlternatives ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-2 pt-2">
              {inference.alternative_strategies.map((alt, i) => (
                <button
                  key={i}
                  onClick={() => handleSelectStrategy(alt)}
                  className={cn(
                    'w-full p-2 rounded-lg border text-left transition-colors',
                    selectedStrategy.strategy_type === alt.strategy_type
                      ? 'border-primary bg-primary/5'
                      : 'hover:bg-muted/50'
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{alt.strategy_name}</span>
                    <Badge variant="outline" className="text-xs">
                      {Math.round(alt.confidence * 100)}%
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">{alt.description}</p>
                </button>
              ))}
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* Parameters */}
        <Collapsible open={showParams} onOpenChange={setShowParams}>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="w-full justify-between">
              <span className="text-xs text-muted-foreground">Strategy Parameters</span>
              {showParams ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="pt-2">
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(editedParams).map(([key, value]) => (
                <div key={key} className="space-y-1">
                  <Label className="text-xs capitalize">{key.replace(/_/g, ' ')}</Label>
                  <Input
                    type="text"
                    value={String(value)}
                    onChange={(e) => handleParamChange(key, e.target.value)}
                    className="h-8 text-sm"
                  />
                </div>
              ))}
            </div>
          </CollapsibleContent>
        </Collapsible>

        {/* Create Strategy Form */}
        <div className="space-y-3 pt-2 border-t">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Strategy Name</Label>
              <Input
                placeholder="My Smart Strategy"
                value={strategyName}
                onChange={(e) => setStrategyName(e.target.value)}
                className="h-9"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Product Type</Label>
              <Select value={productType} onValueChange={(v) => setProductType(v as typeof productType)}>
                <SelectTrigger className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="INTRADAY">Intraday (MIS)</SelectItem>
                  <SelectItem value="DELIVERY">Delivery (CNC)</SelectItem>
                  <SelectItem value="MARGIN">Margin (MTF)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button
            onClick={handleCreate}
            disabled={!strategyName.trim() || isCreating}
            className="w-full"
          >
            {isCreating ? (
              'Creating...'
            ) : (
              <>
                <Zap className="h-4 w-4 mr-2" />
                Create Strategy with {symbolCount} Symbols
              </>
            )}
          </Button>

          <p className="text-xs text-muted-foreground text-center flex items-center justify-center gap-1">
            <AlertCircle className="h-3 w-3" />
            Strategy will be created in inactive state
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

