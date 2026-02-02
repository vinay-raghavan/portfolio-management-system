'use client';

import { Zap, TrendingUp, Target, BarChart3, Layers, Award, Database, Play, Settings2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import { FilterBuilder } from './FilterBuilder';
import { UniverseSelector, type UniverseType } from './UniverseSelector';
import type { ScreenerPresetType, StrictnessLevel, FilterConfig } from '@/lib/api';

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
  { level: 'strict', name: 'Strict', description: 'Professional-grade criteria, very few results' },
  { level: 'moderate', name: 'Moderate', description: 'Balanced criteria, good for trending markets' },
  { level: 'relaxed', name: 'Relaxed', description: 'Looser criteria, more candidates to review' },
  { level: 'exploratory', name: 'Exploratory', description: 'Very loose, for idea generation' },
];

const PRESETS: PresetInfo[] = [
  { type: 'minervini', name: 'Minervini', description: 'Stage 2 uptrend (50>150>200 MA)', icon: <Award className="h-5 w-5" />, color: 'text-yellow-500' },
  { type: 'momentum', name: 'Momentum', description: 'Strong price movement + volume', icon: <TrendingUp className="h-5 w-5" />, color: 'text-green-500' },
  { type: 'breakout', name: 'Breakout', description: 'Breaking consolidation ranges', icon: <Zap className="h-5 w-5" />, color: 'text-blue-500' },
  { type: 'consolidation', name: 'VCP', description: 'Volatility contraction pattern', icon: <Target className="h-5 w-5" />, color: 'text-orange-500' },
  { type: 'value', name: 'Pullback', description: 'Oversold pullback in uptrend', icon: <BarChart3 className="h-5 w-5" />, color: 'text-purple-500' },
  { type: 'sector_rotation', name: 'Sector Leaders', description: 'Strong sector performers', icon: <Layers className="h-5 w-5" />, color: 'text-cyan-500' },
];

interface ScreenerConfigProps {
  universe: UniverseType;
  onUniverseChange: (universe: UniverseType) => void;
  mode: 'preset' | 'custom';
  onModeChange: (mode: 'preset' | 'custom') => void;
  selectedPreset: ScreenerPresetType | null;
  onSelectPreset: (preset: ScreenerPresetType) => void;
  strictness: StrictnessLevel;
  onStrictnessChange: (level: StrictnessLevel) => void;
  filters: FilterConfig[];
  onFiltersChange: (filters: FilterConfig[]) => void;
  onRunCustom: () => void;
  isLoading?: boolean;
}

export function ScreenerConfig({
  universe,
  onUniverseChange,
  mode,
  onModeChange,
  selectedPreset,
  onSelectPreset,
  strictness,
  onStrictnessChange,
  filters,
  onFiltersChange,
  onRunCustom,
  isLoading,
}: ScreenerConfigProps) {
  return (
    <Card>
      <CardHeader className="pb-4">
        <CardTitle className="text-lg flex items-center gap-2">
          <Settings2 className="h-5 w-5" />
          Screener Configuration
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Step 1: Universe */}
        <div className="space-y-2">
          <Label className="text-sm font-medium text-muted-foreground">1. Stock Universe</Label>
          <UniverseSelector value={universe} onChange={onUniverseChange} disabled={isLoading} />
        </div>

        {/* Step 2: Mode */}
        <div className="space-y-2">
          <Label className="text-sm font-medium text-muted-foreground">2. Screening Mode</Label>
          <RadioGroup value={mode} onValueChange={(v) => onModeChange(v as 'preset' | 'custom')} className="flex gap-4">
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="preset" id="mode-preset" disabled={isLoading} />
              <Label htmlFor="mode-preset" className="cursor-pointer">Quick Presets</Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="custom" id="mode-custom" disabled={isLoading} />
              <Label htmlFor="mode-custom" className="cursor-pointer">Custom Filters</Label>
            </div>
          </RadioGroup>
        </div>

        {/* Step 3 & 4: Mode-specific content */}
        {mode === 'preset' ? (
          <>
            {/* Step 3: Strictness */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">3. Criteria Strictness</Label>
              <div className="flex items-center gap-3">
                <Select value={strictness} onValueChange={(v) => onStrictnessChange(v as StrictnessLevel)} disabled={isLoading}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Select strictness" />
                  </SelectTrigger>
                  <SelectContent>
                    {STRICTNESS_LEVELS.map((level) => (
                      <SelectItem key={level.level} value={level.level}>
                        {level.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <span className="text-sm text-muted-foreground">
                  {STRICTNESS_LEVELS.find((l) => l.level === strictness)?.description}
                </span>
              </div>
            </div>

            {/* Step 4: Preset Selection */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">4. Select Strategy</Label>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
                {PRESETS.map((preset) => (
                  <Button
                    key={preset.type}
                    variant={selectedPreset === preset.type ? 'default' : 'outline'}
                    className={cn('h-auto py-3 px-3 flex flex-col items-center gap-1', selectedPreset !== preset.type && preset.color)}
                    onClick={() => onSelectPreset(preset.type)}
                    disabled={isLoading}
                    title={preset.description}
                  >
                    {preset.icon}
                    <span className="text-xs font-medium">{preset.name}</span>
                  </Button>
                ))}
              </div>
            </div>
          </>
        ) : (
          <>
            {/* Custom Filters */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">3. Build Filters</Label>
              <FilterBuilder filters={filters} onChange={onFiltersChange} disabled={isLoading} />
            </div>
            <Button onClick={onRunCustom} disabled={isLoading || filters.length === 0} className="w-full">
              <Play className="h-4 w-4 mr-2" />
              {isLoading ? 'Running...' : 'Run Screener'}
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  );
}

