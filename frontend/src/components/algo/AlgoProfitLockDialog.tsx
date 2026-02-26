'use client';

import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Lock, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
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
import { useCurrency } from '@/hooks/useCurrency';
import type { UnrealizedPnLPosition, ProfitLockUpdate } from '@/types';

interface AlgoProfitLockDialogProps {
  position: UnrealizedPnLPosition | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AlgoProfitLockDialog({ position, open, onOpenChange }: AlgoProfitLockDialogProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { format: formatValue } = useCurrency();
  const [enabled, setEnabled] = useState(false);

  // Fetch existing profit lock config
  const { data: existingConfig } = useQuery({
    queryKey: ['algo-profit-lock-config', position?.position_id],
    queryFn: () => algoApi.getAlgoProfitLockConfig(position!.position_id),
    enabled: !!position?.position_id && open,
  });

  useEffect(() => {
    if (existingConfig?.data) {
      setEnabled(existingConfig.data.enabled ?? false);
    }
  }, [existingConfig]);

  const updateMutation = useMutation({
    mutationFn: async (data: ProfitLockUpdate) => {
      return await algoApi.updateAlgoProfitLock(position!.position_id, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['algo-unrealized-pnl'] });
      queryClient.invalidateQueries({ queryKey: ['algo-profit-lock-config', position?.position_id] });
      toast({
        title: 'Profit lock updated',
        description: enabled
          ? 'Profit lock enabled. Stop will lock at profit level once threshold is reached.'
          : 'Profit lock disabled.',
      });
      onOpenChange(false);
    },
    onError: (error: any) => {
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to update profit lock.';
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate({ enabled });
  };

  if (!position) return null;

  const isActivated = existingConfig?.data?.activated ?? false;
  const profitLockPrice = existingConfig?.data?.profit_lock_price;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Lock className="h-5 w-5" />
            Profit Lock - {position.symbol} ({position.side})
          </DialogTitle>
          <DialogDescription>
            When enabled, once your position reaches the first profit booking threshold,
            the stop loss will lock at a profit level using the trailing stop percentage as a buffer.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex items-center justify-between">
            <Label htmlFor="enabled">Enable Profit Lock</Label>
            <Switch id="enabled" checked={enabled} onCheckedChange={setEnabled} />
          </div>

          {isActivated && profitLockPrice && (
            <div className="rounded-lg border p-3 space-y-2 bg-green-50 dark:bg-green-900/20">
              <div className="flex items-center gap-2 text-sm font-medium text-green-700 dark:text-green-400">
                <Lock className="h-4 w-4" />
                Profit Lock Activated!
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Locked Stop Price:</span>
                <span className="font-medium text-green-600 dark:text-green-400">
                  {formatValue(profitLockPrice)}
                </span>
              </div>
            </div>
          )}

          {enabled && !isActivated && (
            <div className="rounded-lg border p-3 space-y-2 bg-muted/50">
              <p className="text-xs text-muted-foreground">
                The profit lock will activate once the position reaches the first profit booking threshold.
                The stop will then be set using the trailing stop percentage as a buffer below the activation price.
              </p>
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

