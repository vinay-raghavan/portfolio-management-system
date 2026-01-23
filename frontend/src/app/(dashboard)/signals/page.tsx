'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Filter,
  Clock,
  Target,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Info,
  ShoppingCart,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { signalsApi, Signal } from '@/lib/api';
import { formatPercent, cn } from '@/lib/utils';
import { useCurrency } from '@/hooks';
import { useTradingStore } from '@/store';

const STATUS_COLORS: Record<string, string> = {
  ACTIVE: 'bg-green-500/10 text-green-500 border-green-500/20',
  PENDING: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
  EXECUTED: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  EXPIRED: 'bg-gray-500/10 text-gray-500 border-gray-500/20',
  CANCELLED: 'bg-red-500/10 text-red-500 border-red-500/20',
};

export default function SignalsPage() {
  const { format: formatPrice } = useCurrency();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [symbolFilter, setSymbolFilter] = useState('');
  const [generateSymbols, setGenerateSymbols] = useState('');
  const [selectedStrategy, setSelectedStrategy] = useState<string>('all');
  const [selectedTimeframe, setSelectedTimeframe] = useState<string>('1d');
  const [expandedSignals, setExpandedSignals] = useState<Set<string>>(new Set());

  const toggleExpanded = (signalId: string) => {
    setExpandedSignals((prev) => {
      const next = new Set(prev);
      if (next.has(signalId)) {
        next.delete(signalId);
      } else {
        next.add(signalId);
      }
      return next;
    });
  };

  // Trade from signal - opens order form pre-filled with signal data
  const handleTradeFromSignal = (signal: Signal, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent row expansion
    const { openModal } = useTradingStore.getState();
    openModal({
      symbol: signal.symbol,
      side: signal.signal_type === 'BUY' ? 'BUY' : 'SELL',
      orderType: signal.entry_price ? 'LIMIT' : 'MARKET',
      price: signal.entry_price ?? null,
      stopLoss: signal.stop_loss ?? null,
      takeProfit: signal.take_profit ?? null,
      quantity: 1,
    });
  };

  const { data: signalsData, isLoading } = useQuery({
    queryKey: ['signals', statusFilter, symbolFilter],
    queryFn: () =>
      signalsApi
        .getSignals(statusFilter || undefined, symbolFilter || undefined)
        .then((res) => res.data),
  });

  const { data: strategiesData } = useQuery({
    queryKey: ['signal-strategies'],
    queryFn: () => signalsApi.getStrategies().then((res) => res.data),
  });

  const strategies = strategiesData?.strategies || [];

  const generateMutation = useMutation({
    mutationFn: (params: { symbols: string[]; strategy_name?: string; timeframe?: string }) =>
      signalsApi.generateSignals(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['signals'] });
      setGenerateSymbols('');
    },
  });

  const handleGenerate = () => {
    const symbols = generateSymbols
      .split(',')
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean);
    if (symbols.length > 0) {
      generateMutation.mutate({
        symbols,
        strategy_name: selectedStrategy === 'all' ? undefined : selectedStrategy,
        timeframe: selectedTimeframe,
      });
    }
  };

  const signals = signalsData?.signals || [];

  const getSignalIcon = (type: string) => {
    switch (type) {
      case 'BUY':
        return <TrendingUp className="h-4 w-4 text-profit" />;
      case 'SELL':
        return <TrendingDown className="h-4 w-4 text-loss" />;
      default:
        return <Minus className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Trading Signals</h1>
          <p className="text-muted-foreground">
            AI-generated trading signals from multiple strategies
          </p>
        </div>
      </div>

      {/* Generate Signals Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Generate Signals</CardTitle>
          <CardDescription>
            Enter symbols to generate trading signals using all available strategies
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-4">
            <Input
              placeholder="Enter symbols (e.g., RELIANCE, TCS, INFY)"
              value={generateSymbols}
              onChange={(e) => setGenerateSymbols(e.target.value)}
              className="flex-1"
            />
          </div>
          <div className="flex gap-4 items-center">
            <Select value={selectedStrategy} onValueChange={setSelectedStrategy}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="All Strategies" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Strategies</SelectItem>
                {strategies.map((s) => (
                  <SelectItem key={s.name} value={s.name}>
                    {s.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={selectedTimeframe} onValueChange={setSelectedTimeframe}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Timeframe" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="5m">5 Minutes</SelectItem>
                <SelectItem value="15m">15 Minutes</SelectItem>
                <SelectItem value="1h">1 Hour</SelectItem>
                <SelectItem value="1d">1 Day</SelectItem>
              </SelectContent>
            </Select>
            <Button
              onClick={handleGenerate}
              disabled={generateMutation.isPending || !generateSymbols.trim()}
            >
              {generateMutation.isPending ? (
                <RefreshCw className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Target className="h-4 w-4 mr-2" />
              )}
              Generate Signals
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Filters */}
      <div className="flex gap-4 items-center">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Filters:</span>
        </div>
        <Select value={statusFilter || 'all'} onValueChange={(val) => setStatusFilter(val === 'all' ? '' : val)}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All Statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="ACTIVE">Active</SelectItem>
            <SelectItem value="PENDING">Pending</SelectItem>
            <SelectItem value="EXECUTED">Executed</SelectItem>
            <SelectItem value="EXPIRED">Expired</SelectItem>
          </SelectContent>
        </Select>
        <Input
          placeholder="Filter by symbol..."
          value={symbolFilter}
          onChange={(e) => setSymbolFilter(e.target.value.toUpperCase())}
          className="w-40"
        />
      </div>

      {/* Signals Table */}
      <Card>
        <CardHeader>
          <CardTitle>Signals ({signals.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : signals.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <AlertTriangle className="h-8 w-8 mx-auto mb-2" />
              <p>No signals found. Generate some signals to get started.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8"></TableHead>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Signal</TableHead>
                  <TableHead>Strategy</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead>Entry Price</TableHead>
                  <TableHead>Stop Loss</TableHead>
                  <TableHead>Take Profit</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Generated</TableHead>
                  <TableHead className="w-24">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {signals.map((signal) => {
                  const isExpanded = expandedSignals.has(signal.id);
                  return (
                    <>
                      <TableRow
                        key={signal.id}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => toggleExpanded(signal.id)}
                      >
                        <TableCell className="w-8">
                          {isExpanded ? (
                            <ChevronDown className="h-4 w-4 text-muted-foreground" />
                          ) : (
                            <ChevronRight className="h-4 w-4 text-muted-foreground" />
                          )}
                        </TableCell>
                        <TableCell className="font-medium">{signal.symbol}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getSignalIcon(signal.signal_type)}
                            <span
                              className={cn(
                                'font-medium',
                                signal.signal_type === 'BUY' && 'text-profit',
                                signal.signal_type === 'SELL' && 'text-loss'
                              )}
                            >
                              {signal.signal_type}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{signal.strategy_name}</Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <div className="w-16 h-2 bg-muted rounded-full overflow-hidden">
                              <div
                                className={cn(
                                  'h-full rounded-full',
                                  signal.confidence * 100 >= 70
                                    ? 'bg-green-500'
                                    : signal.confidence * 100 >= 50
                                    ? 'bg-yellow-500'
                                    : 'bg-red-500'
                                )}
                                style={{ width: `${signal.confidence * 100}%` }}
                              />
                            </div>
                            <span className="text-sm">{(signal.confidence * 100).toFixed(0)}%</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          {signal.entry_price ? formatPrice(signal.entry_price) : '-'}
                        </TableCell>
                        <TableCell>
                          {signal.stop_loss ? (
                            <span className="text-loss">{formatPrice(signal.stop_loss)}</span>
                          ) : (
                            '-'
                          )}
                        </TableCell>
                        <TableCell>
                          {signal.take_profit ? (
                            <span className="text-profit">{formatPrice(signal.take_profit)}</span>
                          ) : (
                            '-'
                          )}
                        </TableCell>
                        <TableCell>
                          <Badge className={STATUS_COLORS[signal.status] || ''}>
                            {signal.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1 text-sm text-muted-foreground">
                            <Clock className="h-3 w-3" />
                            {formatDate(signal.generated_at)}
                          </div>
                        </TableCell>
                        <TableCell>
                          {signal.status === 'ACTIVE' && (
                            <Button
                              size="sm"
                              variant="outline"
                              className={cn(
                                'h-7 text-xs',
                                signal.signal_type === 'BUY'
                                  ? 'border-profit text-profit hover:bg-profit hover:text-white'
                                  : 'border-loss text-loss hover:bg-loss hover:text-white'
                              )}
                              onClick={(e) => handleTradeFromSignal(signal, e)}
                            >
                              <ShoppingCart className="h-3 w-3 mr-1" />
                              Trade
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                      {isExpanded && (
                        <TableRow key={`${signal.id}-details`} className="bg-muted/30">
                          <TableCell colSpan={11} className="p-4">
                            <div className="space-y-4">
                              {/* Notes Section */}
                              {signal.notes && (
                                <div className="flex items-start gap-2">
                                  <Info className="h-4 w-4 text-muted-foreground mt-0.5" />
                                  <div>
                                    <span className="text-sm font-medium">Analysis: </span>
                                    <span className="text-sm text-muted-foreground">{signal.notes}</span>
                                  </div>
                                </div>
                              )}

                              {/* Signal Details Grid */}
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <div className="space-y-1">
                                  <p className="text-xs text-muted-foreground">Timeframe</p>
                                  <p className="text-sm font-medium">{signal.timeframe || '-'}</p>
                                </div>
                                <div className="space-y-1">
                                  <p className="text-xs text-muted-foreground">Signal Strength</p>
                                  <p className="text-sm font-medium">{signal.strength ? `${(signal.strength * 100).toFixed(0)}%` : '-'}</p>
                                </div>
                                <div className="space-y-1">
                                  <p className="text-xs text-muted-foreground">Price at Signal</p>
                                  <p className="text-sm font-medium">{signal.price_at_signal ? formatPrice(signal.price_at_signal) : '-'}</p>
                                </div>
                                <div className="space-y-1">
                                  <p className="text-xs text-muted-foreground">Risk/Reward</p>
                                  <p className="text-sm font-medium">{signal.risk_reward_ratio ? `1:${signal.risk_reward_ratio.toFixed(1)}` : '-'}</p>
                                </div>
                              </div>

                              {/* Indicators Section */}
                              {signal.indicators && Object.keys(signal.indicators).length > 0 && (
                                <div>
                                  <p className="text-sm font-medium mb-2">Technical Indicators</p>
                                  <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                                    {Object.entries(signal.indicators).map(([key, value]) => (
                                      <div key={key} className="bg-background rounded-md p-2 border">
                                        <p className="text-xs text-muted-foreground capitalize">
                                          {key.replace(/_/g, ' ')}
                                        </p>
                                        <p className="text-sm font-mono">
                                          {typeof value === 'number'
                                            ? value.toFixed(2)
                                            : typeof value === 'boolean'
                                            ? value ? 'Yes' : 'No'
                                            : String(value)}
                                        </p>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Trade Action Button */}
                              {signal.status === 'ACTIVE' && (
                                <div className="flex items-center gap-4 pt-4 border-t">
                                  <Button
                                    className={cn(
                                      signal.signal_type === 'BUY'
                                        ? 'bg-profit hover:bg-profit/90'
                                        : 'bg-loss hover:bg-loss/90'
                                    )}
                                    onClick={(e) => handleTradeFromSignal(signal, e)}
                                  >
                                    <ShoppingCart className="h-4 w-4 mr-2" />
                                    Place {signal.signal_type} Order
                                  </Button>
                                  <span className="text-sm text-muted-foreground">
                                    Opens order form pre-filled with signal data
                                  </span>
                                </div>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

