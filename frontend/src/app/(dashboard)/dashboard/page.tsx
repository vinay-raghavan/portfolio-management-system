'use client';

import { useQuery } from '@tanstack/react-query';
import { TrendingUp, TrendingDown, DollarSign, Briefcase } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { portfolioApi } from '@/lib/api';
import { formatCurrency, formatPercent } from '@/lib/utils';

export default function DashboardPage() {
  const { data: portfolio, isLoading } = useQuery({
    queryKey: ['portfolio'],
    queryFn: () => portfolioApi.getPortfolio().then((res) => res.data),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  const summary = portfolio?.summary;
  const positions = portfolio?.positions || [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Portfolio overview and performance</p>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Value</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(summary?.total_value || 0)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total P&L</CardTitle>
            {(summary?.total_pnl || 0) >= 0 ? (
              <TrendingUp className="h-4 w-4 text-profit" />
            ) : (
              <TrendingDown className="h-4 w-4 text-loss" />
            )}
          </CardHeader>
          <CardContent>
            <div
              className={`text-2xl font-bold ${
                (summary?.total_pnl || 0) >= 0 ? 'text-profit' : 'text-loss'
              }`}
            >
              {formatCurrency(summary?.total_pnl || 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              {formatPercent(summary?.total_pnl_pct || 0)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Positions</CardTitle>
            <Briefcase className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary?.positions_count || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cash Balance</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(summary?.cash_balance || 0)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Positions Table */}
      <Card>
        <CardHeader>
          <CardTitle>Positions</CardTitle>
        </CardHeader>
        <CardContent>
          {positions.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              No positions yet. Start trading to see your portfolio here.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-2">Symbol</th>
                    <th className="text-right py-3 px-2">Quantity</th>
                    <th className="text-right py-3 px-2">Avg Cost</th>
                    <th className="text-right py-3 px-2">Current</th>
                    <th className="text-right py-3 px-2">Value</th>
                    <th className="text-right py-3 px-2">P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((position: any) => (
                    <tr key={position.id} className="border-b last:border-0">
                      <td className="py-3 px-2 font-medium">{position.symbol}</td>
                      <td className="text-right py-3 px-2">{position.quantity}</td>
                      <td className="text-right py-3 px-2">
                        {formatCurrency(position.avg_cost)}
                      </td>
                      <td className="text-right py-3 px-2">
                        {formatCurrency(position.current_price || position.avg_cost)}
                      </td>
                      <td className="text-right py-3 px-2">
                        {formatCurrency(position.market_value || 0)}
                      </td>
                      <td
                        className={`text-right py-3 px-2 ${
                          (position.unrealized_pnl || 0) >= 0 ? 'text-profit' : 'text-loss'
                        }`}
                      >
                        {formatCurrency(position.unrealized_pnl || 0)}
                        <span className="text-xs ml-1">
                          ({formatPercent(position.unrealized_pnl_pct || 0)})
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

