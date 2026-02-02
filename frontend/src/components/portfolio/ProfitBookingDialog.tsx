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
import { portfolioApi } from '@/lib/api';
import { useToast } from '@/components/ui/use-toast';
import type { Position, ProfitBookingRules, ProfitBookingRule } from '@/types';

interface ProfitBookingDialogProps {
  position: Position | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ProfitBookingDialog({ position, open, onOpenChange }: ProfitBookingDialogProps) {
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
    queryKey: ['profit-booking-rules', position?.id],
    queryFn: () => portfolioApi.getProfitBookingRules(position!.id),
    enabled: !!position?.id && open,
  });

  useEffect(() => {
    if (existingRules?.data) {
      setEnabled(existingRules.data.enabled ?? true);
      const existingRulesList = existingRules.data.rules;
      if (Array.isArray(existingRulesList) && existingRulesList.length > 0) {
        // Ensure all values are proper numbers
        setRules(existingRulesList.map(rule => ({
          target_pct: Number(rule.target_pct) || 0,
          quantity_pct: Number(rule.quantity_pct) || 0,
        })));
      } else {
        setRules([
          { target_pct: 5, quantity_pct: 25 },
          { target_pct: 10, quantity_pct: 25 },
          { target_pct: 15, quantity_pct: 50 },
        ]);
      }
    }
  }, [existingRules]);

  const updateMutation = useMutation({
    mutationFn: async (data: ProfitBookingRules) => {
      console.log('=== Profit Booking Update Debug ===');
      console.log('Position object:', position);
      console.log('Position ID:', position?.id);
      console.log('Position symbol:', position?.symbol);
      console.log('Rules to save:', data);
      console.log('API URL will be:', `/portfolio/positions/${position!.id}/profit-booking`);

      const result = await portfolioApi.updateProfitBookingRules(position!.id, data);
      console.log('Update successful:', result);
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      queryClient.invalidateQueries({ queryKey: ['profit-booking-rules', position?.id] });
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

    // Validate rules
    const totalQtyPct = rules.reduce((sum, rule) => sum + Number(rule.quantity_pct || 0), 0);
    if (totalQtyPct > 100) {
      toast({
        title: 'Invalid rules',
        description: `Total quantity percentage cannot exceed 100%. Current total: ${totalQtyPct.toFixed(0)}%`,
        variant: 'destructive',
      });
      return;
    }

    console.log('About to call mutation with position:', position);
    console.log('Position ID before mutation:', position?.id);

    updateMutation.mutate({
      enabled,
      rules: rules.sort((a, b) => Number(a.target_pct) - Number(b.target_pct)),
      executed: existingRules?.data?.executed || [],
    });
  };

  if (!position) return null;

  const rawPnlPct = Number(position.unrealized_pnl_pct ?? 0);
  const currentPnlPct = Number.isFinite(rawPnlPct) ? rawPnlPct : 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            Profit Booking - {position.symbol}
          </DialogTitle>
          <DialogDescription>
            Set automatic profit booking rules. When profit reaches target %, sell specified quantity %.
            Current P&L: <span className={currentPnlPct >= 0 ? 'text-profit' : 'text-loss'}>
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
              <div className="flex items-center gap-2 px-1 mb-2">
                <div className="flex-1 grid grid-cols-2 gap-2">
                  <Label className="text-xs text-muted-foreground">Profit %</Label>
                  <Label className="text-xs text-muted-foreground">Quantity %</Label>
                </div>
                <div className="w-10" /> {/* Spacer for delete button */}
              </div>
              {rules.map((rule, index) => (
                <div key={index} className="flex items-center gap-2">
                  <div className="flex-1 grid grid-cols-2 gap-2">
                    <div>
                      <Input
                        type="number"
                        placeholder="Target %"
                        value={rule.target_pct || ''}
                        onChange={(e) => handleRuleChange(index, 'target_pct', e.target.value)}
                        min="0"
                        step="0.1"
                      />
                    </div>
                    <div>
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
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => handleRemoveRule(index)}
                  >
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

