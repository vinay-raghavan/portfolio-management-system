'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Bot,
  Play,
  Pause,
  Plus,
  AlertTriangle,
  Power,
  TrendingUp,
  TrendingDown,
  Clock,
  Activity,
  Shield,
  RefreshCw,
  Database,
  ChevronDown,
  ChevronRight,
  Pencil,
  Trash2,
  Code2,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { algoApi, portfolioApi } from '@/lib/api';
import { useCurrency } from '@/hooks';
import { useToast } from '@/components/ui/use-toast';
import { StrategyDialog, StrategyDetails, ExecutionHistory, SafetyStatus, PnLDashboard, DSLStrategyBuilder } from '@/components/algo';
import { FundsSummary } from '@/components/dashboard';
import type { AlgoStrategy, StrategyStatus } from '@/types';

const statusColors: Record<StrategyStatus, string> = {
  ACTIVE: 'bg-green-500',
  DISABLED: 'bg-gray-500',
  PAUSED: 'bg-yellow-500',
  ERROR: 'bg-red-500',
  KILLED: 'bg-red-700',
};

const statusLabels: Record<StrategyStatus, string> = {
  ACTIVE: 'Active',
  DISABLED: 'Disabled',
  PAUSED: 'Paused',
  ERROR: 'Error',
  KILLED: 'Killed',
};

