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
import { algoApi } from '@/lib/api';
import { useCurrency } from '@/hooks';
import { useToast } from '@/components/ui/use-toast';
import { StrategyDialog, ExecutionHistory, SafetyStatus } from '@/components/algo';
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
  const [historyOpen, setHistoryOpen] = useState(false);
  const [safetyOpen, setSafetyOpen] = useState(false);
  const [editingStrategy, setEditingStrategy] = useState<AlgoStrategy | null>(null);

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
        <div className="flex items-center gap-4">
          {/* Universe Management */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() => seedUniversesMutation.mutate()}
              disabled={seedUniversesMutation.isPending || refreshUniversesMutation.isPending}
            >
              {seedUniversesMutation.isPending ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Database className="h-4 w-4" />
              )}
              Seed Universes
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() => refreshUniversesMutation.mutate()}
              disabled={seedUniversesMutation.isPending || refreshUniversesMutation.isPending}
            >
              {refreshUniversesMutation.isPending ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              Refresh
            </Button>
          </div>
          {/* Kill Switch */}
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant={killSwitchStatus?.is_active ? 'default' : 'destructive'}
                size="lg"
                className="gap-2"
              >
                <Power className="h-5 w-5" />
                {killSwitchStatus?.is_active ? 'Kill Switch ON' : 'Emergency Stop'}
              </Button>
            </AlertDialogTrigger>
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
      <div className="grid gap-4 md:grid-cols-4">
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
            {totalPnL >= 0 ? (
              <TrendingUp className="h-4 w-4 text-green-500" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-500" />
            )}
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${totalPnL >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {formatPrice(totalPnL)}
            </div>
            <p className="text-xs text-muted-foreground">All strategies combined</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Trades</CardTitle>
            <Bot className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalTrades}</div>
            <p className="text-xs text-muted-foreground">Executed by algo</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{winRate.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              {strategies?.reduce((sum, s) => sum + s.winning_trades, 0) ?? 0} winning trades
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Strategies Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Strategies</CardTitle>
              <CardDescription>Manage your automated trading strategies</CardDescription>
            </div>
            <Button className="gap-2" onClick={() => { setEditingStrategy(null); setDialogOpen(true); }}>
              <Plus className="h-4 w-4" />
              New Strategy
            </Button>
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
            <Table>
              <TableHeader>
                <TableRow>
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

                  return (
                  <TableRow key={strategy.id}>
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
                    <TableCell className="text-right">{strategy.total_trades}</TableCell>
                    <TableCell className="text-right">
                      {strategy.total_trades > 0
                        ? ((strategy.winning_trades / strategy.total_trades) * 100).toFixed(1)
                        : 0}%
                    </TableCell>
                    <TableCell className={`text-right ${strategy.total_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {formatPrice(strategy.total_pnl)}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {strategy.last_run_at
                        ? new Date(strategy.last_run_at).toLocaleString()
                        : 'Never'}
                    </TableCell>
                    <TableCell className="text-center">
                      <Switch
                        checked={strategy.status === 'ACTIVE'}
                        onCheckedChange={() => handleToggleStrategy(strategy)}
                        disabled={killSwitchStatus?.is_active || enableMutation.isPending || disableMutation.isPending}
                      />
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => triggerMutation.mutate(strategy.id)}
                          disabled={strategy.status !== 'ACTIVE' || triggerMutation.isPending}
                          title="Run Now"
                        >
                          <Play className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => { setSelectedStrategy(strategy); setHistoryOpen(true); }}
                          title="View History"
                        >
                          <Clock className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => { setSelectedStrategy(strategy); setSafetyOpen(true); }}
                          title="Safety Controls"
                        >
                          <Shield className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Strategy Dialog */}
      <StrategyDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        strategy={editingStrategy}
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
    </div>
  );
}
