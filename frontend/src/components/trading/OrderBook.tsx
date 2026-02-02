'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { X, ChevronLeft, ChevronRight, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { tradingApi } from '@/lib/api';
import { useNotificationStore } from '@/store';
import { useCurrency } from '@/hooks/useCurrency';
import { cn } from '@/lib/utils';
import type { Order, OrderStatus } from '@/types';

const STATUS_CONFIG: Record<OrderStatus, { icon: typeof Clock; color: string; label: string }> = {
  PENDING: { icon: Clock, color: 'bg-yellow-500/10 text-yellow-500', label: 'Pending' },
  OPEN: { icon: Clock, color: 'bg-blue-500/10 text-blue-500', label: 'Open' },
  FILLED: { icon: CheckCircle, color: 'bg-green-500/10 text-green-500', label: 'Filled' },
  PARTIALLY_FILLED: { icon: AlertCircle, color: 'bg-orange-500/10 text-orange-500', label: 'Partial' },
  CANCELLED: { icon: XCircle, color: 'bg-gray-500/10 text-gray-500', label: 'Cancelled' },
  REJECTED: { icon: XCircle, color: 'bg-red-500/10 text-red-500', label: 'Rejected' },
  EXPIRED: { icon: XCircle, color: 'bg-gray-500/10 text-gray-500', label: 'Expired' },
};

interface OrderBookProps {
  statusFilter?: OrderStatus;
  pageSize?: number;
}

export function OrderBook({ statusFilter, pageSize = 10 }: OrderBookProps) {
  const [page, setPage] = useState(1);
  const queryClient = useQueryClient();
  const { addNotification } = useNotificationStore();
  const { format: formatCurrency } = useCurrency();

  const { data, isLoading } = useQuery({
    queryKey: ['orders', statusFilter, page, pageSize],
    queryFn: () => tradingApi.getOrders(statusFilter, page, pageSize).then((res) => res.data),
    refetchInterval: 10000,
  });

  const cancelMutation = useMutation({
    mutationFn: (orderId: string) => tradingApi.cancelOrder(orderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      addNotification({
        type: 'success',
        title: 'Order Cancelled',
        message: 'Order has been cancelled successfully',
      });
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Cancel Failed',
        message: error.response?.data?.detail || 'Failed to cancel order',
      });
    },
  });

  const orders = data?.orders ?? [];
  const totalCount = data?.total_count ?? 0;
  const currentPageSize = data?.page_size ?? pageSize;
  const totalPages = Math.ceil(totalCount / currentPageSize) || 1;

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Orders</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-muted rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Orders</CardTitle>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm text-muted-foreground">
            {page} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {orders.length === 0 ? (
          <p className="text-muted-foreground text-center py-8">No orders found</p>
        ) : (
          <div className="space-y-3">
            {orders.map((order: Order) => {
              const config = STATUS_CONFIG[order.status];
              const StatusIcon = config.icon;
              const canCancel = ['PENDING', 'OPEN'].includes(order.status);

              return (
                <div
                  key={order.id}
                  className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/30"
                >
                  <div className="flex items-center gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{order.symbol}</span>
                        <Badge variant="outline" className={cn(order.side === 'BUY' ? 'text-profit' : 'text-loss')}>
                          {order.side}
                        </Badge>
                        <Badge variant="outline" className={config.color}>
                          <StatusIcon className="h-3 w-3 mr-1" />
                          {config.label}
                        </Badge>
                      </div>
                      <div className="text-sm text-muted-foreground mt-1">
                        {order.quantity} @ {order.order_type === 'MARKET' ? 'Market' : formatCurrency(order.price ?? 0)}
                        {' • '}{formatDate(order.created_at)}
                      </div>
                    </div>
                  </div>
                  {canCancel && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => cancelMutation.mutate(order.id)}
                      disabled={cancelMutation.isPending}
                      aria-label={`Cancel ${order.side} order for ${order.symbol}`}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

