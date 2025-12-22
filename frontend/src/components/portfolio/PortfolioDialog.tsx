'use client';

import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Loader2, Trash2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { portfolioApi } from '@/lib/api';
import { useToast } from '@/components/ui/use-toast';
import { usePortfolioStore } from '@/store';
import type { PortfolioInfo } from '@/types';

interface PortfolioDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  portfolio?: PortfolioInfo | null;
}

const CURRENCIES = ['INR', 'USD', 'EUR', 'GBP'];

export function PortfolioDialog({ open, onOpenChange, portfolio }: PortfolioDialogProps) {
  const isEditing = !!portfolio;
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { selectedPortfolioId, setSelectedPortfolio } = usePortfolioStore();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    currency: 'INR',
    is_default: false,
  });

  useEffect(() => {
    if (portfolio) {
      setFormData({
        name: portfolio.name,
        description: portfolio.description || '',
        currency: portfolio.currency,
        is_default: portfolio.is_default,
      });
    } else {
      setFormData({ name: '', description: '', currency: 'INR', is_default: false });
    }
  }, [portfolio, open]);

  const createMutation = useMutation({
    mutationFn: () => portfolioApi.createPortfolio(formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
      toast({ title: 'Portfolio created', description: `${formData.name} has been created.` });
      onOpenChange(false);
    },
    onError: () => {
      toast({ title: 'Error', description: 'Failed to create portfolio.', variant: 'destructive' });
    },
  });

  const updateMutation = useMutation({
    mutationFn: () => portfolioApi.updatePortfolio(portfolio!.id, formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio', portfolio!.id] });
      toast({ title: 'Portfolio updated', description: `${formData.name} has been updated.` });
      onOpenChange(false);
    },
    onError: () => {
      toast({ title: 'Error', description: 'Failed to update portfolio.', variant: 'destructive' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => portfolioApi.deletePortfolio(portfolio!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
      if (selectedPortfolioId === portfolio!.id) {
        setSelectedPortfolio(null);
      }
      toast({ title: 'Portfolio deleted', description: `${portfolio!.name} has been deleted.` });
      setShowDeleteConfirm(false);
      onOpenChange(false);
    },
    onError: () => {
      toast({ title: 'Error', description: 'Failed to delete portfolio. It may have positions.', variant: 'destructive' });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isEditing) {
      updateMutation.mutate();
    } else {
      createMutation.mutate();
    }
  };

  const isLoading = createMutation.isPending || updateMutation.isPending;

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-[425px]">
          <form onSubmit={handleSubmit}>
            <DialogHeader>
              <DialogTitle>{isEditing ? 'Edit Portfolio' : 'Create Portfolio'}</DialogTitle>
              <DialogDescription>
                {isEditing ? 'Update your portfolio settings.' : 'Create a new portfolio to organize your investments.'}
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="My Portfolio"
                  required
                  maxLength={100}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="description">Description (optional)</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Portfolio description..."
                  maxLength={500}
                  rows={3}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="currency">Currency</Label>
                <Select
                  value={formData.currency}
                  onValueChange={(value) => setFormData({ ...formData, currency: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select currency" />
                  </SelectTrigger>
                  <SelectContent>
                    {CURRENCIES.map((currency) => (
                      <SelectItem key={currency} value={currency}>
                        {currency}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="is_default">Default Portfolio</Label>
                  <p className="text-sm text-muted-foreground">
                    New trades will use this portfolio by default
                  </p>
                </div>
                <Switch
                  id="is_default"
                  checked={formData.is_default}
                  onCheckedChange={(checked) => setFormData({ ...formData, is_default: checked })}
                />
              </div>
            </div>
            <DialogFooter className="gap-2 sm:gap-0">
              {isEditing && (
                <Button
                  type="button"
                  variant="destructive"
                  onClick={() => setShowDeleteConfirm(true)}
                  disabled={isLoading}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </Button>
              )}
              <Button type="submit" disabled={isLoading || !formData.name.trim()}>
                {isLoading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                {isEditing ? 'Save Changes' : 'Create Portfolio'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Portfolio</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &quot;{portfolio?.name}&quot;? This action cannot be undone.
              Portfolios with open positions cannot be deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteMutation.mutate()}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