export default function AlgoTradingPage() {
  const { format: formatPrice } = useCurrency();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [selectedStrategy, setSelectedStrategy] = useState<AlgoStrategy | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dslDialogOpen, setDslDialogOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [safetyOpen, setSafetyOpen] = useState(false);
  const [editingStrategy, setEditingStrategy] = useState<AlgoStrategy | null>(null);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [strategyToDelete, setStrategyToDelete] = useState<AlgoStrategy | null>(null);

  // Fetch strategies
  const { data: strategies, isLoading } = useQuery({
    queryKey: ['algo-strategies'],
    queryFn: () => algoApi.getStrategies().then((res) => res.data),
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  // Fetch kill switch status
  const { data: killSwitchStatus } = useQuery({
    queryKey: ['kill-switch'],
    queryFn: () => algoApi.getKillSwitchStatus().then((res) => res.data),
    refetchInterval: 5000,
  });

  // Fetch P&L summary for enhanced cards
  const { data: pnlSummary } = useQuery({
    queryKey: ['algo-pnl-summary'],
    queryFn: () => algoApi.getPnLSummary().then((res) => res.data),
    refetchInterval: 30000,
  });

  // Fetch P&L by strategy for accurate trade counts
  const { data: pnlByStrategy } = useQuery({
    queryKey: ['algo-pnl-by-strategy'],
    queryFn: () => algoApi.getPnLByStrategy().then((res) => res.data),
    refetchInterval: 30000,
  });

  // Enable/disable mutations
  const enableMutation = useMutation({
    mutationFn: (id: string) => algoApi.enableStrategy(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['algo-strategies'] }),
  });

  const disableMutation = useMutation({
    mutationFn: (id: string) => algoApi.disableStrategy(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['algo-strategies'] }),
  });

  const triggerMutation = useMutation({
    mutationFn: (id: string) => algoApi.triggerStrategy(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['algo-strategies'] }),
  });

  const emergencyStopMutation = useMutation({
    mutationFn: () => algoApi.emergencyStop(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['algo-strategies'] });
      queryClient.invalidateQueries({ queryKey: ['kill-switch'] });
    },
  });

  const toggleKillSwitchMutation = useMutation({
    mutationFn: (activate: boolean) => algoApi.toggleKillSwitch(activate),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['kill-switch'] }),
  });

  const seedUniversesMutation = useMutation({
    mutationFn: () => algoApi.seedAllUniverses(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['universes'] });
      toast({
        title: 'Universes Seeded',
        description: `Created ${data.data.predefined_count} predefined and ${data.data.dynamic_count} dynamic universes`,
      });
    },
    onError: (error) => {
      toast({
        variant: 'destructive',
        title: 'Failed to Seed Universes',
        description: error instanceof Error ? error.message : 'Unknown error occurred',
      });
    },
  });

  const refreshUniversesMutation = useMutation({
    mutationFn: () => algoApi.refreshAllUniverses(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['universes'] });
      toast({
        title: 'Universes Refreshed',
        description: `Refreshed ${data.data.refreshed_count} dynamic universes`,
      });
    },
    onError: (error) => {
      toast({
        variant: 'destructive',
        title: 'Failed to Refresh Universes',
        description: error instanceof Error ? error.message : 'Unknown error occurred',
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => algoApi.deleteStrategy(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['algo-strategies'] });
      toast({
        title: 'Strategy Deleted',
        description: 'The strategy has been permanently deleted.',
      });
      setDeleteDialogOpen(false);
      setStrategyToDelete(null);
    },
    onError: (error) => {
      toast({
        variant: 'destructive',
        title: 'Failed to Delete Strategy',
        description: error instanceof Error ? error.message : 'Unknown error occurred',
      });
    },
  });

  // Calculate summary stats
  const activeCount = strategies?.filter((s) => s.status === 'ACTIVE').length ?? 0;
  const totalPnL = strategies?.reduce((sum, s) => sum + s.total_pnl, 0) ?? 0;
  const totalTrades = strategies?.reduce((sum, s) => sum + s.total_trades, 0) ?? 0;
  const winRate = strategies?.length
    ? (strategies.reduce((sum, s) => sum + s.winning_trades, 0) / Math.max(totalTrades, 1)) * 100
    : 0;

  const handleToggleStrategy = (strategy: AlgoStrategy) => {
    if (strategy.status === 'ACTIVE') {
      disableMutation.mutate(strategy.id);
    } else {
      enableMutation.mutate(strategy.id);
    }
  };

  const toggleRowExpanded = (strategyId: string) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(strategyId)) {
        next.delete(strategyId);
      } else {
        next.add(strategyId);
      }
      return next;
    });
  };

  const handleDeleteClick = (strategy: AlgoStrategy) => {
    setStrategyToDelete(strategy);
    setDeleteDialogOpen(true);
  };

  const handleEditClick = (strategy: AlgoStrategy) => {
    setEditingStrategy(strategy);
    setDialogOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Bot className="h-8 w-8" />
            Algo Trading
          </h1>
          <p className="text-muted-foreground">Automated strategy execution and monitoring</p>
        </div>
        <div className="flex items-center gap-2">
          <TooltipProvider delayDuration={0}>
            {/* Seed Universes */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => seedUniversesMutation.mutate()}
                  disabled={seedUniversesMutation.isPending || refreshUniversesMutation.isPending}
                >
                  {seedUniversesMutation.isPending ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    <Database className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>Seed Universes</TooltipContent>
            </Tooltip>
            {/* Refresh */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => refreshUniversesMutation.mutate()}
                  disabled={seedUniversesMutation.isPending || refreshUniversesMutation.isPending}
                >
                  {refreshUniversesMutation.isPending ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>Refresh</TooltipContent>
            </Tooltip>
            {/* Kill Switch */}
            <AlertDialog>
              <Tooltip>
                <TooltipTrigger asChild>
                  <AlertDialogTrigger asChild>
                    <Button
                      variant={killSwitchStatus?.is_active ? 'default' : 'destructive'}
                      size="icon"
                    >
                      <Power className="h-5 w-5" />
                    </Button>
                  </AlertDialogTrigger>
                </TooltipTrigger>
                <TooltipContent>
                  {killSwitchStatus?.is_active ? 'Kill Switch ON' : 'Emergency Stop'}
                </TooltipContent>
              </Tooltip>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle className="flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-destructive" />
                    {killSwitchStatus?.is_active ? 'Deactivate Kill Switch?' : 'Activate Emergency Stop?'}
                  </AlertDialogTitle>
                  <AlertDialogDescription>
                    {killSwitchStatus?.is_active
                      ? 'This will allow algo strategies to resume trading.'
                      : 'This will immediately stop all algo trading and disable all active strategies.'}
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => {
                      if (killSwitchStatus?.is_active) {
                        toggleKillSwitchMutation.mutate(false);
                      } else {
                        emergencyStopMutation.mutate();
                      }
                    }}
                    className={killSwitchStatus?.is_active ? '' : 'bg-destructive'}
                  >
                    {killSwitchStatus?.is_active ? 'Deactivate' : 'Activate Emergency Stop'}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </TooltipProvider>
        </div>
      </div>

      {/* Kill Switch Warning Banner */}
      {killSwitchStatus?.is_active && (
        <div className="bg-destructive/10 border border-destructive rounded-lg p-4 flex items-center gap-3">
          <AlertTriangle className="h-6 w-6 text-destructive" />
          <div>
            <p className="font-semibold text-destructive">Kill Switch Active</p>
            <p className="text-sm text-muted-foreground">
              All algo trading is disabled. Reason: {killSwitchStatus.reason || 'Manual activation'}
            </p>
          </div>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {/* Funds Summary */}
        <FundsSummary />

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Strategies</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activeCount}</div>
            <p className="text-xs text-muted-foreground">
              of {strategies?.length ?? 0} total
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total P&L</CardTitle>
            {(pnlSummary?.total_pnl ?? totalPnL) >= 0 ? (
              <TrendingUp className="h-4 w-4 text-green-500" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-500" />
            )}
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(pnlSummary?.total_pnl ?? totalPnL) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {formatPrice(pnlSummary?.total_pnl ?? totalPnL)}
            </div>
            <div className="flex gap-3 text-xs text-muted-foreground mt-1">
              <span className={pnlSummary?.total_realized_pnl && pnlSummary.total_realized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                Realized: {formatPrice(pnlSummary?.total_realized_pnl ?? 0)}
              </span>
              <span className={pnlSummary?.total_unrealized_pnl && pnlSummary.total_unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                Unrealized: {formatPrice(pnlSummary?.total_unrealized_pnl ?? 0)}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Trades</CardTitle>
            <Bot className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{pnlSummary?.total_trades ?? totalTrades}</div>
            <div className="flex gap-3 text-xs text-muted-foreground mt-1">
              <span className="text-green-600">{pnlSummary?.winning_trades ?? 0} wins</span>
              <span className="text-red-600">{pnlSummary?.losing_trades ?? 0} losses</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {pnlSummary?.win_rate !== undefined
                ? Number(pnlSummary.win_rate ?? 0).toFixed(1)
                : (winRate ?? 0).toFixed(1)}%
            </div>
            <div className="flex gap-3 text-xs text-muted-foreground mt-1">
              <span>{pnlSummary?.open_positions ?? 0} open positions</span>
              <span>{pnlSummary?.closed_positions ?? 0} closed</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* P&L Dashboard with Unrealized Positions and Profit Booking */}
      <PnLDashboard />

      {/* Strategies Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Strategies</CardTitle>
              <CardDescription>Manage your automated trading strategies</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" className="gap-2" onClick={() => setDslDialogOpen(true)}>
                <Code2 className="h-4 w-4" />
                Custom DSL
              </Button>
              <Button className="gap-2" onClick={() => { setEditingStrategy(null); setDialogOpen(true); }}>
                <Plus className="h-4 w-4" />
                New Strategy
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : strategies?.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No strategies configured yet</p>
              <p className="text-sm">Create your first algo trading strategy to get started</p>
            </div>
          ) : (
            <TooltipProvider>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8"></TableHead>
                  <TableHead>Strategy</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Schedule</TableHead>
                  <TableHead className="text-right">Trades</TableHead>
                  <TableHead className="text-right">Win Rate</TableHead>
                  <TableHead className="text-right">P&L</TableHead>
                  <TableHead>Last Run</TableHead>
                  <TableHead className="text-center">Enabled</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {strategies?.map((strategy) => {
                  // Determine if strategy is intraday based on type name
                  const intradayStrategies = ['orb', 'vwap_reversion', 'gap_go', 'twap', 'intraday_momentum'];
                  const isIntraday = intradayStrategies.includes(strategy.strategy_type);
                  const isCombined = strategy.strategy_type.includes('confluence') ||
                    strategy.strategy_type.includes('pullback') ||
                    strategy.strategy_type.includes('confirmation') ||
                    strategy.strategy_type.includes('momentum');
                  const isExpanded = expandedRows.has(strategy.id);

                  // Get P&L data for this strategy (based on closed positions)
                  const strategyPnL = pnlByStrategy?.strategies.find((s) => s.strategy_id === strategy.id);
                  const totalTrades = strategyPnL?.total_trades ?? 0;
                  const winningTrades = strategyPnL?.winning_trades ?? 0;
                  const winRate = totalTrades > 0 ? (winningTrades / totalTrades) * 100 : 0;

                  return (
                  <>
                  <TableRow key={strategy.id} className="cursor-pointer hover:bg-muted/50" onClick={() => toggleRowExpanded(strategy.id)}>
                    <TableCell className="w-8">
                      <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </Button>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-medium">{strategy.name}</p>
                        <div className="flex items-center gap-1.5">
                          <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ${
                            isIntraday
                              ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                              : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          }`}>
                            {isIntraday ? 'Intraday' : 'Swing'}
                          </span>
                          {isCombined && (
                            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200">
                              Combined
                            </span>
                          )}
                          <span className="text-xs text-muted-foreground">{strategy.strategy_type}</span>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={statusColors[strategy.status]}>
                        {statusLabels[strategy.status]}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1 text-sm">
                        <Clock className="h-3 w-3" />
                        {strategy.schedule_type}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">{totalTrades}</TableCell>
                    <TableCell className="text-right">
                      {winRate.toFixed(1)}%
                    </TableCell>
                    <TableCell className={`text-right ${(strategyPnL?.total_pnl ?? strategy.total_pnl) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {formatPrice(strategyPnL?.total_pnl ?? strategy.total_pnl)}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {strategy.last_run_at
                        ? new Date(strategy.last_run_at).toLocaleString()
                        : 'Never'}
                    </TableCell>
                    <TableCell className="text-center" onClick={(e) => e.stopPropagation()}>
                      <Switch
                        checked={strategy.status === 'ACTIVE'}
                        onCheckedChange={() => handleToggleStrategy(strategy)}
                        disabled={killSwitchStatus?.is_active || enableMutation.isPending || disableMutation.isPending}
                      />
                    </TableCell>
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center gap-0.5">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => triggerMutation.mutate(strategy.id)}
                              disabled={strategy.status !== 'ACTIVE' || triggerMutation.isPending}
                            >
                              <Play className="h-4 w-4" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>Run Now</TooltipContent>
                        </Tooltip>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => { setSelectedStrategy(strategy); setHistoryOpen(true); }}
                            >
                              <Clock className="h-4 w-4" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>History</TooltipContent>
                        </Tooltip>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => { setSelectedStrategy(strategy); setSafetyOpen(true); }}
                            >
                              <Shield className="h-4 w-4" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>Safety</TooltipContent>
                        </Tooltip>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => handleEditClick(strategy)}
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>Edit</TooltipContent>
                        </Tooltip>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-destructive hover:text-destructive"
                              onClick={() => handleDeleteClick(strategy)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>Delete</TooltipContent>
                        </Tooltip>
                      </div>
                    </TableCell>
                  </TableRow>
                  {isExpanded && (
                    <TableRow key={`${strategy.id}-details`}>
                      <TableCell colSpan={10} className="p-0">
                        <StrategyDetails strategy={strategy} />
                      </TableCell>
                    </TableRow>
                  )}
                  </>
                  );
                })}
              </TableBody>
            </Table>
            </TooltipProvider>
          )}
        </CardContent>
      </Card>

      {/* Strategy Dialog */}
      <StrategyDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        strategy={editingStrategy}
      />

      {/* DSL Strategy Builder */}
      <DSLStrategyBuilder
        open={dslDialogOpen}
        onOpenChange={setDslDialogOpen}
      />

      {/* Execution History Dialog */}
      <ExecutionHistory
        open={historyOpen}
        onOpenChange={setHistoryOpen}
        strategy={selectedStrategy}
      />

      {/* Safety Status Dialog */}
      <SafetyStatus
        open={safetyOpen}
        onOpenChange={setSafetyOpen}
        strategy={selectedStrategy}
      />

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <Trash2 className="h-5 w-5 text-destructive" />
              Delete Strategy?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <strong>{strategyToDelete?.name}</strong>?
              This action cannot be undone. All execution history and statistics for this
              strategy will be permanently deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setStrategyToDelete(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => strategyToDelete && deleteMutation.mutate(strategyToDelete.id)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete Strategy'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
