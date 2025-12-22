'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { tradingApi } from '@/lib/api';
import { useNotificationStore } from '@/store';
import { formatCurrency, cn } from '@/lib/utils';
import type { OrderCreate } from '@/types';

interface OrderConfirmationModalProps {
  order: OrderCreate | null;
  estimatedPrice: number;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function OrderConfirmationModal({
  order,
  estimatedPrice,
  isOpen,
  onClose,
  onSuccess,
}: OrderConfirmationModalProps) {
  const queryClient = useQueryClient();
  const { addNotification } = useNotificationStore();

  const createOrderMutation = useMutation({
    mutationFn: (orderData: OrderCreate) => tradingApi.createOrder(orderData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      addNotification({
        type: 'success',
        title: 'Order Placed',
        message: `${order?.side} order for ${order?.quantity} ${order?.symbol} placed successfully`,
      });
      onClose();
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

  if (!order) return null;

  const estimatedValue = order.quantity * (order.price || estimatedPrice);
  const isBuy = order.side === 'BUY';

  const handleConfirm = () => {
    createOrderMutation.mutate(order);
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Confirm Order</DialogTitle>
          <DialogDescription>
            Please review your order details before confirming.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Order Summary */}
          <div className="p-4 rounded-lg bg-muted space-y-3">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Action</span>
              <span className={cn('font-medium', isBuy ? 'text-profit' : 'text-loss')}>
                {order.side}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Symbol</span>
              <span className="font-medium">{order.symbol}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Quantity</span>
              <span className="font-medium">{order.quantity}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Order Type</span>
              <span className="font-medium">{order.order_type}</span>
            </div>
            {order.price && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Price</span>
                <span className="font-medium">{formatCurrency(order.price)}</span>
              </div>
            )}
            {order.stop_loss && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Stop Loss</span>
                <span className="font-medium">{formatCurrency(order.stop_loss)}</span>
              </div>
            )}
            {order.take_profit && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Take Profit</span>
                <span className="font-medium">{formatCurrency(order.take_profit)}</span>
              </div>
            )}
            <div className="border-t pt-3 flex justify-between">
              <span className="font-medium">Estimated Value</span>
              <span className="font-bold">{formatCurrency(estimatedValue)}</span>
            </div>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={onClose} disabled={createOrderMutation.isPending}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={createOrderMutation.isPending}
            className={cn(isBuy ? 'bg-profit hover:bg-profit/90' : 'bg-loss hover:bg-loss/90')}
          >
            {createOrderMutation.isPending ? 'Placing...' : 'Confirm Order'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

