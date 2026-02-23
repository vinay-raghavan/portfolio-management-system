'use client';

import { useState } from 'react';
import { Bell, Check, X, AlertTriangle, Bot } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useNotificationStore, type Notification } from '@/store';
import { useToast } from '@/components/ui/use-toast';
import { autoTradeApi } from '@/lib/api';
import { cn } from '@/lib/utils';

const NOTIFICATION_ICONS: Record<string, typeof Bell> = {
  success: Check,
  error: X,
  warning: AlertTriangle,
  info: Bell,
  auto_trade: Bot,
};

// Component for pending trade action buttons
function PendingTradeActions({
  notification,
  onAction,
  isLoading,
}: {
  notification: Notification;
  onAction: (action: 'approve' | 'reject') => void;
  isLoading: boolean;
}) {
  const pendingTradeId = notification.data?.pendingTradeId as string | undefined;
  if (!pendingTradeId) return null;

  return (
    <div className="flex items-center gap-1 mt-2">
      <Button
        size="sm"
        variant="outline"
        className="h-6 px-2 text-xs text-green-600 border-green-600 hover:bg-green-50 dark:hover:bg-green-950"
        onClick={(e) => {
          e.stopPropagation();
          onAction('approve');
        }}
        disabled={isLoading}
      >
        <Check className="h-3 w-3 mr-1" />
        Approve
      </Button>
      <Button
        size="sm"
        variant="outline"
        className="h-6 px-2 text-xs text-red-600 border-red-600 hover:bg-red-50 dark:hover:bg-red-950"
        onClick={(e) => {
          e.stopPropagation();
          onAction('reject');
        }}
        disabled={isLoading}
      >
        <X className="h-3 w-3 mr-1" />
        Reject
      </Button>
    </div>
  );
}

export function NotificationBell() {
  const { notifications, removeNotification, clearAll } = useNotificationStore();
  const [isOpen, setIsOpen] = useState(false);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const unreadCount = notifications.filter((n) => !n.read).length;

  const actionMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'approve' | 'reject'; notificationId: string }) =>
      autoTradeApi.actionPendingTrade(id, { action }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['pending-auto-trades'] });
      removeNotification(variables.notificationId);
      toast({
        title: variables.action === 'approve' ? 'Trade approved' : 'Trade rejected',
        description: variables.action === 'approve'
          ? 'Strategy will be created and executed'
          : 'Trade recommendation dismissed',
      });
    },
    onError: () => {
      toast({ title: 'Error', description: 'Failed to process trade', variant: 'destructive' });
    },
  });

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return date.toLocaleDateString();
  };

  const handlePendingTradeAction = (notification: Notification, action: 'approve' | 'reject') => {
    const pendingTradeId = notification.data?.pendingTradeId as string;
    if (pendingTradeId) {
      actionMutation.mutate({ id: pendingTradeId, action, notificationId: notification.id });
    }
  };

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          aria-label={unreadCount > 0 ? `Notifications, ${unreadCount} unread` : 'Notifications'}
        >
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span
              className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-destructive text-destructive-foreground text-xs flex items-center justify-center"
              aria-hidden="true"
            >
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel className="flex items-center justify-between">
          <span>Notifications</span>
          {notifications.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
              onClick={() => clearAll()}
            >
              Clear all
            </Button>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {notifications.length === 0 ? (
          <div className="py-8 text-center text-muted-foreground">
            <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No notifications</p>
          </div>
        ) : (
          <div className="max-h-80 overflow-y-auto">
            {notifications.slice(0, 10).map((notification) => {
              const hasPendingTrade = !!notification.data?.pendingTradeId;
              const Icon = hasPendingTrade ? Bot : (NOTIFICATION_ICONS[notification.type] || Bell);
              return (
                <DropdownMenuItem
                  key={notification.id}
                  className="flex items-start gap-3 p-3 cursor-pointer"
                  onSelect={(e) => e.preventDefault()}
                >
                  <div
                    className={cn(
                      'p-1.5 rounded-full shrink-0',
                      hasPendingTrade && 'bg-purple-500/10 text-purple-500',
                      !hasPendingTrade && notification.type === 'success' && 'bg-green-500/10 text-green-500',
                      !hasPendingTrade && notification.type === 'error' && 'bg-red-500/10 text-red-500',
                      !hasPendingTrade && notification.type === 'warning' && 'bg-yellow-500/10 text-yellow-500',
                      !hasPendingTrade && notification.type === 'info' && 'bg-blue-500/10 text-blue-500'
                    )}
                  >
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{notification.title}</p>
                    <p className="text-xs text-muted-foreground truncate">
                      {notification.message}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatTime(notification.timestamp)}
                    </p>
                    {/* Action buttons for pending trades */}
                    <PendingTradeActions
                      notification={notification}
                      onAction={(action) => handlePendingTradeAction(notification, action)}
                      isLoading={actionMutation.isPending}
                    />
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0 shrink-0"
                    onClick={() => removeNotification(notification.id)}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </DropdownMenuItem>
              );
            })}
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

