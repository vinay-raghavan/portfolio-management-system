'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bell, BellOff, Trash2, TrendingUp, TrendingDown } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { alertsApi } from '@/lib/api';
import { useNotificationStore } from '@/store';
import { useCurrency } from '@/hooks/useCurrency';
import { cn } from '@/lib/utils';
import type { Alert, AlertStatus } from '@/types';

const STATUS_COLORS: Record<AlertStatus, string> = {
  ACTIVE: 'bg-green-500/10 text-green-500',
  TRIGGERED: 'bg-yellow-500/10 text-yellow-500',
  EXPIRED: 'bg-gray-500/10 text-gray-500',
  DISABLED: 'bg-gray-500/10 text-gray-500',
};

export function AlertList() {
  const queryClient = useQueryClient();
  const { addNotification } = useNotificationStore();
  const { format: formatCurrency } = useCurrency();

  const { data, isLoading } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => alertsApi.getAlerts().then((res) => res.data),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => alertsApi.deleteAlert(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      addNotification({ type: 'success', title: 'Alert Deleted', message: 'Alert has been deleted' });
    },
    onError: (error: any) => {
      addNotification({ type: 'error', title: 'Error', message: error.response?.data?.detail || 'Failed to delete alert' });
    },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      alertsApi.updateAlert(id, { enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
    onError: (error: any) => {
      addNotification({ type: 'error', title: 'Error', message: error.response?.data?.detail || 'Failed to update alert' });
    },
  });

  const alerts = data?.alerts ?? [];

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Price Alerts</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-16 bg-muted rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bell className="h-5 w-5" />
          Price Alerts
        </CardTitle>
      </CardHeader>
      <CardContent>
        {alerts.length === 0 ? (
          <p className="text-muted-foreground text-center py-8">
            No alerts configured. Create one to get notified when prices change.
          </p>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert: Alert) => {
              const isAbove = alert.condition === 'ABOVE';
              return (
                <div
                  key={alert.id}
                  className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted/30"
                >
                  <div className="flex items-center gap-4">
                    {isAbove ? (
                      <TrendingUp className="h-5 w-5 text-profit" />
                    ) : (
                      <TrendingDown className="h-5 w-5 text-loss" />
                    )}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{alert.symbol}</span>
                        <Badge variant="outline" className={STATUS_COLORS[alert.status]}>
                          {alert.status}
                        </Badge>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Alert when price goes {isAbove ? 'above' : 'below'}{' '}
                        <span className="font-medium">{formatCurrency(alert.target_price)}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleMutation.mutate({ id: alert.id, enabled: alert.status === 'DISABLED' })}
                      aria-label={alert.status === 'DISABLED' ? `Enable alert for ${alert.symbol}` : `Disable alert for ${alert.symbol}`}
                    >
                      {alert.status === 'DISABLED' ? (
                        <Bell className="h-4 w-4" />
                      ) : (
                        <BellOff className="h-4 w-4" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => deleteMutation.mutate(alert.id)}
                      aria-label={`Delete alert for ${alert.symbol}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

