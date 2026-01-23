'use client';

import { Zap, TrendingUp, Target, BarChart3, Layers } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { ScreenerPresetType } from '@/lib/api';

interface PresetInfo {
  type: ScreenerPresetType;
  name: string;
  description: string;
  icon: React.ReactNode;
  color: string;
}

const PRESETS: PresetInfo[] = [
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
    name: 'Consolidation',
    description: 'Tight range before potential move',
    icon: <Target className="h-5 w-5" />,
    color: 'text-orange-500',
  },
  {
    type: 'value',
    name: 'Value',
    description: 'Pullback opportunities in strong stocks',
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
];

interface PresetSelectorProps {
  selectedPreset: ScreenerPresetType | null;
  onSelect: (preset: ScreenerPresetType) => void;
  isLoading?: boolean;
}

export function PresetSelector({ selectedPreset, onSelect, isLoading }: PresetSelectorProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Quick Presets</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-2">
          {PRESETS.map((preset) => (
            <Button
              key={preset.type}
              variant={selectedPreset === preset.type ? 'default' : 'outline'}
              className={cn(
                'h-auto py-3 px-3 flex flex-col items-center gap-1 whitespace-normal',
                selectedPreset !== preset.type && preset.color
              )}
              onClick={() => onSelect(preset.type)}
              disabled={isLoading}
            >
              {preset.icon}
              <span className="text-xs font-medium">{preset.name}</span>
            </Button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

