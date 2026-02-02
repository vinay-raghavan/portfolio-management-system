'use client';

import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { tradingApi } from '@/lib/api';
import { useQuote, useCurrency } from '@/hooks';
import { useTradingStore, useNotificationStore } from '@/store';
import { safeToFixed, cn } from '@/lib/utils';
import { TemplateSelector } from './TemplateSelector';
import type { OrderSide, OrderType, ProductType, OrderCreate } from '@/types';

interface OrderEntryFormProps {
  onSuccess?: () => void;
  onConfirm?: (order: OrderCreate) => void;
}

export function OrderEntryForm({ onSuccess, onConfirm }: OrderEntryFormProps) {
  const queryClient = useQueryClient();
  const { formState, updateForm, resetForm } = useTradingStore();
  const { addNotification } = useNotificationStore();
  const { format: formatCurrency } = useCurrency();
  
  const [symbolInput, setSymbolInput] = useState(formState.symbol);
  
  const { data: quote, isLoading: quoteLoading } = useQuote(formState.symbol, {
    enabled: !!formState.symbol,
    useWebSocket: true,
  });

  // Sync symbol input with form state
  useEffect(() => {
    setSymbolInput(formState.symbol);
  }, [formState.symbol]);

  const createOrderMutation = useMutation({
    mutationFn: (order: OrderCreate) => tradingApi.createOrder(order),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      addNotification({
        type: 'success',
        title: 'Order Placed',
        message: `${formState.side} order for ${formState.quantity} ${formState.symbol} placed successfully`,
      });
      resetForm();
      onSuccess?.();
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Order Failed',
        message: error.response?.data?.detail || 'Failed to place order',
      });
    },
  });

  const handleSymbolBlur = () => {
    updateForm({ symbol: symbolInput.toUpperCase() });
  };

  const estimatedValue = formState.quantity * (formState.price || quote?.price || 0);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const order: OrderCreate = {
      symbol: formState.symbol,
      side: formState.side,
      quantity: formState.quantity,
      order_type: formState.orderType,
      product_type: formState.productType,
      price: formState.orderType === 'LIMIT' ? formState.price ?? undefined : undefined,
      stop_loss: formState.stopLoss ?? undefined,
      take_profit: formState.takeProfit ?? undefined,
    };

    if (onConfirm) {
      onConfirm(order);
    } else {
      createOrderMutation.mutate(order);
    }
  };

  const isValid = formState.symbol && formState.quantity > 0 && 
    (formState.orderType === 'MARKET' || (formState.price && formState.price > 0));

  return (
    <Card>
      <CardHeader className="pb-4">
        <CardTitle>Place Order</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Template Selector */}
        <TemplateSelector />

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Buy/Sell Toggle */}
          <div className="grid grid-cols-2 gap-2">
            <Button
              type="button"
              variant={formState.side === 'BUY' ? 'default' : 'outline'}
              className={cn(formState.side === 'BUY' && 'bg-profit hover:bg-profit/90')}
              onClick={() => updateForm({ side: 'BUY' })}
            >
              Buy
            </Button>
            <Button
              type="button"
              variant={formState.side === 'SELL' ? 'default' : 'outline'}
              className={cn(formState.side === 'SELL' && 'bg-loss hover:bg-loss/90')}
              onClick={() => updateForm({ side: 'SELL' })}
            >
              Sell
            </Button>
          </div>

          {/* Symbol */}
          <div className="space-y-2">
            <Label htmlFor="symbol">Symbol</Label>
            <Input
              id="symbol"
              value={symbolInput}
              onChange={(e) => setSymbolInput(e.target.value.toUpperCase())}
              onBlur={handleSymbolBlur}
              placeholder="e.g., AAPL"
            />
            {quote && (
              <p className="text-sm text-muted-foreground">
                LTP: {formatCurrency(quote.price)}
                <span className={cn('ml-2', (quote.change_pct ?? 0) >= 0 ? 'text-profit' : 'text-loss')}>
                  ({(quote.change_pct ?? 0) >= 0 ? '+' : ''}{safeToFixed(quote.change_pct, 2)}%)
                </span>
              </p>
            )}
          </div>

          {/* Order Type */}
          <div className="space-y-2">
            <Label>Order Type</Label>
            <Select value={formState.orderType} onValueChange={(v) => updateForm({ orderType: v as OrderType })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="MARKET">Market</SelectItem>
                <SelectItem value="LIMIT">Limit</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Quantity */}
          <div className="space-y-2">
            <Label htmlFor="quantity">Quantity</Label>
            <Input
              id="quantity"
              type="number"
              min="1"
              value={formState.quantity}
              onChange={(e) => updateForm({ quantity: parseInt(e.target.value) || 0 })}
            />
          </div>

          {/* Price (for Limit orders) */}
          {formState.orderType === 'LIMIT' && (
            <div className="space-y-2">
              <Label htmlFor="price">Price</Label>
              <Input
                id="price"
                type="number"
                step="0.01"
                min="0"
                value={formState.price ?? ''}
                onChange={(e) => updateForm({ price: parseFloat(e.target.value) || null })}
              />
            </div>
          )}

          {/* Product Type */}
          <div className="space-y-2">
            <Label>Product Type</Label>
            <Select value={formState.productType} onValueChange={(v) => updateForm({ productType: v as ProductType })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="DELIVERY">Delivery (CNC)</SelectItem>
                <SelectItem value="INTRADAY">Intraday (MIS)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Stop Loss & Take Profit */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="stopLoss">Stop Loss</Label>
              <Input
                id="stopLoss"
                type="number"
                step="0.01"
                min="0"
                value={formState.stopLoss ?? ''}
                onChange={(e) => updateForm({ stopLoss: parseFloat(e.target.value) || null })}
                placeholder="Optional"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="takeProfit">Take Profit</Label>
              <Input
                id="takeProfit"
                type="number"
                step="0.01"
                min="0"
                value={formState.takeProfit ?? ''}
                onChange={(e) => updateForm({ takeProfit: parseFloat(e.target.value) || null })}
                placeholder="Optional"
              />
            </div>
          </div>

          {/* Estimated Value */}
          <div className="p-3 bg-muted rounded-lg">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Estimated Value</span>
              <span className="font-medium">{formatCurrency(estimatedValue)}</span>
            </div>
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            className={cn(
              'w-full',
              formState.side === 'BUY' ? 'bg-profit hover:bg-profit/90' : 'bg-loss hover:bg-loss/90'
            )}
            disabled={!isValid || createOrderMutation.isPending}
          >
            {createOrderMutation.isPending ? 'Placing Order...' : `${formState.side} ${formState.symbol || 'Stock'}`}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

