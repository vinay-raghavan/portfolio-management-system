'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Wallet, CreditCard, PiggyBank, Plus, Minus, RotateCcw, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { portfolioApi } from '@/lib/api';
import { useCurrency } from '@/hooks/useCurrency';
import { cn } from '@/lib/utils';
import { useToast } from '@/components/ui/use-toast';

type ActionType = 'deposit' | 'withdraw' | 'reset' | null;

interface FundCardProps {
  icon: React.ElementType;
  label: string;
  value: string;
  color: 'blue' | 'emerald' | 'amber' | 'purple' | 'slate';
}

function FundCard({ icon: Icon, label, value, color }: FundCardProps) {
  const colorClasses = {
    blue: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
    emerald: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
    amber: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
    purple: 'bg-purple-500/10 text-purple-600 dark:text-purple-400',
    slate: 'bg-slate-500/10 text-slate-600 dark:text-slate-400',
  };
  return (
    <div className={cn('p-4 rounded-lg', colorClasses[color])}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className="h-4 w-4" />
        <span className="text-xs font-medium">{label}</span>
      </div>
      <p className="text-lg font-bold">{value}</p>
    </div>
  );
}

export function FundsManagement() {
  const { format: formatCurrency } = useCurrency();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [actionType, setActionType] = useState<ActionType>(null);
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [resetAmount, setResetAmount] = useState('');

  const { data: funds, isLoading } = useQuery({
    queryKey: ['funds'],
    queryFn: () => portfolioApi.getFunds().then((res) => res.data),
    refetchInterval: 30000,
  });

  const depositMutation = useMutation({
    mutationFn: (data: { amount: number; note?: string }) => portfolioApi.depositFunds(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['funds'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      toast({ title: 'Success', description: 'Funds deposited successfully' });
      handleClose();
    },
    onError: (error: Error) => toast({ title: 'Error', description: error.message || 'Failed to deposit funds', variant: 'destructive' }),
  });

  const withdrawMutation = useMutation({
    mutationFn: (data: { amount: number; note?: string }) => portfolioApi.withdrawFunds(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['funds'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      toast({ title: 'Success', description: 'Funds withdrawn successfully' });
      handleClose();
    },
    onError: (error: Error) => toast({ title: 'Error', description: error.message || 'Failed to withdraw funds', variant: 'destructive' }),
  });

  const resetMutation = useMutation({
    mutationFn: (data?: { initial_balance?: number }) => portfolioApi.resetFunds(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['funds'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      toast({ title: 'Success', description: 'Funds reset successfully' });
      handleClose();
    },
    onError: (error: Error) => toast({ title: 'Error', description: error.message || 'Failed to reset funds', variant: 'destructive' }),
  });

  const handleClose = () => {
    setActionType(null);
    setAmount('');
    setNote('');
    setResetAmount('');
  };

  const handleSubmit = () => {
    if (actionType === 'deposit') {
      const amountNum = parseFloat(amount);
      if (amountNum > 0) depositMutation.mutate({ amount: amountNum, note: note || undefined });
    } else if (actionType === 'withdraw') {
      const amountNum = parseFloat(amount);
      if (amountNum > 0) withdrawMutation.mutate({ amount: amountNum, note: note || undefined });
    } else if (actionType === 'reset') {
      const resetAmountNum = resetAmount ? parseFloat(resetAmount) : undefined;
      resetMutation.mutate(resetAmountNum ? { initial_balance: resetAmountNum } : undefined);
    }
  };

  const isSubmitting = depositMutation.isPending || withdrawMutation.isPending || resetMutation.isPending;

  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><Wallet className="h-5 w-5" />Funds Management</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-3 gap-4">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-24 w-full" />)}</div>
          <Skeleton className="h-10 w-full" />
        </CardContent>
      </Card>
    );
  }

  const availableCash = funds?.available_cash ?? 0;
  const marginUsed = funds?.margin_used ?? 0;
  const totalBalance = funds?.total_balance ?? 0;
  const collateral = funds?.collateral ?? 0;

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Wallet className="h-5 w-5" />Funds Management</CardTitle>
          <CardDescription>Manage your paper trading funds - deposit, withdraw, or reset balance</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <FundCard icon={Wallet} label="Total Balance" value={formatCurrency(totalBalance)} color="blue" />
            <FundCard icon={PiggyBank} label="Available Cash" value={formatCurrency(availableCash)} color="emerald" />
            <FundCard icon={CreditCard} label="Margin Used" value={formatCurrency(marginUsed)} color={marginUsed > 0 ? 'amber' : 'slate'} />
            <FundCard icon={CreditCard} label="Collateral" value={formatCurrency(collateral)} color="purple" />
          </div>
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => setActionType('deposit')} className="flex-1 min-w-[120px]"><Plus className="h-4 w-4 mr-2" />Deposit</Button>
            <Button onClick={() => setActionType('withdraw')} variant="outline" className="flex-1 min-w-[120px]" disabled={availableCash <= 0}><Minus className="h-4 w-4 mr-2" />Withdraw</Button>
            <Button onClick={() => setActionType('reset')} variant="secondary" className="flex-1 min-w-[120px]"><RotateCcw className="h-4 w-4 mr-2" />Reset Balance</Button>
          </div>
        </CardContent>
      </Card>
      <Dialog open={actionType !== null} onOpenChange={(open) => !open && handleClose()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {actionType === 'deposit' && 'Deposit Funds'}
              {actionType === 'withdraw' && 'Withdraw Funds'}
              {actionType === 'reset' && 'Reset Balance'}
            </DialogTitle>
            <DialogDescription>
              {actionType === 'deposit' && 'Add funds to your paper trading account.'}
              {actionType === 'withdraw' && 'Withdraw funds from your available balance.'}
              {actionType === 'reset' && 'Reset your balance to the initial amount.'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {actionType === 'reset' && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>This will reset your balance and clear all margin.</AlertDescription>
              </Alert>
            )}
            {(actionType === 'deposit' || actionType === 'withdraw') && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="amount">Amount</Label>
                  <Input id="amount" type="number" placeholder="Enter amount" value={amount} onChange={(e) => setAmount(e.target.value)} min="0" step="1000" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="note">Note (optional)</Label>
                  <Input id="note" placeholder="Add a note" value={note} onChange={(e) => setNote(e.target.value)} />
                </div>
                {actionType === 'withdraw' && <p className="text-sm text-muted-foreground">Available to withdraw: {formatCurrency(availableCash)}</p>}
              </>
            )}
            {actionType === 'reset' && (
              <div className="space-y-2">
                <Label htmlFor="resetAmount">Initial Balance (optional)</Label>
                <Input id="resetAmount" type="number" placeholder="Leave empty for default (₹10,00,000)" value={resetAmount} onChange={(e) => setResetAmount(e.target.value)} min="0" step="100000" />
                <p className="text-sm text-muted-foreground">Leave empty to use the default initial balance.</p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleClose} disabled={isSubmitting}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={isSubmitting || ((actionType === 'deposit' || actionType === 'withdraw') && (!amount || parseFloat(amount) <= 0))} variant={actionType === 'reset' ? 'destructive' : 'default'}>
              {isSubmitting ? 'Processing...' : 'Confirm'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

