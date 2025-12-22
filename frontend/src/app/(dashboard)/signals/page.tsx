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

  const { data: signalsData, isLoading } = useQuery({
    queryKey: ['signals', statusFilter, symbolFilter],
    queryFn: () =>
      signalsApi
        .getSignals(statusFilter || undefined, symbolFilter || undefined)
        .then((res) => res.data),
  });

  const { data: strategies } = useQuery({
    queryKey: ['signal-strategies'],
    queryFn: () => signalsApi.getStrategies().then((res) => res.data),
  });

  const generateMutation = useMutation({
    mutationFn: (symbols: string[]) =>
      signalsApi.generateSignals({ symbols }),
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
      generateMutation.mutate(symbols);
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
        <CardContent>
          <div className="flex gap-4">
            <Input
              placeholder="Enter symbols (e.g., AAPL, MSFT, GOOGL)"
              value={generateSymbols}
              onChange={(e) => setGenerateSymbols(e.target.value)}
              className="flex-1"
            />
            <Button
              onClick={handleGenerate}
              disabled={generateMutation.isPending || !generateSymbols.trim()}
            >
              {generateMutation.isPending ? (
                <RefreshCw className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Target className="h-4 w-4 mr-2" />
              )}
              Generate
            </Button>
          </div>
          {strategies && strategies.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="text-sm text-muted-foreground">Available strategies:</span>
              {strategies.map((s) => (
                <Badge key={s.name} variant="outline">
                  {s.name}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Filters */}
      <div className="flex gap-4 items-center">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Filters:</span>
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All Statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Statuses</SelectItem>
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
                  <TableHead>Symbol</TableHead>
                  <TableHead>Signal</TableHead>
                  <TableHead>Strategy</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead>Entry Price</TableHead>
                  <TableHead>Stop Loss</TableHead>
                  <TableHead>Take Profit</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Generated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {signals.map((signal) => (
                  <TableRow key={signal.id}>
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
                              signal.confidence >= 70
                                ? 'bg-green-500'
                                : signal.confidence >= 50
                                ? 'bg-yellow-500'
                                : 'bg-red-500'
                            )}
                            style={{ width: `${signal.confidence}%` }}
                          />
                        </div>
                        <span className="text-sm">{signal.confidence.toFixed(0)}%</span>
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
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

