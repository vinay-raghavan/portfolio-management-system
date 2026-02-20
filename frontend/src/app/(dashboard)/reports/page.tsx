'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import {
  FileBarChart,
  Receipt,
  TrendingDown,
  TrendingUp,
  FileText,
  Activity,
  ArrowUpRight,
  CheckCircle,
  XCircle,
  Wallet,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { reportsApi, portfolioApi } from '@/lib/api';
import { useCurrency } from '@/hooks/useCurrency';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';

export default function ReportsOverviewPage() {
  const { format: formatCurrency } = useCurrency();

  // Fetch recent activities
  const { data: activityData, isLoading: activityLoading } = useQuery({
    queryKey: ['reports', 'activities', 'recent'],
    queryFn: () => reportsApi.getActivities({ page_size: 5 }).then((res) => res.data),
  });

  // Fetch API stats
  const { data: apiStats, isLoading: statsLoading } = useQuery({
    queryKey: ['reports', 'api-stats'],
    queryFn: () => reportsApi.getAPIStats().then((res) => res.data),
  });

  // Fetch gains summary for current FY
  const { data: gainsSummary, isLoading: gainsLoading } = useQuery({
    queryKey: ['reports', 'gains-summary'],
    queryFn: () => reportsApi.getGainsSummary().then((res) => res.data),
  });

  // Fetch funds for account balance
  const { data: funds, isLoading: fundsLoading } = useQuery({
    queryKey: ['funds'],
    queryFn: () => portfolioApi.getFunds().then((res) => res.data),
  });

  // Calculate overall API health
  const overallSuccessRate = apiStats?.stats?.length
    ? apiStats.stats.reduce((acc, s) => acc + s.success_rate, 0) / apiStats.stats.length
    : 0;

  const reportCards = [
    {
      title: 'Account Statement',
      description: 'Transaction ledger with filters and export',
      href: '/reports/statement',
      icon: Receipt,
      color: 'text-blue-500',
    },
    {
      title: 'Capital Gains',
      description: 'Tax report with STCG/LTCG breakdown',
      href: '/reports/gains',
      icon: TrendingDown,
      color: 'text-amber-500',
    },
    {
      title: 'API Logs',
      description: 'Broker API call history and debugging',
      href: '/reports/api-logs',
      icon: FileText,
      color: 'text-purple-500',
    },
    {
      title: 'Activity Feed',
      description: 'All account activities and notifications',
      href: '/reports/activity',
      icon: Activity,
      color: 'text-emerald-500',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <FileBarChart className="h-8 w-8 text-primary" />
          Reports
        </h1>
        <p className="text-muted-foreground">
          Account statements, tax reports, and activity logs
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        {/* Account Balance */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Wallet className="h-4 w-4 text-emerald-500" />
              Account Balance
            </CardTitle>
          </CardHeader>
          <CardContent>
            {fundsLoading ? (
              <Skeleton className="h-8 w-28" />
            ) : (
              <p className="text-2xl font-bold">
                {formatCurrency(funds?.total_balance ?? 0)}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Net Gains */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              {(gainsSummary?.net_gain_loss ?? 0) >= 0 ? (
                <TrendingUp className="h-4 w-4 text-emerald-500" />
              ) : (
                <TrendingDown className="h-4 w-4 text-red-500" />
              )}
              Net Gains (FY)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {gainsLoading ? (
              <Skeleton className="h-8 w-28" />
            ) : (
              <p className={cn(
                "text-2xl font-bold",
                (gainsSummary?.net_gain_loss ?? 0) >= 0 ? "text-emerald-600" : "text-red-600"
              )}>
                {formatCurrency(gainsSummary?.net_gain_loss ?? 0)}
              </p>
            )}
          </CardContent>
        </Card>

        {/* API Health */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              {overallSuccessRate >= 90 ? (
                <CheckCircle className="h-4 w-4 text-emerald-500" />
              ) : (
                <XCircle className="h-4 w-4 text-amber-500" />
              )}
              API Health
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <p className={cn(
                "text-2xl font-bold",
                overallSuccessRate >= 90 ? "text-emerald-600" : "text-amber-600"
              )}>
                {overallSuccessRate.toFixed(1)}%
              </p>
            )}
          </CardContent>
        </Card>

        {/* Unread Activities */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Activity className="h-4 w-4 text-blue-500" />
              Unread Activities
            </CardTitle>
          </CardHeader>
          <CardContent>
            {activityLoading ? (
              <Skeleton className="h-8 w-12" />
            ) : (
              <p className="text-2xl font-bold">
                {activityData?.unread_count ?? 0}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Report Cards Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {reportCards.map((card) => (
          <Card key={card.href} className="hover:border-primary transition-colors">
            <Link href={card.href} className="block">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <card.icon className={cn("h-5 w-5", card.color)} />
                  {card.title}
                </CardTitle>
                <CardDescription>{card.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="ghost" size="sm" className="h-6 px-2 text-xs">
                  View Report
                  <ArrowUpRight className="h-3 w-3 ml-1" />
                </Button>
              </CardContent>
            </Link>
          </Card>
        ))}
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Latest account activities</CardDescription>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link href="/reports/activity">
              View All
              <ArrowUpRight className="h-4 w-4 ml-1" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          {activityLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-3">
                  <Skeleton className="h-8 w-8 rounded-full" />
                  <div className="flex-1">
                    <Skeleton className="h-4 w-32 mb-1" />
                    <Skeleton className="h-3 w-24" />
                  </div>
                </div>
              ))}
            </div>
          ) : activityData?.activities?.length === 0 ? (
            <p className="text-muted-foreground text-center py-4">
              No recent activities
            </p>
          ) : (
            <div className="space-y-3">
              {activityData?.activities?.slice(0, 5).map((activity) => (
                <div
                  key={activity.id}
                  className="flex items-start gap-3 p-2 rounded-md hover:bg-muted/50"
                >
                  <div className={cn(
                    "p-2 rounded-full",
                    activity.severity === 'critical' ? 'bg-red-500/10' :
                    activity.severity === 'error' ? 'bg-red-500/10' :
                    activity.severity === 'warning' ? 'bg-amber-500/10' :
                    'bg-blue-500/10'
                  )}>
                    <Activity className={cn(
                      "h-4 w-4",
                      activity.severity === 'critical' ? 'text-red-500' :
                      activity.severity === 'error' ? 'text-red-500' :
                      activity.severity === 'warning' ? 'text-amber-500' :
                      'text-blue-500'
                    )} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-sm truncate">
                        {activity.title}
                      </p>
                      {!activity.is_read && (
                        <Badge variant="secondary" className="h-4 text-xs">
                          New
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground truncate">
                      {activity.description}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatDistanceToNow(new Date(activity.created_at), { addSuffix: true })}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

