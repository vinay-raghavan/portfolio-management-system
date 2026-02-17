'use client';

import { useQuery } from '@tanstack/react-query';
import { Info, RotateCcw } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Skeleton } from '@/components/ui/skeleton';
import { algoApi } from '@/lib/api';
import type { StrategyParameterSchema } from '@/types';

interface ComponentParameterFormProps {
  strategyType: string;
  params: Record<string, unknown>;
  onChange: (params: Record<string, unknown>) => void;
}

export function ComponentParameterForm({
  strategyType,
  params,
  onChange,
}: ComponentParameterFormProps) {
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
    onChange({});
  };

  if (!strategyType) return null;

  const customizedCount = Object.keys(params).length;

  return (
    <div className="pt-3 space-y-3">
      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-6 w-full" />
          <Skeleton className="h-6 w-full" />
        </div>
      ) : strategyDetail?.parameters && strategyDetail.parameters.length > 0 ? (
        <>
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Customize {strategyDetail.name} parameters
              {customizedCount > 0 && (
                <span className="ml-2 text-blue-600 dark:text-blue-400">
                  ({customizedCount} modified)
                </span>
              )}
            </p>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleResetToDefaults}
              className="h-6 text-xs px-2"
              type="button"
              disabled={customizedCount === 0}
            >
              <RotateCcw className="h-3 w-3 mr-1" />
              Reset
            </Button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {strategyDetail.parameters.map((param) => (
              <ParameterInput
                key={param.name}
                param={param}
                value={params[param.name] ?? param.default}
                isModified={param.name in params}
                onChange={(value) => handleParamChange(param.name, value)}
              />
            ))}
          </div>
        </>
      ) : (
        <p className="text-xs text-muted-foreground text-center py-1">
          This strategy uses default parameters.
        </p>
      )}
    </div>
  );
}

interface ParameterInputProps {
  param: StrategyParameterSchema;
  value: unknown;
  isModified: boolean;
  onChange: (value: unknown) => void;
}

function ParameterInput({ param, value, isModified, onChange }: ParameterInputProps) {
  const formatParamName = (name: string) =>
    name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1">
        <Label htmlFor={`param-${param.name}`} className={`text-xs ${isModified ? 'text-blue-600 dark:text-blue-400' : ''}`}>
          {formatParamName(param.name)}
        </Label>
        {param.description && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Info className="h-3 w-3 text-muted-foreground cursor-help" />
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-[200px]">
                <p className="text-xs">{param.description}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>

      {param.type === 'bool' ? (
        <div className="flex items-center gap-2">
          <Switch
            id={`param-${param.name}`}
            checked={Boolean(value)}
            onCheckedChange={onChange}
          />
          <span className="text-xs text-muted-foreground">
            {Boolean(value) ? 'On' : 'Off'}
          </span>
        </div>
      ) : param.type === 'select' && param.options ? (
        <Select value={String(value)} onValueChange={onChange}>
          <SelectTrigger className="h-7 text-xs">
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
        <Input
          id={`param-${param.name}`}
          type="number"
          value={String(value)}
          onChange={(e) => {
            const v = param.type === 'int' ? parseInt(e.target.value) : parseFloat(e.target.value);
            if (!isNaN(v)) onChange(v);
          }}
          className="h-7 text-xs"
          min={param.min_value ?? undefined}
          max={param.max_value ?? undefined}
          step={param.type === 'int' ? 1 : 0.1}
        />
      )}
    </div>
  );
}

export default ComponentParameterForm;

