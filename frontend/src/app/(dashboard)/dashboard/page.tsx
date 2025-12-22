'use client';

import { useQuery } from '@tanstack/react-query';
import { portfolioApi } from '@/lib/api';
import {
  PortfolioSummary,
  TopMovers,
  RecentTrades,
  MarketOverview,
} from '@/components/dashboard';

export default function DashboardPage() {
  const { data: portfolio, isLoading } = useQuery({
    queryKey: ['portfolio'],
    queryFn: () => portfolioApi.getPortfolio().then((res) => res.data),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const summary = portfolio?.summary;
  const positions = portfolio?.positions ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Portfolio overview and performance</p>
      </div>

      {/* Portfolio Summary Cards */}
      <PortfolioSummary summary={summary} isLoading={isLoading} />

      {/* Top Movers */}
      <TopMovers positions={positions} isLoading={isLoading} />

      {/* Recent Trades and Market Overview */}
      <div className="grid gap-4 md:grid-cols-2">
        <RecentTrades limit={5} />
        <MarketOverview />
      </div>
    </div>
  );
}

