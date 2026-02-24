'use client';

import { useQuery } from '@tanstack/react-query';
import { portfolioApi } from '@/lib/api';
import {
  PortfolioSummary,
  TopMovers,
  RecentTrades,
  MarketOverview,
  FundsSummary,
  RecommendationsCarousel,
  TotalAccountValue,
  AlgoCarousel,
} from '@/components/dashboard';
import { SectorHeatmap } from '@/components/research';

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

      {/* Funds, Algo Carousel (Summary + Pending Trades) and Market Overview */}
      <div className="grid gap-4 md:grid-cols-3">
        <FundsSummary />
        <AlgoCarousel />
        <MarketOverview />
      </div>

      {/* Recommendations, Sector Heatmap & Recent Trades */}
      <div className="grid gap-4 md:grid-cols-3">
        <RecommendationsCarousel />
        <SectorHeatmap compact />
        <RecentTrades limit={4} />
      </div>
    </div>
  );
}

