'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { portfolioApi } from '@/lib/api';
import { formatCurrency, cn } from '@/lib/utils';

type TimeRange = '7d' | '30d' | '90d' | '1y';

const TIME_RANGES: { value: TimeRange; label: string; days: number }[] = [
  { value: '7d', label: '7D', days: 7 },
  { value: '30d', label: '1M', days: 30 },
  { value: '90d', label: '3M', days: 90 },
  { value: '1y', label: '1Y', days: 365 },
];

export function PerformanceChart() {
  const [timeRange, setTimeRange] = useState<TimeRange>('30d');
  const days = TIME_RANGES.find((r) => r.value === timeRange)?.days ?? 30;

  const { data, isLoading } = useQuery({
    queryKey: ['daily-pnl', days],
    queryFn: () => portfolioApi.getDailyPnL(days).then((res) => res.data),
  });

  const chartData = data?.records?.map((item) => ({
    date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    value: item.total_value,
    pnl: item.day_pnl,
  })) ?? [];

  const startValue = chartData[0]?.value ?? 0;
  const endValue = chartData[chartData.length - 1]?.value ?? 0;
  const totalChange = endValue - startValue;
  const totalChangePct = startValue > 0 ? (totalChange / startValue) * 100 : 0;
  const isPositive = totalChange >= 0;

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Portfolio Performance</CardTitle>
          <div className="flex gap-1">
            {TIME_RANGES.map((range) => (
              <div key={range.value} className="h-8 w-10 bg-muted rounded animate-pulse" />
            ))}
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center">
            <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Portfolio Performance</CardTitle>
          <p className={cn('text-sm mt-1', isPositive ? 'text-profit' : 'text-loss')}>
            {isPositive ? '+' : ''}{formatCurrency(totalChange)} ({totalChangePct.toFixed(2)}%)
          </p>
        </div>
        <div className="flex gap-1">
          {TIME_RANGES.map((range) => (
            <Button
              key={range.value}
              variant={timeRange === range.value ? 'default' : 'outline'}
              size="sm"
              onClick={() => setTimeRange(range.value)}
            >
              {range.label}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <p className="text-muted-foreground text-center py-8">
            No performance data available
          </p>
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value) => formatCurrency(value)}
                  width={80}
                />
                <Tooltip
                  formatter={(value: number) => [formatCurrency(value), 'Value']}
                  labelFormatter={(label) => label}
                />
                <ReferenceLine y={startValue} stroke="#888" strokeDasharray="3 3" />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={isPositive ? 'hsl(var(--profit))' : 'hsl(var(--loss))'}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

