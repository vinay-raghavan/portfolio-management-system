'use client';

import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { TrendingUp, Loader2 } from 'lucide-react';
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
import { useCurrency } from '@/hooks/useCurrency';
import type { Position, TrailingStopUpdate } from '@/types';

interface TrailingStopDialogProps {
  position: Position | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function TrailingStopDialog({ position, open, onOpenChange }: TrailingStopDialogProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { format: formatValue } = useCurrency();
  const [enabled, setEnabled] = useState(false);
  const [percentage, setPercentage] = useState<string>('5');

  // Fetch existing trailing stop config
  const { data: existingConfig } = useQuery({
    queryKey: ['trailing-stop-config', position?.id],
    queryFn: () => portfolioApi.getTrailingStopConfig(position!.id),
    enabled: !!position?.id && open,
  });

  useEffect(() => {
    if (existingConfig?.data) {
      setEnabled(existingConfig.data.enabled ?? false);
      if (existingConfig.data.percentage != null) {
        // Convert from decimal (0.05) to percentage (5)
        setPercentage((existingConfig.data.percentage * 100).toString());
      } else {
        setPercentage('5');
      }
    }
  }, [existingConfig]);

  const updateMutation = useMutation({
    mutationFn: async (data: TrailingStopUpdate) => {
      return await portfolioApi.updateTrailingStop(position!.id, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      queryClient.invalidateQueries({ queryKey: ['trailing-stop-config', position?.id] });
      toast({
        title: 'Trailing stop updated',
        description: enabled
          ? `Trailing stop enabled at ${percentage}% distance.`
          : 'Trailing stop disabled.',
      });
      onOpenChange(false);
    },
    onError: (error: any) => {
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to update trailing stop.';
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const pctValue = parseFloat(percentage);
    if (enabled && (isNaN(pctValue) || pctValue <= 0 || pctValue > 50)) {
      toast({
        title: 'Invalid percentage',
        description: 'Trailing stop percentage must be between 0.1% and 50%.',
        variant: 'destructive',
      });
      return;
    }

    updateMutation.mutate({
      enabled,
      // Convert from percentage (5) to decimal (0.05)
      percentage: enabled ? pctValue / 100 : null,
    });
  };

  if (!position) return null;

  const currentPrice = position.current_price ?? position.avg_cost;
  const previewStopPrice = enabled
    ? currentPrice * (1 - parseFloat(percentage || '0') / 100)
    : null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Trailing Stop - {position.symbol}
          </DialogTitle>
          <DialogDescription>
            A trailing stop automatically adjusts upward as the price rises,
            locking in profits while protecting against reversals.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex items-center justify-between">
            <Label htmlFor="enabled">Enable Trailing Stop</Label>
            <Switch id="enabled" checked={enabled} onCheckedChange={setEnabled} />
          </div>

          {enabled && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="percentage">Trail Distance (%)</Label>
                <Input
                  id="percentage"
                  type="number"
                  placeholder="5"
                  value={percentage}
                  onChange={(e) => setPercentage(e.target.value)}
                  min="0.1"
                  max="50"
                  step="0.1"
                />
                <p className="text-xs text-muted-foreground">
                  Stop will trail {percentage}% below the highest price reached.
                </p>
              </div>

              {previewStopPrice && (
                <div className="rounded-lg border p-3 space-y-2 bg-muted/50">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Current Price:</span>
                    <span>{formatValue(currentPrice)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Initial Stop Price:</span>
                    <span className="text-loss font-medium">{formatValue(previewStopPrice)}</span>
                  </div>
                  {existingConfig?.data?.current_stop_price && (
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Active Stop Price:</span>
                      <span className="text-loss font-medium">
                        {formatValue(existingConfig.data.current_stop_price)}
                      </span>
                    </div>
                  )}
                  {existingConfig?.data?.highest_price && (
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Highest Since Entry:</span>
                      <span className="text-profit font-medium">
                        {formatValue(existingConfig.data.highest_price)}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={updateMutation.isPending}>
              {updateMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Save
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

