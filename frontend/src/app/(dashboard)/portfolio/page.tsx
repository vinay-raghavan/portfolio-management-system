'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Download, XCircle, Loader2 } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { useToast } from '@/components/ui/use-toast';
import { portfolioApi, tradingApi } from '@/lib/api';
import { exportPositionsToCSV, exportTradesToCSV } from '@/lib/export';
import { PortfolioSummary } from '@/components/dashboard';
import {
  PositionsTable,
  TradeHistory,
  SectorAllocation,
  PerformanceChart,
  PortfolioSelector,
  PortfolioDialog,
  FundsManagement,
} from '@/components/portfolio';
import { usePortfolioStore } from '@/store';
import { useCurrency } from '@/hooks';
import type { PortfolioInfo, Position } from '@/types';

export default function PortfolioPage() {
  const [activeTab, setActiveTab] = useState('positions');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingPortfolio, setEditingPortfolio] = useState<PortfolioInfo | null>(null);
  const [showSquareOffAllConfirm, setShowSquareOffAllConfirm] = useState(false);
  const { selectedPortfolioId } = usePortfolioStore();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { format: formatCurrency } = useCurrency();

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

  // Calculate total unrealized P&L for all positions
  const totalUnrealizedPnL = positions.reduce(
    (sum, pos) => sum + (pos.unrealized_pnl ?? 0),
    0
  );

  // Square off all positions mutation
  const squareOffAllMutation = useMutation({
    mutationFn: async (positionsToClose: Position[]) => {
      const results = [];
      for (const position of positionsToClose) {
        try {
          const result = await tradingApi.createOrder({
            symbol: position.symbol,
            order_type: 'MARKET',
            side: 'SELL',
            quantity: position.quantity,
            product_type: 'DELIVERY',
          });
          results.push({ symbol: position.symbol, success: true, result });
        } catch (error: any) {
          results.push({ symbol: position.symbol, success: false, error });
        }
      }
      return results;
    },
    onSuccess: (results) => {
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      const successCount = results.filter((r) => r.success).length;
      const failCount = results.filter((r) => !r.success).length;

      if (failCount === 0) {
        toast({
          title: 'All Positions Squared Off',
          description: `Successfully placed ${successCount} market sell orders`,
        });
      } else {
        toast({
          title: 'Square Off Partially Complete',
          description: `${successCount} orders placed, ${failCount} failed`,
          variant: 'warning',
        });
      }
      setShowSquareOffAllConfirm(false);
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to square off positions',
        description: error?.message || 'Unknown error',
        variant: 'destructive',
      });
    },
  });

  const handleSquareOffAll = async () => {
    if (positions.length === 0) return;
    await squareOffAllMutation.mutateAsync(positions);
  };

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
          {positions.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              className="border-loss text-loss hover:bg-loss hover:text-white"
              onClick={() => setShowSquareOffAllConfirm(true)}
              disabled={squareOffAllMutation.isPending}
            >
              {squareOffAllMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <XCircle className="h-4 w-4 mr-2" />
              )}
              Square Off All
            </Button>
          )}
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

      {/* Square Off All Confirmation Dialog */}
      <AlertDialog open={showSquareOffAllConfirm} onOpenChange={setShowSquareOffAllConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Square Off All Positions?</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div>
                <p>
                  This will place market sell orders for all {positions.length} position{positions.length !== 1 ? 's' : ''} in your portfolio.
                </p>
                <div className="mt-3 p-3 bg-muted rounded-md space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Total Positions:</span>
                    <span className="font-medium">{positions.length}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Unrealized P&L:</span>
                    <span className={`font-medium ${totalUnrealizedPnL >= 0 ? 'text-profit' : 'text-loss'}`}>
                      {formatCurrency(totalUnrealizedPnL)}
                    </span>
                  </div>
                </div>
                <p className="mt-3 text-sm text-muted-foreground">
                  This action cannot be undone.
                </p>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={squareOffAllMutation.isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleSquareOffAll}
              disabled={squareOffAllMutation.isPending}
              className="bg-loss text-white hover:bg-loss/90"
            >
              {squareOffAllMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <XCircle className="mr-2 h-4 w-4" />
              )}
              Square Off All ({positions.length})
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

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

      {/* Tabs for Positions, Trade History, and Funds */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="positions">Positions</TabsTrigger>
          <TabsTrigger value="history">Trade History</TabsTrigger>
          <TabsTrigger value="funds">Funds</TabsTrigger>
        </TabsList>
        <TabsContent value="positions" className="mt-4">
          <PositionsTable positions={positions} isLoading={isLoading} />
        </TabsContent>
        <TabsContent value="history" className="mt-4">
          <TradeHistory pageSize={20} />
        </TabsContent>
        <TabsContent value="funds" className="mt-4">
          <FundsManagement />
        </TabsContent>
      </Tabs>
    </div>
  );
}

