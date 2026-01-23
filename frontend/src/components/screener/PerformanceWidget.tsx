'use client';

import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { TrendingUp, TrendingDown, Target, Award, BarChart3, Calendar } from 'lucide-react';
import { screenerApi, CategoryPerformanceStats } from '@/lib/api';
import { cn } from '@/lib/utils';

interface PerformanceWidgetProps {
  days?: number;
  compact?: boolean;
}

export function PerformanceWidget({ days = 30, compact = false }: PerformanceWidgetProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['screener-performance', days],
    queryFn: () => screenerApi.getPerformance(days),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-32" />
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || !data?.data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Screener Performance
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">Unable to load performance data</p>
        </CardContent>
      </Card>
    );
  }

  const stats = data.data;
  const formatPercent = (val: number | null) =>
    val !== null ? `${val >= 0 ? '+' : ''}${val.toFixed(2)}%` : '-';
  const formatWinRate = (val: number | null) =>
    val !== null ? `${val.toFixed(1)}%` : '-';

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Screener Performance
        </CardTitle>
        <CardDescription className="flex items-center gap-2">
          <Calendar className="h-3 w-3" />
          Last {days} days • {stats.total_recommendations} recommendations
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Overall Stats */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <StatCard
            label="1-Day Win Rate"
            value={formatWinRate(stats.overall_win_rate_1d)}
            subValue={formatPercent(stats.overall_avg_return_1d)}
            positive={stats.overall_avg_return_1d !== null && stats.overall_avg_return_1d > 0}
          />
          <StatCard
            label="1-Week Win Rate"
            value={formatWinRate(stats.overall_win_rate_1w)}
            subValue={formatPercent(stats.overall_avg_return_1w)}
            positive={stats.overall_avg_return_1w !== null && stats.overall_avg_return_1w > 0}
          />
          <StatCard
            label="1-Month Win Rate"
            value={formatWinRate(stats.overall_win_rate_1m)}
            subValue={formatPercent(stats.overall_avg_return_1m)}
            positive={stats.overall_avg_return_1m !== null && stats.overall_avg_return_1m > 0}
          />
        </div>

        {!compact && stats.categories.length > 0 && (
          <Tabs defaultValue={stats.categories[0]?.category || 'momentum'}>
            <TabsList className="mb-4">
              {stats.categories.map((cat) => (
                <TabsTrigger key={cat.category} value={cat.category} className="capitalize">
                  {cat.category}
                </TabsTrigger>
              ))}
            </TabsList>
            {stats.categories.map((cat) => (
              <TabsContent key={cat.category} value={cat.category}>
                <CategoryStats stats={cat} />
              </TabsContent>
            ))}
          </Tabs>
        )}
      </CardContent>
    </Card>
  );
}

function StatCard({
  label,
  value,
  subValue,
  positive,
}: {
  label: string;
  value: string;
  subValue?: string;
  positive?: boolean;
}) {
  return (
    <div className="rounded-lg border p-3 text-center">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
      {subValue && (
        <p className={cn('text-xs', positive ? 'text-green-600' : 'text-red-600')}>
          Avg: {subValue}
        </p>
      )}
    </div>
  );
}

function CategoryStats({ stats }: { stats: CategoryPerformanceStats }) {
  const formatPercent = (val: number | null) =>
    val !== null ? `${val >= 0 ? '+' : ''}${val.toFixed(2)}%` : '-';

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-4 text-sm">
        <div>
          <p className="text-muted-foreground">1D Win Rate</p>
          <p className="font-medium">{stats.win_rate_1d?.toFixed(1) || '-'}%</p>
        </div>
        <div>
          <p className="text-muted-foreground">1W Win Rate</p>
          <p className="font-medium">{stats.win_rate_1w?.toFixed(1) || '-'}%</p>
        </div>
        <div>
          <p className="text-muted-foreground">1M Win Rate</p>
          <p className="font-medium">{stats.win_rate_1m?.toFixed(1) || '-'}%</p>
        </div>
      </div>
      {(stats.best_pick_1d || stats.best_pick_1w || stats.best_pick_1m) && (
        <div className="border-t pt-4">
          <p className="text-xs text-muted-foreground mb-2 flex items-center gap-1">
            <Award className="h-3 w-3" /> Best Picks
          </p>
          <div className="flex flex-wrap gap-2">
            {stats.best_pick_1d && (
              <Badge variant="outline" className="text-xs">
                1D: {stats.best_pick_1d} {formatPercent(stats.best_return_1d)}
              </Badge>
            )}
            {stats.best_pick_1w && (
              <Badge variant="outline" className="text-xs">
                1W: {stats.best_pick_1w} {formatPercent(stats.best_return_1w)}
              </Badge>
            )}
            {stats.best_pick_1m && (
              <Badge variant="outline" className="text-xs">
                1M: {stats.best_pick_1m} {formatPercent(stats.best_return_1m)}
              </Badge>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

