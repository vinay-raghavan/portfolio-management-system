'use client';

import { useQuery } from '@tanstack/react-query';
import { Settings2, Info, RotateCcw } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Skeleton } from '@/components/ui/skeleton';
import { algoApi } from '@/lib/api';
import type { StrategyParameterSchema } from '@/types';

interface StrategyParameterFormProps {
  strategyType: string;
  params: Record<string, unknown>;
  onChange: (params: Record<string, unknown>) => void;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

export function StrategyParameterForm({
  strategyType,
  params,
  onChange,
  isOpen,
  onOpenChange,
}: StrategyParameterFormProps) {
  // Fetch parameter schema for the selected strategy
  const { data: strategyDetail, isLoading } = useQuery({
    queryKey: ['strategy-type-detail', strategyType],
    queryFn: () => algoApi.getStrategyTypeDetail(strategyType).then((res) => res.data),
    enabled: !!strategyType,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  const handleParamChange = (name: string, value: unknown) => {
    onChange({ ...params, [name]: value });
  };

  const handleResetToDefaults = () => {
    if (!strategyDetail?.parameters) return;
    const defaults: Record<string, unknown> = {};
    strategyDetail.parameters.forEach((p) => {
      defaults[p.name] = p.default;
    });
    onChange(defaults);
  };

  // Initialize params with defaults when strategy changes
  const hasUninitializedParams =
    strategyDetail?.parameters &&
    strategyDetail.parameters.length > 0 &&
    Object.keys(params).length === 0;

  if (hasUninitializedParams) {
    const defaults: Record<string, unknown> = {};
    strategyDetail.parameters.forEach((p) => {
      defaults[p.name] = p.default;
    });
    onChange(defaults);
  }

  if (!strategyType) return null;

  const paramCount = strategyDetail?.parameters?.length || 0;
  const customizedCount = Object.keys(params).filter((key) => {
    const param = strategyDetail?.parameters?.find((p) => p.name === key);
    return param && params[key] !== param.default;
  }).length;

  return (
    <Collapsible open={isOpen} onOpenChange={onOpenChange} className="mt-4">
      <CollapsibleTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-between text-left font-normal"
          type="button"
        >
          <div className="flex items-center gap-2">
            <Settings2 className="h-4 w-4" />
            <span>Customize Strategy Parameters</span>
            {customizedCount > 0 && (
              <span className="text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 px-1.5 py-0.5 rounded">
                {customizedCount} modified
              </span>
            )}
          </div>
          <span className="text-xs text-muted-foreground">
            {paramCount} parameters
          </span>
        </Button>
      </CollapsibleTrigger>

      <CollapsibleContent className="mt-3 space-y-4 border rounded-lg p-4 bg-muted/30">
        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-3/4" />
          </div>
        ) : strategyDetail?.parameters && strategyDetail.parameters.length > 0 ? (
          <>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-muted-foreground">
                Fine-tune {strategyDetail.name} parameters
              </p>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleResetToDefaults}
                className="h-7 text-xs"
                type="button"
              >
                <RotateCcw className="h-3 w-3 mr-1" />
                Reset to defaults
              </Button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {strategyDetail.parameters.map((param) => (
                <ParameterInput
                  key={param.name}
                  param={param}
                  value={params[param.name] ?? param.default}
                  onChange={(value) => handleParamChange(param.name, value)}
                />
              ))}
            </div>
          </>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-2">
            This strategy uses default parameters and cannot be customized.
          </p>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}

interface ParameterInputProps {
  param: StrategyParameterSchema;
  value: unknown;
  onChange: (value: unknown) => void;
}

function ParameterInput({ param, value, onChange }: ParameterInputProps) {
  const formatParamName = (name: string) =>
    name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1">
        <Label htmlFor={param.name} className="text-xs font-medium">
          {formatParamName(param.name)}
        </Label>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Info className="h-3 w-3 text-muted-foreground cursor-help" />
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-[350px]">
              <p className="text-xs whitespace-pre-wrap">
                {param.description || 'No description available'}
              </p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      {param.type === 'bool' ? (
        <div className="flex items-center gap-2">
          <Switch
            id={param.name}
            checked={Boolean(value)}
            onCheckedChange={onChange}
          />
          <span className="text-xs text-muted-foreground">
            {Boolean(value) ? 'Enabled' : 'Disabled'}
          </span>
        </div>
      ) : param.type === 'select' && param.options ? (
        <Select value={String(value)} onValueChange={onChange}>
          <SelectTrigger className="h-8 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {param.options.map((opt) => (
              <SelectItem key={opt} value={opt} className="text-xs">
                {opt}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ) : (
        <div className="space-y-1">
          <Input
            id={param.name}
            type="number"
            value={String(value)}
            onChange={(e) => {
              const v = param.type === 'int' ? parseInt(e.target.value) : parseFloat(e.target.value);
              if (!isNaN(v)) onChange(v);
            }}
            className="h-8 text-xs"
            min={param.min_value ?? undefined}
            max={param.max_value ?? undefined}
            step={param.type === 'int' ? 1 : 0.1}
          />
          {(param.min_value !== null || param.max_value !== null) && (
            <div className="flex justify-between text-[10px] text-muted-foreground">
              <span>{param.min_value !== null ? `Min: ${param.min_value}` : ''}</span>
              <span>Default: {param.default}</span>
              <span>{param.max_value !== null ? `Max: ${param.max_value}` : ''}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default StrategyParameterForm;

