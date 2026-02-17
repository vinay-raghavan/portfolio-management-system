'use client';

import { useState, useCallback } from 'react';
import {
  DndContext,
  DragEndEvent,
  DragStartEvent,
  DragOverlay,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  GripVertical,
  Plus,
  Trash2,
  TrendingUp,
  TrendingDown,
  Activity,
  BarChart3,
  X,
} from 'lucide-react';
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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

// Types for visual rule builder
export interface ConditionBlock {
  id: string;
  type: 'indicator' | 'price' | 'operator' | 'value';
  value: string;
  params?: Record<string, string>;
}

export interface EntryRule {
  id: string;
  conditions: ConditionBlock[];
  action: 'BUY' | 'SELL';
  confidence: number;
  strength: number;
}

export interface ExitConfig {
  stopLossPct: number;
  takeProfitPct: number;
  trailingStopPct?: number;
}

export interface VisualRuleBuilderProps {
  entryRules: EntryRule[];
  exitConfig: ExitConfig;
  filters: string[];
  onEntryRulesChange: (rules: EntryRule[]) => void;
  onExitConfigChange: (config: ExitConfig) => void;
  onFiltersChange: (filters: string[]) => void;
}

// Available indicators and their configs
const INDICATORS = [
  { id: 'rsi', label: 'RSI', icon: Activity, params: ['period'], defaults: { period: '14' } },
  { id: 'sma', label: 'SMA', icon: TrendingUp, params: ['period'], defaults: { period: '20' } },
  { id: 'ema', label: 'EMA', icon: TrendingUp, params: ['period'], defaults: { period: '12' } },
  { id: 'macd', label: 'MACD', icon: BarChart3, params: [], defaults: {} },
  { id: 'macd_signal', label: 'MACD Signal', icon: BarChart3, params: [], defaults: {} },
  { id: 'macd_histogram', label: 'MACD Hist', icon: BarChart3, params: [], defaults: {} },
  { id: 'bbands_upper', label: 'BB Upper', icon: TrendingUp, params: ['period', 'std'], defaults: { period: '20', std: '2' } },
  { id: 'bbands_lower', label: 'BB Lower', icon: TrendingDown, params: ['period', 'std'], defaults: { period: '20', std: '2' } },
  { id: 'atr', label: 'ATR', icon: Activity, params: ['period'], defaults: { period: '14' } },
  { id: 'volume_sma', label: 'Vol SMA', icon: BarChart3, params: ['period'], defaults: { period: '20' } },
];

const PRICE_VARIABLES = [
  { id: 'close', label: 'Close' },
  { id: 'open', label: 'Open' },
  { id: 'high', label: 'High' },
  { id: 'low', label: 'Low' },
  { id: 'volume', label: 'Volume' },
  { id: 'previous_close', label: 'Prev Close' },
];

const COMPARISON_OPERATORS = [
  { id: '>', label: '>' },
  { id: '<', label: '<' },
  { id: '>=', label: '>=' },
  { id: '<=', label: '<=' },
  { id: '==', label: '==' },
  { id: '!=', label: '!=' },
];

const LOGICAL_OPERATORS = [
  { id: 'AND', label: 'AND' },
  { id: 'OR', label: 'OR' },
];

