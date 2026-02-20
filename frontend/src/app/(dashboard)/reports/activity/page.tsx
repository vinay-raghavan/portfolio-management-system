'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Activity,
  ChevronLeft,
  ChevronRight,
  Bell,
  CheckCheck,
  Filter,
  ShoppingCart,
  TrendingUp,
  AlertTriangle,
  Shield,
  Settings,
  User,
  Bot,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/components/ui/use-toast';
import { reportsApi } from '@/lib/api';
import { cn } from '@/lib/utils';
import type { ActivityCategory, ActivitySeverity } from '@/types';

const CATEGORY_OPTIONS: { value: ActivityCategory | 'ALL'; label: string; icon: typeof Activity }[] = [
  { value: 'ALL', label: 'All Categories', icon: Activity },
  { value: 'auth', label: 'Authentication', icon: User },
  { value: 'trading', label: 'Trading', icon: ShoppingCart },
  { value: 'portfolio', label: 'Portfolio', icon: TrendingUp },
  { value: 'algo', label: 'Algo Trading', icon: Bot },
  { value: 'risk', label: 'Risk', icon: Shield },
  { value: 'broker', label: 'Broker', icon: Activity },
  { value: 'settings', label: 'Settings', icon: Settings },
];

const SEVERITY_OPTIONS: { value: ActivitySeverity | 'ALL'; label: string }[] = [
  { value: 'ALL', label: 'All Severity' },
  { value: 'info', label: 'Info' },
  { value: 'warning', label: 'Warning' },
  { value: 'error', label: 'Error' },
  { value: 'critical', label: 'Critical' },
];

const getCategoryIcon = (category: string) => {
  const cat = CATEGORY_OPTIONS.find((c) => c.value === category);
  return cat?.icon ?? Activity;
};

const getSeverityStyle = (severity: string) => {
  switch (severity) {
    case 'critical':
      return 'bg-red-500/10 text-red-600 border-red-500/20';
    case 'error':
      return 'bg-red-500/10 text-red-500 border-red-500/20';
    case 'warning':
      return 'bg-amber-500/10 text-amber-600 border-amber-500/20';
    default:
      return 'bg-blue-500/10 text-blue-600 border-blue-500/20';
  }
};

const getIconBg = (severity: string) => {
  switch (severity) {
    case 'critical':
    case 'error':
      return 'bg-red-500/10';
    case 'warning':
      return 'bg-amber-500/10';
    default:
      return 'bg-blue-500/10';
  }
};

const getIconColor = (severity: string) => {
  switch (severity) {
    case 'critical':
    case 'error':
      return 'text-red-500';
    case 'warning':
      return 'text-amber-500';
    default:
      return 'text-blue-500';
  }
};

export default function ActivityFeedPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [category, setCategory] = useState<ActivityCategory | 'ALL'>('ALL');
  const [severity, setSeverity] = useState<ActivitySeverity | 'ALL'>('ALL');
  const [readFilter, setReadFilter] = useState<'ALL' | 'unread' | 'read'>('ALL');

  // Fetch activities
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['activities', category, severity, readFilter, page, pageSize],
    queryFn: () =>
      reportsApi
        .getActivities({
          category: category === 'ALL' ? undefined : category,
          severity: severity === 'ALL' ? undefined : severity,
          is_read: readFilter === 'ALL' ? undefined : readFilter === 'read',
          page,
          page_size: pageSize,
        })
        .then((res) => res.data),
  });

  // Mark all as read mutation
  const markAllReadMutation = useMutation({
    mutationFn: () => reportsApi.markAsRead({ mark_all: true }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['activities'] });
      toast({
        title: 'Marked as Read',
        description: `${res.data.marked_count} activities marked as read`,
      });
    },
  });

  const activities = data?.activities ?? [];
  const totalCount = data?.total ?? 0;
  const totalPages = data?.total_pages ?? 1;
  const unreadCount = data?.unread_count ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Activity className="h-8 w-8 text-emerald-500" />
            Activity Feed
          </h1>
          <p className="text-muted-foreground">
            Timeline of all account activities and notifications
          </p>
        </div>
        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <Badge variant="secondary" className="gap-1">
              <Bell className="h-3 w-3" />
              {unreadCount} unread
            </Badge>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => markAllReadMutation.mutate()}
            disabled={markAllReadMutation.isPending || unreadCount === 0}
          >
            <CheckCheck className="h-4 w-4 mr-2" />
            Mark All Read
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <Select value={category} onValueChange={(v) => {
              setCategory(v as ActivityCategory | 'ALL');
              setPage(1);
            }}>
              <SelectTrigger className="w-[160px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CATEGORY_OPTIONS.map((c) => (
                  <SelectItem key={c.value} value={c.value}>
                    {c.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={severity} onValueChange={(v) => {
              setSeverity(v as ActivitySeverity | 'ALL');
              setPage(1);
            }}>
              <SelectTrigger className="w-[140px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SEVERITY_OPTIONS.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={readFilter} onValueChange={(v) => {
              setReadFilter(v as 'ALL' | 'unread' | 'read');
              setPage(1);
            }}>
              <SelectTrigger className="w-[120px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All</SelectItem>
                <SelectItem value="unread">Unread</SelectItem>
                <SelectItem value="read">Read</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Activity Timeline */}
      <Card>
        <CardHeader>
          <CardTitle>Activities ({totalCount})</CardTitle>
          <CardDescription>Recent account activities and system events</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="flex items-start gap-4">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-3 w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          ) : activities.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              No activities found
            </p>
          ) : (
            <>
              <div className="space-y-4">
                {activities.map((activity) => {
                  const Icon = getCategoryIcon(activity.category);
                  return (
                    <div
                      key={activity.id}
                      className={cn(
                        "flex items-start gap-4 p-4 rounded-lg border transition-colors",
                        !activity.is_read && "bg-muted/30 border-primary/20"
                      )}
                    >
                      <div className={cn(
                        "flex h-10 w-10 shrink-0 items-center justify-center rounded-full",
                        getIconBg(activity.severity)
                      )}>
                        <Icon className={cn("h-5 w-5", getIconColor(activity.severity))} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <p className={cn(
                              "text-sm font-medium leading-tight",
                              !activity.is_read && "font-semibold"
                            )}>
                              {activity.title}
                            </p>
                            {activity.description && (
                              <p className="text-sm text-muted-foreground mt-1 truncate">
                                {activity.description}
                              </p>
                            )}
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <Badge
                              variant="outline"
                              className={getSeverityStyle(activity.severity)}
                            >
                              {activity.severity}
                            </Badge>
                            {!activity.is_read && (
                              <div className="h-2 w-2 rounded-full bg-primary" />
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                          <Badge variant="secondary" className="font-normal">
                            {activity.category}
                          </Badge>
                          <span>•</span>
                          <span>{activity.activity_type}</span>
                          <span>•</span>
                          <span>
                            {formatDistanceToNow(new Date(activity.created_at), { addSuffix: true })}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Pagination */}
              <div className="flex items-center justify-between mt-6">
                <p className="text-sm text-muted-foreground">
                  Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, totalCount)} of {totalCount}
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <span className="text-sm">Page {page} of {totalPages}</span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

