'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ChevronRight, ChevronLeft, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { tradingApi } from '@/lib/api';
import { useQuote, useCurrency } from '@/hooks';
import { useNotificationStore } from '@/store';
import { safeToFixed, cn } from '@/lib/utils';
import type { OrderSide, OrderType, ProductType, OrderCreate } from '@/types';

interface QuickTradePanelProps {
  symbol: string;
  defaultExpanded?: boolean;
  className?: string;
}

export function QuickTradePanel({ symbol, defaultExpanded = false, className }: QuickTradePanelProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [side, setSide] = useState<OrderSide>('BUY');
  const [orderType, setOrderType] = useState<OrderType>('MARKET');
  const [quantity, setQuantity] = useState(1);
  const [price, setPrice] = useState<number | null>(null);
  const [productType, setProductType] = useState<ProductType>('DELIVERY');

  const queryClient = useQueryClient();
  const { addNotification } = useNotificationStore();
  const { format: formatCurrency } = useCurrency();
  
  const { data: quote, isLoading: quoteLoading } = useQuote(symbol, {
    enabled: !!symbol && isExpanded,
    useWebSocket: true,
  });

  const createOrderMutation = useMutation({
    mutationFn: (order: OrderCreate) => tradingApi.createOrder(order),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      addNotification({
        type: 'success',
        title: 'Order Placed',
        message: `${side} order for ${quantity} ${symbol} placed successfully`,
      });
      setQuantity(1);
      setPrice(null);
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Order Failed',
        message: error.response?.data?.detail || 'Failed to place order',
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const order: OrderCreate = {
      symbol,
      side,
      quantity,
      order_type: orderType,
      product_type: productType,
      price: orderType === 'LIMIT' ? price ?? undefined : undefined,
    };

    createOrderMutation.mutate(order);
  };

  const estimatedValue = quantity * (price || quote?.price || 0);
  const isValid = symbol && quantity > 0 && 
    (orderType === 'MARKET' || (price && price > 0));

  if (!isExpanded) {
    return (
      <Button
        variant="outline"
        size="sm"
        onClick={() => setIsExpanded(true)}
        className={cn('fixed right-0 top-1/2 -translate-y-1/2 rounded-l-lg rounded-r-none z-50', className)}
        aria-label="Open trade panel"
      >
        <ChevronLeft className="h-4 w-4 mr-1" />
        Trade
      </Button>
    );
  }

  return (
    <div className={cn(
      'fixed right-0 top-1/2 -translate-y-1/2 w-72 bg-card border rounded-l-lg shadow-lg z-50',
      className
    )}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <div>
          <h3 className="font-semibold text-sm">Quick Trade</h3>
          <p className="text-xs text-muted-foreground">{symbol}</p>
        </div>
        <Button variant="ghost" size="icon" onClick={() => setIsExpanded(false)} aria-label="Close trade panel">
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* Quote Info */}
      {quote && (
        <div className="px-3 py-2 border-b bg-muted/50">
          <div className="flex items-baseline justify-between">
            <span className="text-lg font-bold">{formatCurrency(quote.price)}</span>
            <span className={cn('text-sm font-medium', (quote.change_pct ?? 0) >= 0 ? 'text-profit' : 'text-loss')}>
              {(quote.change_pct ?? 0) >= 0 ? '+' : ''}{safeToFixed(quote.change_pct, 2)}%
            </span>
          </div>
        </div>
      )}

      {/* Order Form */}
      <form onSubmit={handleSubmit} className="p-3 space-y-3">
        {/* Buy/Sell Toggle */}
        <div className="grid grid-cols-2 gap-2">
          <Button
            type="button"
            size="sm"
            variant={side === 'BUY' ? 'default' : 'outline'}
            className={cn(side === 'BUY' && 'bg-profit hover:bg-profit/90')}
            onClick={() => setSide('BUY')}
          >
            Buy
          </Button>
          <Button
            type="button"
            size="sm"
            variant={side === 'SELL' ? 'default' : 'outline'}
            className={cn(side === 'SELL' && 'bg-loss hover:bg-loss/90')}
            onClick={() => setSide('SELL')}
          >
            Sell
          </Button>
        </div>

        {/* Order Type & Product */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <Label className="text-xs">Type</Label>
            <Select value={orderType} onValueChange={(v) => setOrderType(v as OrderType)}>
              <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="MARKET">Market</SelectItem>
                <SelectItem value="LIMIT">Limit</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">Product</Label>
            <Select value={productType} onValueChange={(v) => setProductType(v as ProductType)}>
              <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="DELIVERY">Delivery</SelectItem>
                <SelectItem value="INTRADAY">Intraday</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Quantity */}
        <div>
          <Label className="text-xs">Quantity</Label>
          <Input
            type="number"
            min={1}
            value={quantity}
            onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
            className="h-8 text-sm"
          />
        </div>

        {/* Price (for Limit orders) */}
        {orderType === 'LIMIT' && (
          <div>
            <Label className="text-xs">Limit Price</Label>
            <Input
              type="number"
              step="0.01"
              value={price ?? ''}
              onChange={(e) => setPrice(parseFloat(e.target.value) || null)}
              placeholder={quote ? safeToFixed(quote.price, 2) : '0.00'}
              className="h-8 text-sm"
            />
          </div>
        )}

        {/* Estimated Value */}
        <div className="text-xs text-muted-foreground flex justify-between py-1 border-t">
          <span>Est. Value:</span>
          <span className="font-medium">{formatCurrency(estimatedValue)}</span>
        </div>

        {/* Submit Button */}
        <Button
          type="submit"
          disabled={!isValid || createOrderMutation.isPending}
          className={cn(
            'w-full',
            side === 'BUY' ? 'bg-profit hover:bg-profit/90' : 'bg-loss hover:bg-loss/90'
          )}
        >
          {createOrderMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
          ) : null}
          {side === 'BUY' ? 'Buy' : 'Sell'} {symbol}
        </Button>
      </form>
    </div>
  );
}

