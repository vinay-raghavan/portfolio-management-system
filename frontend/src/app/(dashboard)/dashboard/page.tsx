'use client';

import { useQuery } from '@tanstack/react-query';
import { portfolioApi } from '@/lib/api';
import {
  PortfolioSummary,
  TopMovers,
  RecentTrades,
  MarketOverview,
  AlgoSummary,
  FundsSummary,
  RecommendationsWidget,
  TotalAccountValue,
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
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">Portfolio overview and performance</p>
        </div>
        <TotalAccountValue />
      </div>

      {/* Portfolio Summary Cards */}
      <PortfolioSummary summary={summary} isLoading={isLoading} />

      {/* Top Movers */}
      <TopMovers positions={positions} isLoading={isLoading} />

      {/* Funds, Algo Summary and Market Overview */}
      <div className="grid gap-4 md:grid-cols-3">
        <FundsSummary />
        <AlgoSummary />
        <MarketOverview />
      </div>

      {/* Daily Recommendations */}
      <RecommendationsWidget />

      {/* Recent Trades */}
      <RecentTrades limit={5} />
    </div>
  );
}

