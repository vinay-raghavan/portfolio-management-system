'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, TrendingUp, TrendingDown } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { alertsApi } from '@/lib/api';
import { useSymbolSearch } from '@/hooks';
import { useNotificationStore } from '@/store';
import { cn } from '@/lib/utils';
import type { AlertCondition } from '@/types';

export function CreateAlertForm() {
  const [symbol, setSymbol] = useState('');
  const [condition, setCondition] = useState<AlertCondition>('ABOVE');
  const [targetPrice, setTargetPrice] = useState('');
  const queryClient = useQueryClient();
  const { addNotification } = useNotificationStore();

  const { query, setQuery, results, isLoading: searchLoading, clear } = useSymbolSearch({
    minLength: 1,
    debounceMs: 300,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      alertsApi.createAlert({
        symbol,
        condition,
        target_price: parseFloat(targetPrice),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      addNotification({
        type: 'success',
        title: 'Alert Created',
        message: `Price alert for ${symbol} has been created`,
      });
      setSymbol('');
      setTargetPrice('');
      clear();
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Error',
        message: error.response?.data?.detail || 'Failed to create alert',
      });
    },
  });

  const handleSelectSymbol = (sym: string) => {
    setSymbol(sym);
    setQuery(sym);
    clear();
  };

  const isValid = symbol && targetPrice && parseFloat(targetPrice) > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Plus className="h-5 w-5" />
          Create Alert
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (isValid) createMutation.mutate();
          }}
          className="space-y-4"
        >
          {/* Symbol Search */}
          <div className="space-y-2">
            <Label>Symbol</Label>
            <div className="relative">
              <Input
                placeholder="Search symbol..."
                value={query || symbol}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setSymbol('');
                }}
              />
              {query && results.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-popover border rounded-lg shadow-lg max-h-48 overflow-y-auto">
                  {results.map((result) => (
                    <div
                      key={result.symbol}
                      className="p-2 hover:bg-muted cursor-pointer"
                      onClick={() => handleSelectSymbol(result.symbol)}
                    >
                      <div className="font-medium">{result.symbol}</div>
                      <div className="text-xs text-muted-foreground truncate">{result.name}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Condition */}
          <div className="space-y-2">
            <Label>Condition</Label>
            <div className="flex gap-2">
              <Button
                type="button"
                variant={condition === 'ABOVE' ? 'default' : 'outline'}
                className={cn('flex-1', condition === 'ABOVE' && 'bg-profit hover:bg-profit/90')}
                onClick={() => setCondition('ABOVE')}
              >
                <TrendingUp className="h-4 w-4 mr-2" />
                Above
              </Button>
              <Button
                type="button"
                variant={condition === 'BELOW' ? 'default' : 'outline'}
                className={cn('flex-1', condition === 'BELOW' && 'bg-loss hover:bg-loss/90')}
                onClick={() => setCondition('BELOW')}
              >
                <TrendingDown className="h-4 w-4 mr-2" />
                Below
              </Button>
            </div>
          </div>

          {/* Target Price */}
          <div className="space-y-2">
            <Label htmlFor="targetPrice">Target Price</Label>
            <Input
              id="targetPrice"
              type="number"
              step="0.01"
              min="0"
              placeholder="Enter price..."
              value={targetPrice}
              onChange={(e) => setTargetPrice(e.target.value)}
            />
          </div>

          <Button
            type="submit"
            className="w-full"
            disabled={!isValid || createMutation.isPending}
          >
            {createMutation.isPending ? 'Creating...' : 'Create Alert'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

