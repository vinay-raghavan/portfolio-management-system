'use client';

import { Zap, TrendingUp, TrendingDown, Target, BarChart3, Layers, Award, Settings2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import type { ScreenerPresetType, StrictnessLevel } from '@/lib/api';

interface PresetInfo {
  type: ScreenerPresetType;
  name: string;
  description: string;
  icon: React.ReactNode;
  color: string;
}

interface StrictnessInfo {
  level: StrictnessLevel;
  name: string;
  description: string;
}

const STRICTNESS_LEVELS: StrictnessInfo[] = [
  { level: 'strict', name: 'Strict', description: 'Professional criteria (few results)' },
  { level: 'moderate', name: 'Moderate', description: 'Balanced criteria (default)' },
  { level: 'relaxed', name: 'Relaxed', description: 'Looser criteria (more results)' },
  { level: 'exploratory', name: 'Exploratory', description: 'Very loose (idea generation)' },
];

const PRESETS: PresetInfo[] = [
  {
    type: 'minervini',
    name: 'Minervini',
    description: 'Stage 2 uptrend template (50>150>200 MA)',
    icon: <Award className="h-5 w-5" />,
    color: 'text-yellow-500',
  },
  {
    type: 'momentum',
    name: 'Momentum',
    description: 'Strong upward price movement with volume',
    icon: <TrendingUp className="h-5 w-5" />,
    color: 'text-green-500',
  },
  {
    type: 'breakout',
    name: 'Breakout',
    description: 'Breaking out of consolidation ranges',
    icon: <Zap className="h-5 w-5" />,
    color: 'text-blue-500',
  },
  {
    type: 'consolidation',
    name: 'VCP',
    description: 'Volatility contraction pattern',
    icon: <Target className="h-5 w-5" />,
    color: 'text-orange-500',
  },
  {
    type: 'value',
    name: 'Pullback',
    description: 'Oversold pullback in uptrend',
    icon: <BarChart3 className="h-5 w-5" />,
    color: 'text-purple-500',
  },
  {
    type: 'sector_rotation',
    name: 'Sector Leaders',
    description: 'Leaders in strong performing sectors',
    icon: <Layers className="h-5 w-5" />,
    color: 'text-cyan-500',
  },
  {
    type: 'bearish_short',
    name: '⚠️ Short Sell',
    description: 'Weak stocks for shorting (MIS/SLB only)',
    icon: <TrendingDown className="h-5 w-5" />,
    color: 'text-red-500',
  },
];

interface PresetSelectorProps {
  selectedPreset: ScreenerPresetType | null;
  strictness: StrictnessLevel;
  onSelectPreset: (preset: ScreenerPresetType) => void;
  onStrictnessChange: (level: StrictnessLevel) => void;
  isLoading?: boolean;
}

export function PresetSelector({
  selectedPreset,
  strictness,
  onSelectPreset,
  onStrictnessChange,
  isLoading,
}: PresetSelectorProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Quick Presets</CardTitle>
          <div className="flex items-center gap-2">
            <Settings2 className="h-4 w-4 text-muted-foreground" />
            <Select value={strictness} onValueChange={(v) => onStrictnessChange(v as StrictnessLevel)}>
              <SelectTrigger className="w-[140px] h-8 text-xs">
                <SelectValue placeholder="Strictness" />
              </SelectTrigger>
              <SelectContent>
                {STRICTNESS_LEVELS.map((level) => (
                  <SelectItem key={level.level} value={level.level}>
                    <div className="flex flex-col">
                      <span>{level.name}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
          {PRESETS.map((preset) => (
            <Button
              key={preset.type}
              variant={selectedPreset === preset.type ? 'default' : 'outline'}
              className={cn(
                'h-auto py-3 px-3 flex flex-col items-center gap-1 whitespace-normal',
                selectedPreset !== preset.type && preset.color
              )}
              onClick={() => onSelectPreset(preset.type)}
              disabled={isLoading}
            >
              {preset.icon}
              <span className="text-xs font-medium">{preset.name}</span>
            </Button>
          ))}
        </div>
        <p className="text-xs text-muted-foreground mt-3">
          {STRICTNESS_LEVELS.find((l) => l.level === strictness)?.description}
        </p>
      </CardContent>
    </Card>
  );
}