// Generate unique ID
const generateId = () => `block-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

// Sortable condition block component
interface SortableConditionBlockProps {
  block: ConditionBlock;
  onRemove: () => void;
  onUpdate: (block: ConditionBlock) => void;
}

// Get display label for a block
function getBlockLabel(block: ConditionBlock): string {
  if (block.type === 'indicator') {
    const indicator = INDICATORS.find((i) => i.id === block.value);
    return indicator?.label || block.value;
  }
  if (block.type === 'price') {
    const price = PRICE_VARIABLES.find((p) => p.id === block.value);
    return price?.label || block.value;
  }
  return block.value;
}

function SortableConditionBlock({ block, onRemove }: SortableConditionBlockProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: block.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const indicator = INDICATORS.find((i) => i.id === block.value);
  const Icon = indicator?.icon || Activity;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'flex items-center gap-1 px-2 py-1 rounded-md border text-sm',
        isDragging && 'opacity-50',
        block.type === 'indicator' && 'bg-blue-50 border-blue-200 dark:bg-blue-950 dark:border-blue-800',
        block.type === 'price' && 'bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800',
        block.type === 'operator' && 'bg-purple-50 border-purple-200 dark:bg-purple-950 dark:border-purple-800',
        block.type === 'value' && 'bg-orange-50 border-orange-200 dark:bg-orange-950 dark:border-orange-800'
      )}
    >
      <button {...attributes} {...listeners} className="cursor-grab hover:bg-muted rounded p-0.5">
        <GripVertical className="h-3 w-3 text-muted-foreground" />
      </button>
      {block.type === 'indicator' && <Icon className="h-3 w-3" />}
      <span className="font-medium">{getBlockLabel(block)}</span>
      {block.params && Object.keys(block.params).length > 0 && (
        <span className="text-xs text-muted-foreground">
          ({Object.values(block.params).join(', ')})
        </span>
      )}
      <button onClick={onRemove} className="ml-1 hover:bg-muted rounded p-0.5">
        <X className="h-3 w-3 text-muted-foreground" />
      </button>
    </div>
  );
}

// Convert visual rules to DSL condition string
export function rulesToConditionString(conditions: ConditionBlock[]): string {
  return conditions
    .map((block) => {
      if (block.type === 'indicator') {
        const params = block.params ? Object.values(block.params).join(', ') : '';
        return params ? `${block.value}(${params})` : block.value;
      }
      return block.value;
    })
    .join(' ');
}

// Convert DSL condition string to visual blocks (simplified parser)
export function conditionStringToBlocks(condition: string): ConditionBlock[] {
  const blocks: ConditionBlock[] = [];
  const tokens = condition.match(/([a-z_]+\([^)]*\))|([a-z_]+)|([<>=!]+)|(\d+\.?\d*)|(\bAND\b|\bOR\b)/gi) || [];

  for (const token of tokens) {
    const funcMatch = token.match(/^([a-z_]+)\(([^)]*)\)$/i);
    if (funcMatch) {
      const indicator = INDICATORS.find((i) => i.id === funcMatch[1]);
      if (indicator) {
        const paramValues = funcMatch[2].split(',').map((p) => p.trim());
        const params: Record<string, string> = {};
        const defaults = indicator.defaults as Record<string, string>;
        indicator.params.forEach((param, idx) => {
          params[param] = paramValues[idx] || defaults[param] || '';
        });
        blocks.push({ id: generateId(), type: 'indicator', value: funcMatch[1], params });
        continue;
      }
    }

    if (INDICATORS.find((i) => i.id === token.toLowerCase())) {
      blocks.push({ id: generateId(), type: 'indicator', value: token.toLowerCase(), params: {} });
    } else if (PRICE_VARIABLES.find((p) => p.id === token.toLowerCase())) {
      blocks.push({ id: generateId(), type: 'price', value: token.toLowerCase() });
    } else if (COMPARISON_OPERATORS.find((o) => o.id === token) || LOGICAL_OPERATORS.find((o) => o.id === token.toUpperCase())) {
      blocks.push({ id: generateId(), type: 'operator', value: token.toUpperCase() === 'AND' || token.toUpperCase() === 'OR' ? token.toUpperCase() : token });
    } else if (/^\d+\.?\d*$/.test(token)) {
      blocks.push({ id: generateId(), type: 'value', value: token });
    }
  }

  return blocks;
}

// Entry Rule Editor Component
interface EntryRuleEditorProps {
  rule: EntryRule;
  onUpdate: (rule: EntryRule) => void;
  onRemove: () => void;
  ruleIndex: number;
}

function EntryRuleEditor({ rule, onUpdate, onRemove, ruleIndex }: EntryRuleEditorProps) {
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (over && active.id !== over.id) {
      const oldIndex = rule.conditions.findIndex((c) => c.id === active.id);
      const newIndex = rule.conditions.findIndex((c) => c.id === over.id);
      onUpdate({ ...rule, conditions: arrayMove(rule.conditions, oldIndex, newIndex) });
    }
  };

  const addBlock = (type: ConditionBlock['type'], value: string, params?: Record<string, string>) => {
    const newBlock: ConditionBlock = { id: generateId(), type, value, params };
    onUpdate({ ...rule, conditions: [...rule.conditions, newBlock] });
  };

  const removeBlock = (blockId: string) => {
    onUpdate({ ...rule, conditions: rule.conditions.filter((c) => c.id !== blockId) });
  };

  const updateBlock = (block: ConditionBlock) => {
    onUpdate({ ...rule, conditions: rule.conditions.map((c) => (c.id === block.id ? block : c)) });
  };

  const activeBlock = activeId ? rule.conditions.find((c) => c.id === activeId) : null;

  return (
    <Card className="border-l-4 border-l-primary">
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <CardTitle className="text-sm flex items-center gap-2">
          <Badge variant={rule.action === 'BUY' ? 'default' : 'destructive'}>{rule.action}</Badge>
          Rule {ruleIndex + 1}
        </CardTitle>
        <Button variant="ghost" size="icon" onClick={onRemove} className="h-6 w-6">
          <Trash2 className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Condition blocks */}
        <div className="space-y-2">
          <Label className="text-xs">Condition (drag to reorder)</Label>
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <SortableContext items={rule.conditions.map((c) => c.id)} strategy={verticalListSortingStrategy}>
              <div className="flex flex-wrap gap-1 min-h-[36px] p-2 border rounded-md bg-muted/30">
                {rule.conditions.length === 0 && (
                  <span className="text-xs text-muted-foreground">Add blocks below...</span>
                )}
                {rule.conditions.map((block) => (
                  <SortableConditionBlock
                    key={block.id}
                    block={block}
                    onRemove={() => removeBlock(block.id)}
                    onUpdate={updateBlock}
                  />
                ))}
              </div>
            </SortableContext>
            <DragOverlay>
              {activeBlock && (
                <div className="flex items-center gap-1 px-2 py-1 rounded-md border bg-background shadow-lg text-sm">
                  <GripVertical className="h-3 w-3" />
                  <span>{getBlockLabel(activeBlock)}</span>
                </div>
              )}
            </DragOverlay>
          </DndContext>
        </div>

        {/* Block palette */}
        <div className="space-y-2">
          <Label className="text-xs">Add Blocks</Label>
          <div className="flex flex-wrap gap-1">
            {/* Indicators dropdown */}
            <Select onValueChange={(v) => {
              const ind = INDICATORS.find((i) => i.id === v);
              addBlock('indicator', v, ind?.defaults as Record<string, string> | undefined);
            }}>
              <SelectTrigger className="h-7 w-28 text-xs">
                <SelectValue placeholder="Indicator" />
              </SelectTrigger>
              <SelectContent>
                {INDICATORS.map((ind) => (
                  <SelectItem key={ind.id} value={ind.id} className="text-xs">{ind.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {/* Price variables */}
            <Select onValueChange={(v) => addBlock('price', v)}>
              <SelectTrigger className="h-7 w-24 text-xs">
                <SelectValue placeholder="Price" />
              </SelectTrigger>
              <SelectContent>
                {PRICE_VARIABLES.map((p) => (
                  <SelectItem key={p.id} value={p.id} className="text-xs">{p.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {/* Comparison operators */}
            {COMPARISON_OPERATORS.map((op) => (
              <Button key={op.id} variant="outline" size="sm" className="h-7 px-2 text-xs" onClick={() => addBlock('operator', op.id)}>
                {op.label}
              </Button>
            ))}
            {/* Logical operators */}
            {LOGICAL_OPERATORS.map((op) => (
              <Button key={op.id} variant="secondary" size="sm" className="h-7 px-2 text-xs" onClick={() => addBlock('operator', op.id)}>
                {op.label}
              </Button>
            ))}
            {/* Value input */}
            <Input
              type="number"
              placeholder="Value"
              className="h-7 w-20 text-xs"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const target = e.target as HTMLInputElement;
                  if (target.value) {
                    addBlock('value', target.value);
                    target.value = '';
                  }
                }
              }}
            />
          </div>
        </div>

        {/* Action and confidence */}
        <div className="grid grid-cols-3 gap-2">
          <div>
            <Label className="text-xs">Action</Label>
            <Select value={rule.action} onValueChange={(v) => onUpdate({ ...rule, action: v as 'BUY' | 'SELL' })}>
              <SelectTrigger className="h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="BUY">BUY</SelectItem>
                <SelectItem value="SELL">SELL</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">Confidence</Label>
            <Input
              type="number"
              min="0"
              max="1"
              step="0.1"
              value={rule.confidence}
              onChange={(e) => onUpdate({ ...rule, confidence: parseFloat(e.target.value) || 0.5 })}
              className="h-8 text-xs"
            />
          </div>
          <div>
            <Label className="text-xs">Strength</Label>
            <Input
              type="number"
              min="0"
              max="1"
              step="0.1"
              value={rule.strength}
              onChange={(e) => onUpdate({ ...rule, strength: parseFloat(e.target.value) || 0.5 })}
              className="h-8 text-xs"
            />
          </div>
        </div>

        {/* Preview */}
        <div className="text-xs text-muted-foreground bg-muted/50 p-2 rounded font-mono">
          {rulesToConditionString(rule.conditions) || 'No condition defined'}
        </div>
      </CardContent>
    </Card>
  );
}

// Main VisualRuleBuilder Component
export function VisualRuleBuilder({
  entryRules,
  exitConfig,
  filters,
  onEntryRulesChange,
  onExitConfigChange,
  onFiltersChange,
}: VisualRuleBuilderProps) {
  const [newFilter, setNewFilter] = useState('');

  const addEntryRule = () => {
    const newRule: EntryRule = {
      id: generateId(),
      conditions: [],
      action: 'BUY',
      confidence: 0.5,
      strength: 0.5,
    };
    onEntryRulesChange([...entryRules, newRule]);
  };

  const updateEntryRule = (index: number, rule: EntryRule) => {
    const newRules = [...entryRules];
    newRules[index] = rule;
    onEntryRulesChange(newRules);
  };

  const removeEntryRule = (index: number) => {
    onEntryRulesChange(entryRules.filter((_, i) => i !== index));
  };

  const addFilter = () => {
    if (newFilter.trim()) {
      onFiltersChange([...filters, newFilter.trim()]);
      setNewFilter('');
    }
  };

  const removeFilter = (index: number) => {
    onFiltersChange(filters.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-4">
      {/* Entry Rules Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label className="text-sm font-medium">Entry Rules</Label>
          <Button variant="outline" size="sm" onClick={addEntryRule} className="h-7 text-xs">
            <Plus className="h-3 w-3 mr-1" /> Add Rule
          </Button>
        </div>
        {entryRules.length === 0 && (
          <p className="text-xs text-muted-foreground text-center py-4 border rounded-md bg-muted/30">
            No entry rules defined. Click &quot;Add Rule&quot; to create one.
          </p>
        )}
        {entryRules.map((rule, index) => (
          <EntryRuleEditor
            key={rule.id}
            rule={rule}
            ruleIndex={index}
            onUpdate={(r) => updateEntryRule(index, r)}
            onRemove={() => removeEntryRule(index)}
          />
        ))}
      </div>

      {/* Exit Configuration */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Exit Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <Label className="text-xs">Stop Loss %</Label>
              <Input
                type="number"
                min="0.1"
                max="20"
                step="0.1"
                value={exitConfig.stopLossPct}
                onChange={(e) => onExitConfigChange({ ...exitConfig, stopLossPct: parseFloat(e.target.value) || 2 })}
                className="h-8 text-xs"
              />
            </div>
            <div>
              <Label className="text-xs">Take Profit %</Label>
              <Input
                type="number"
                min="0.1"
                max="50"
                step="0.1"
                value={exitConfig.takeProfitPct}
                onChange={(e) => onExitConfigChange({ ...exitConfig, takeProfitPct: parseFloat(e.target.value) || 4 })}
                className="h-8 text-xs"
              />
            </div>
            <div>
              <Label className="text-xs">Trailing Stop %</Label>
              <Input
                type="number"
                min="0"
                max="20"
                step="0.1"
                value={exitConfig.trailingStopPct || ''}
                placeholder="Optional"
                onChange={(e) => onExitConfigChange({
                  ...exitConfig,
                  trailingStopPct: e.target.value ? parseFloat(e.target.value) : undefined
                })}
                className="h-8 text-xs"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Filters Section */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Filters (all must pass)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex gap-2">
            <Input
              placeholder="e.g., close > sma(200)"
              value={newFilter}
              onChange={(e) => setNewFilter(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addFilter()}
              className="h-8 text-xs flex-1"
            />
            <Button variant="outline" size="sm" onClick={addFilter} className="h-8">
              <Plus className="h-3 w-3" />
            </Button>
          </div>
          <div className="flex flex-wrap gap-1">
            {filters.map((filter, index) => (
              <Badge key={index} variant="secondary" className="text-xs">
                {filter}
                <button onClick={() => removeFilter(index)} className="ml-1 hover:text-destructive">
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
