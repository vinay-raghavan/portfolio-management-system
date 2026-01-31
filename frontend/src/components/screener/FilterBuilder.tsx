'use client';

import { useState } from 'react';
import { Plus, X, Sliders } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { FilterConfig, FilterType } from '@/lib/api';

interface FilterDefinition {
  type: FilterType;
  name: string;
  description: string;
  defaultParams: Record<string, unknown>;
  paramLabels: Record<string, string>;
}

const FILTER_DEFINITIONS: FilterDefinition[] = [
  {
    type: 'volume',
    name: 'Volume Filter',
    description: 'Filter by trading volume',
    defaultParams: { min_relative_volume: 1.5, lookback_period: 20 },
    paramLabels: { min_relative_volume: 'Min Relative Volume', lookback_period: 'Lookback Days' },
  },
  {
    type: 'momentum',
    name: 'Momentum Filter',
    description: 'Filter by price momentum and RSI',
    defaultParams: { rsi_min: 50, rsi_max: 70, min_roc: 0, lookback_period: 14 },
    paramLabels: { rsi_min: 'RSI Min', rsi_max: 'RSI Max', min_roc: 'Min ROC %', lookback_period: 'Lookback Days' },
  },
  {
    type: 'breakout',
    name: 'Breakout Filter',
    description: 'Detect range breakouts',
    defaultParams: { consolidation_days: 20, breakout_threshold: 2, volume_surge: 1.5 },
    paramLabels: { consolidation_days: 'Consolidation Days', breakout_threshold: 'Breakout %', volume_surge: 'Volume Surge' },
  },
  {
    type: 'consolidation',
    name: 'Consolidation Filter',
    description: 'Find stocks in tight range',
    defaultParams: { max_range_pct: 10, min_days: 10, volume_decline: 0.8 },
    paramLabels: { max_range_pct: 'Max Range %', min_days: 'Min Days', volume_decline: 'Vol Decline Ratio' },
  },
  {
    type: 'moving_average',
    name: 'Moving Average Filter',
    description: 'Filter by MA position',
    defaultParams: { short_period: 20, long_period: 50, require_above_both: true },
    paramLabels: { short_period: 'Short MA', long_period: 'Long MA', require_above_both: 'Above Both MAs' },
  },
];

interface FilterBuilderProps {
  filters: FilterConfig[];
  onChange: (filters: FilterConfig[]) => void;
  disabled?: boolean;
}

export function FilterBuilder({ filters, onChange, disabled }: FilterBuilderProps) {
  const [selectedType, setSelectedType] = useState<FilterType | ''>('');

  const addFilter = () => {
    if (!selectedType) return;
    const def = FILTER_DEFINITIONS.find((d) => d.type === selectedType);
    if (!def) return;

    const newFilter: FilterConfig = {
      filter_type: selectedType,
      params: { ...def.defaultParams },
      weight: 1.0,
    };
    onChange([...filters, newFilter]);
    setSelectedType('');
  };

  const removeFilter = (index: number) => {
    onChange(filters.filter((_, i) => i !== index));
  };

  const updateFilterParam = (index: number, key: string, value: unknown) => {
    const updated = [...filters];
    updated[index] = {
      ...updated[index],
      params: { ...updated[index].params, [key]: value },
    };
    onChange(updated);
  };

  const updateFilterWeight = (index: number, weight: number) => {
    const updated = [...filters];
    updated[index] = { ...updated[index], weight };
    onChange(updated);
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Sliders className="h-5 w-5" />
          Filters
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Add Filter */}
        <div className="flex gap-2">
          <Select value={selectedType} onValueChange={(v) => setSelectedType(v as FilterType)} disabled={disabled}>
            <SelectTrigger className="flex-1">
              <SelectValue placeholder="Select filter type..." />
            </SelectTrigger>
            <SelectContent>
              {FILTER_DEFINITIONS.map((def) => (
                <SelectItem key={def.type} value={def.type}>
                  {def.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={addFilter} disabled={!selectedType || disabled} size="icon">
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        {/* Filter List */}
        {filters.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No filters added. Add filters to customize screening criteria.
          </p>
        ) : (
          <div className="space-y-3">
            {filters.map((filter, index) => {
              const def = FILTER_DEFINITIONS.find((d) => d.type === filter.filter_type);
              return (
                <div key={index} className="border rounded-lg p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm">{def?.name ?? filter.filter_type}</span>
                    <Button variant="ghost" size="sm" onClick={() => removeFilter(index)} disabled={disabled}>
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(filter.params).map(([key, value]) => (
                      <div key={key} className="space-y-1">
                        <Label className="text-xs">{def?.paramLabels[key] ?? key}</Label>
                        <Input
                          type={typeof value === 'boolean' ? 'checkbox' : 'number'}
                          value={typeof value === 'boolean' ? undefined : String(value)}
                          checked={typeof value === 'boolean' ? value as boolean : undefined}
                          onChange={(e) => updateFilterParam(index, key, typeof value === 'boolean' ? e.target.checked : Number(e.target.value))}
                          className="h-8"
                          disabled={disabled}
                        />
                      </div>
                    ))}
                    <div className="space-y-1">
                      <Label className="text-xs">Weight</Label>
                      <Input type="number" min={0.1} max={5} step={0.1} value={filter.weight} onChange={(e) => updateFilterWeight(index, Number(e.target.value))} className="h-8" disabled={disabled} />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

