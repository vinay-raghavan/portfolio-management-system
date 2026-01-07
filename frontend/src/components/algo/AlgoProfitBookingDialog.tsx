'use client';

import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Target, Plus, Trash2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { algoApi } from '@/lib/api';
import { useToast } from '@/components/ui/use-toast';
import type { UnrealizedPnLPosition, ProfitBookingRules, ProfitBookingRule } from '@/types';

interface AlgoProfitBookingDialogProps {
  position: UnrealizedPnLPosition | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AlgoProfitBookingDialog({ position, open, onOpenChange }: AlgoProfitBookingDialogProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [enabled, setEnabled] = useState(true);
  const [rules, setRules] = useState<ProfitBookingRule[]>([
    { target_pct: 5, quantity_pct: 25 },
    { target_pct: 10, quantity_pct: 25 },
    { target_pct: 15, quantity_pct: 50 },
  ]);

  // Fetch existing rules
  const { data: existingRules } = useQuery({
    queryKey: ['algo-profit-booking-rules', position?.position_id],
    queryFn: () => algoApi.getAlgoProfitBookingRules(position!.position_id),
    enabled: !!position?.position_id && open,
  });

  useEffect(() => {
    if (existingRules) {
      setEnabled(existingRules.enabled);
      setRules(existingRules.rules.length > 0 ? existingRules.rules : [
        { target_pct: 5, quantity_pct: 25 },
        { target_pct: 10, quantity_pct: 25 },
        { target_pct: 15, quantity_pct: 50 },
      ]);
    }
  }, [existingRules]);

  const updateMutation = useMutation({
    mutationFn: (data: ProfitBookingRules) =>
      algoApi.updateAlgoProfitBookingRules(position!.position_id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['algo-unrealized-pnl'] });
      queryClient.invalidateQueries({ queryKey: ['algo-profit-booking-rules', position?.position_id] });
      toast({
        title: 'Profit booking updated',
        description: 'Your profit booking rules have been saved.',
      });
      onOpenChange(false);
    },
    onError: (error: any) => {
      console.error('Profit booking update error:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to update profit booking rules.';
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    },
  });

  const handleAddRule = () => {
    setRules([...rules, { target_pct: 0, quantity_pct: 0 }]);
  };

  const handleRemoveRule = (index: number) => {
    setRules(rules.filter((_, i) => i !== index));
  };

  const handleRuleChange = (index: number, field: 'target_pct' | 'quantity_pct', value: string) => {
    const newRules = [...rules];
    newRules[index] = { ...newRules[index], [field]: parseFloat(value) || 0 };
    setRules(newRules);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const totalQtyPct = rules.reduce((sum, rule) => sum + Number(rule.quantity_pct || 0), 0);
    if (totalQtyPct > 100) {
      toast({
        title: 'Invalid rules',
        description: `Total quantity percentage cannot exceed 100%. Current total: ${totalQtyPct.toFixed(0)}%`,
        variant: 'destructive',
      });
      return;
    }

    updateMutation.mutate({
      enabled,
      rules: rules.sort((a, b) => Number(a.target_pct) - Number(b.target_pct)),
      executed: existingRules?.executed || [],
    });
  };

  if (!position) return null;

  const currentPnlPct = Number(position.unrealized_pnl_percent ?? 0);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            Profit Booking - {position.symbol} ({position.side})
          </DialogTitle>
          <DialogDescription>
            Set automatic profit booking rules for this algo position. Current P&L: <span className={currentPnlPct >= 0 ? 'text-profit' : 'text-loss'}>
              {currentPnlPct.toFixed(2)}%
            </span>
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex items-center justify-between">
            <Label htmlFor="enabled">Enable Profit Booking</Label>
            <Switch id="enabled" checked={enabled} onCheckedChange={setEnabled} />
          </div>

          {enabled && (
            <div className="space-y-3">
              <Label>Profit Booking Rules</Label>
              <div className="flex items-center gap-2 px-1">
                <div className="flex-1 grid grid-cols-2 gap-2">
                  <Label className="text-xs text-muted-foreground">Profit %</Label>
                  <Label className="text-xs text-muted-foreground">Quantity %</Label>
                </div>
                <div className="w-10" /> {/* Spacer for delete button */}
              </div>
              {rules.map((rule, index) => (
                <div key={index} className="flex items-center gap-2">
                  <div className="flex-1 grid grid-cols-2 gap-2">
                    <Input
                      type="number"
                      placeholder="Target %"
                      value={rule.target_pct || ''}
                      onChange={(e) => handleRuleChange(index, 'target_pct', e.target.value)}
                      min="0"
                      step="0.1"
                    />
                    <Input
                      type="number"
                      placeholder="Sell Qty %"
                      value={rule.quantity_pct || ''}
                      onChange={(e) => handleRuleChange(index, 'quantity_pct', e.target.value)}
                      min="0"
                      max="100"
                      step="1"
                    />
                  </div>
                  <Button type="button" variant="ghost" size="icon" onClick={() => handleRemoveRule(index)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              <Button type="button" variant="outline" size="sm" onClick={handleAddRule}>
                <Plus className="h-4 w-4 mr-2" />
                Add Rule
              </Button>
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={updateMutation.isPending}>
              {updateMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Save Rules
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

