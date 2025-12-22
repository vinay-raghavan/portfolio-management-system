'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { portfolioApi } from '@/lib/api';
import { exportPositionsToCSV, exportTradesToCSV } from '@/lib/export';
import { PortfolioSummary } from '@/components/dashboard';
import {
  PositionsTable,
  TradeHistory,
  SectorAllocation,
  PerformanceChart,
  PortfolioSelector,
  PortfolioDialog,
} from '@/components/portfolio';
import { usePortfolioStore } from '@/store';
import type { PortfolioInfo } from '@/types';

export default function PortfolioPage() {
  const [activeTab, setActiveTab] = useState('positions');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingPortfolio, setEditingPortfolio] = useState<PortfolioInfo | null>(null);
  const { selectedPortfolioId } = usePortfolioStore();

  // Fetch portfolio data based on selection
  const { data: portfolio, isLoading } = useQuery({
    queryKey: ['portfolio', selectedPortfolioId],
    queryFn: () => {
      if (selectedPortfolioId) {
        return portfolioApi.getPortfolioDetail(selectedPortfolioId).then((res) => res.data);
      }
      return portfolioApi.getPortfolio().then((res) => res.data);
    },
    refetchInterval: 30000,
  });

  const { data: tradesData } = useQuery({
    queryKey: ['trades', 'all'],
    queryFn: () => portfolioApi.getTrades(1, 1000).then((res) => res.data),
    enabled: activeTab === 'history',
  });

  const summary = portfolio?.summary;
  const positions = portfolio?.positions ?? [];

  const handleExportPositions = () => {
    exportPositionsToCSV(positions);
  };

  const handleExportTrades = () => {
    if (tradesData?.trades) {
      exportTradesToCSV(tradesData.trades);
    }
  };

  const handleCreateClick = () => {
    setEditingPortfolio(null);
    setDialogOpen(true);
  };

  const handleManageClick = (portfolio: PortfolioInfo) => {
    setEditingPortfolio(portfolio);
    setDialogOpen(true);
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold">Portfolio</h1>
            <p className="text-muted-foreground">Manage your positions and view trade history</p>
          </div>
          <PortfolioSelector
            onCreateClick={handleCreateClick}
            onManageClick={handleManageClick}
          />
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleExportPositions}>
            <Download className="h-4 w-4 mr-2" />
            Export Positions
          </Button>
          <Button variant="outline" size="sm" onClick={handleExportTrades}>
            <Download className="h-4 w-4 mr-2" />
            Export Trades
          </Button>
        </div>
      </div>

      <PortfolioDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        portfolio={editingPortfolio}
      />

      {/* Portfolio Summary */}
      <PortfolioSummary summary={summary} isLoading={isLoading} />

      {/* Charts Row */}
      <div className="grid gap-4 md:grid-cols-2">
        <PerformanceChart />
        <SectorAllocation positions={positions} isLoading={isLoading} />
      </div>

      {/* Tabs for Positions and Trade History */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="positions">Positions</TabsTrigger>
          <TabsTrigger value="history">Trade History</TabsTrigger>
        </TabsList>
        <TabsContent value="positions" className="mt-4">
          <PositionsTable positions={positions} isLoading={isLoading} />
        </TabsContent>
        <TabsContent value="history" className="mt-4">
          <TradeHistory pageSize={20} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

