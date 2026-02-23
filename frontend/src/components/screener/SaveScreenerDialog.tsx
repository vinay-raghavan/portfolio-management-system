'use client';

import { useState, useEffect } from 'react';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { Save, Bot, Clock, FileCode2 } from 'lucide-react';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/components/ui/use-toast';
import { screenerApi, autoTradeApi, type FilterConfig, type RunFrequency } from '@/lib/api';
import { cn } from '@/lib/utils';

interface SaveScreenerDialogProps {
  filters: FilterConfig[];
  universe: string;
  preset?: string | null;
  onSaved?: () => void;
  trigger?: React.ReactNode;
}

const RUN_FREQUENCIES: { value: RunFrequency; label: string }[] = [
  { value: 'daily', label: 'Daily' },
  { value: 'hourly', label: 'Hourly' },
  { value: 'manual', label: 'Manual' },
];

export function SaveScreenerDialog({
  filters,
  universe,
  preset,
  onSaved,
  trigger,
}: SaveScreenerDialogProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isAutoTradeEnabled, setIsAutoTradeEnabled] = useState(false);
  const [runFrequency, setRunFrequency] = useState<RunFrequency>('daily');
  const [runTime, setRunTime] = useState('09:20');
  const [templateId, setTemplateId] = useState<string>('');
  const [inferredStrategy, setInferredStrategy] = useState<string | null>(null);

  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch templates for selection
  const { data: templatesData } = useQuery({
    queryKey: ['strategy-templates'],
    queryFn: () => autoTradeApi.getTemplates().then(r => r.data),
    enabled: isAutoTradeEnabled,
  });

  // Infer strategy when auto-trade is enabled
  useEffect(() => {
    if (isAutoTradeEnabled && (filters.length > 0 || preset)) {
      screenerApi.inferStrategy({ filters: filters.length > 0 ? filters : undefined, preset: preset || undefined })
        .then(res => setInferredStrategy(res.data.recommended_strategy?.strategy_type || null))
        .catch(() => setInferredStrategy(null));
    }
  }, [isAutoTradeEnabled, filters, preset]);

  const createMutation = useMutation({
    mutationFn: () => screenerApi.createCustomScreener({
      name,
      description: description || undefined,
      universe,
      filters,
      is_auto_trade_enabled: isAutoTradeEnabled,
      run_frequency: isAutoTradeEnabled ? runFrequency : 'manual',
      run_time: isAutoTradeEnabled && runFrequency === 'daily' ? runTime : undefined,
      strategy_template_id: isAutoTradeEnabled && templateId ? templateId : undefined,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customScreeners'] });
      setOpen(false);
      resetForm();
      toast({
        title: 'Screener Saved',
        description: isAutoTradeEnabled 
          ? `"${name}" saved with auto-trade ${runFrequency === 'manual' ? 'enabled' : `scheduled ${runFrequency}`}`
          : `"${name}" has been saved`,
      });
      onSaved?.();
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to save screener',
        variant: 'destructive',
      });
    },
  });

  const resetForm = () => {
    setName('');
    setDescription('');
    setIsAutoTradeEnabled(false);
    setRunFrequency('daily');
    setRunTime('09:20');
    setTemplateId('');
    setInferredStrategy(null);
  };

  const templates = templatesData?.templates || [];
  const canSave = name.trim() && filters.length > 0;

  return (
    <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (!o) resetForm(); }}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" size="sm" disabled={filters.length === 0}>
            <Save className="h-4 w-4 mr-2" /> Save Screener
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Save className="h-5 w-5" /> Save Screener
          </DialogTitle>
          <DialogDescription>
            Save your filter configuration for quick access and optional auto-trading
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="name">Name *</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="My Screener" />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea id="description" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional description..." rows={2} />
          </div>

          <div className="text-sm text-muted-foreground">
            <span className="font-medium">{filters.length}</span> filters • Universe: <span className="font-medium">{universe}</span>
          </div>

          {/* Auto-Trade Section */}
          <div className="border rounded-lg p-4 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bot className="h-4 w-4 text-primary" />
                <Label htmlFor="auto-trade" className="font-medium">Enable Auto-Trade</Label>
              </div>
              <Switch id="auto-trade" checked={isAutoTradeEnabled} onCheckedChange={setIsAutoTradeEnabled} />
            </div>

            {isAutoTradeEnabled && (
              <div className="space-y-4 pt-2">
                {inferredStrategy && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">Inferred Strategy:</span>
                    <Badge variant="secondary">{inferredStrategy}</Badge>
                  </div>
                )}

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="run-frequency" className="text-sm">Run Frequency</Label>
                    <Select value={runFrequency} onValueChange={(v) => setRunFrequency(v as RunFrequency)}>
                      <SelectTrigger id="run-frequency">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {RUN_FREQUENCIES.map(f => (
                          <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {runFrequency === 'daily' && (
                    <div className="space-y-2">
                      <Label htmlFor="run-time" className="text-sm flex items-center gap-1">
                        <Clock className="h-3 w-3" /> Run Time
                      </Label>
                      <Input
                        id="run-time"
                        type="time"
                        value={runTime}
                        onChange={(e) => setRunTime(e.target.value)}
                      />
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="template" className="text-sm flex items-center gap-1">
                    <FileCode2 className="h-3 w-3" /> Strategy Template (optional)
                  </Label>
                  <Select value={templateId} onValueChange={setTemplateId}>
                    <SelectTrigger id="template">
                      <SelectValue placeholder="Use inferred params" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Use inferred params</SelectItem>
                      {templates.map(t => (
                        <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <p className="text-xs text-muted-foreground">
                  Trades will be created based on your confirmation mode in auto-trade settings.
                </p>
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={() => createMutation.mutate()} disabled={!canSave || createMutation.isPending}>
            {createMutation.isPending ? 'Saving...' : 'Save Screener'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
