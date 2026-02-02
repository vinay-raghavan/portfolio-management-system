'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Clock, CheckCircle, XCircle, AlertCircle, Loader2, ChevronDown, ChevronRight, TrendingUp, TrendingDown } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { algoApi } from '@/lib/api';
import type { AlgoStrategy, ExecutionStatus, StrategyExecution } from '@/types';
import { cn } from '@/lib/utils';

interface ExecutionHistoryProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  strategy: AlgoStrategy | null;
}

const statusIcons: Record<ExecutionStatus, React.ReactNode> = {
  PENDING: <Clock className="h-4 w-4 text-yellow-500" />,
  RUNNING: <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />,
  COMPLETED: <CheckCircle className="h-4 w-4 text-green-500" />,
  FAILED: <XCircle className="h-4 w-4 text-red-500" />,
  CANCELLED: <AlertCircle className="h-4 w-4 text-gray-500" />,
};

const statusColors: Record<ExecutionStatus, string> = {
  PENDING: 'bg-yellow-500',
  RUNNING: 'bg-blue-500',
  COMPLETED: 'bg-green-500',
  FAILED: 'bg-red-500',
  CANCELLED: 'bg-gray-500',
};

function formatPrice(value: number | null): string {
  if (value === null) return '-';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
  }).format(value);
}

function ExecutionRow({ execution }: { execution: StrategyExecution }) {
  const [isOpen, setIsOpen] = useState(false);
  const hasOrders = execution.orders && execution.orders.length > 0;

  const formatDuration = (ms: number | null) => {
    if (!ms) return '-';
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  return (
    <React.Fragment>
      <TableRow
        className={cn('cursor-pointer hover:bg-muted/50', hasOrders && 'cursor-pointer')}
        onClick={() => hasOrders && setIsOpen(!isOpen)}
      >
        <TableCell className="w-8">
          {hasOrders ? (
            isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />
          ) : (
            <span className="w-4" />
          )}
        </TableCell>
        <TableCell>
          <div className="flex items-center gap-2">
            {statusIcons[execution.status]}
            <Badge className={statusColors[execution.status]}>
              {execution.status}
            </Badge>
          </div>
        </TableCell>
        <TableCell className="text-sm">
          {new Date(execution.started_at).toLocaleString()}
        </TableCell>
        <TableCell>{formatDuration(execution.duration_ms)}</TableCell>
        <TableCell className="text-right">{execution.symbols_analyzed}</TableCell>
        <TableCell className="text-right">{execution.signals_generated}</TableCell>
        <TableCell className="text-right">{execution.orders_placed}</TableCell>
        <TableCell className="text-right">
          <span className="text-green-500">{execution.orders_filled}</span>
          {execution.orders_rejected > 0 && (
            <span className="text-red-500 ml-1">/ {execution.orders_rejected} rej</span>
          )}
        </TableCell>
        <TableCell className="text-right">
          {execution.realized_pnl !== 0 && (
            <span className={execution.realized_pnl >= 0 ? 'text-green-500' : 'text-red-500'}>
              {formatPrice(execution.realized_pnl)}
            </span>
          )}
        </TableCell>
        <TableCell className="max-w-[150px] truncate text-sm text-red-500">
          {execution.error_message || '-'}
        </TableCell>
      </TableRow>
      {hasOrders && isOpen && (
        <TableRow className="bg-muted/30 hover:bg-muted/30">
          <TableCell colSpan={10} className="p-0">
              <div className="p-4 pl-12">
                <h4 className="text-sm font-medium mb-2">Order Details</h4>
                <Table>
                  <TableHeader>
                    <TableRow className="text-xs">
                      <TableHead>Symbol</TableHead>
                      <TableHead>Side</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead className="text-right">Qty</TableHead>
                      <TableHead className="text-right">Price</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Filled Qty</TableHead>
                      <TableHead className="text-right">Filled Price</TableHead>
                      <TableHead className="text-right">Value</TableHead>
                      <TableHead>Signal</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {execution.orders.map((order) => (
                      <TableRow key={order.id} className="text-xs">
                        <TableCell className="font-medium">{order.symbol}</TableCell>
                        <TableCell>
                          <Badge variant={order.side === 'BUY' ? 'default' : 'destructive'} className="text-xs">
                            {order.side === 'BUY' ? (
                              <TrendingUp className="h-3 w-3 mr-1" />
                            ) : (
                              <TrendingDown className="h-3 w-3 mr-1" />
                            )}
                            {order.side}
                          </Badge>
                        </TableCell>
                        <TableCell>{order.order_type}</TableCell>
                        <TableCell className="text-right">{order.quantity}</TableCell>
                        <TableCell className="text-right">{formatPrice(order.price)}</TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              order.order_status === 'FILLED' ? 'default' :
                              order.order_status === 'REJECTED' ? 'destructive' :
                              'secondary'
                            }
                            className="text-xs"
                          >
                            {order.order_status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">{order.filled_quantity}</TableCell>
                        <TableCell className="text-right">{formatPrice(order.filled_price)}</TableCell>
                        <TableCell className="text-right">{formatPrice(order.order_value)}</TableCell>
                        <TableCell>
                          {order.signal_type && (
                            <Badge variant="outline" className="text-xs">
                              {order.signal_type}
                              {order.signal_strength !== null && ` (${(order.signal_strength * 100).toFixed(0)}%)`}
                            </Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </TableCell>
          </TableRow>
      )}
    </React.Fragment>
  );
}

export function ExecutionHistory({ open, onOpenChange, strategy }: ExecutionHistoryProps) {
  const { data: executions, isLoading } = useQuery({
    queryKey: ['strategy-executions', strategy?.id],
    queryFn: () => algoApi.getExecutionHistory(strategy!.id).then((res) => res.data),
    enabled: !!strategy?.id && open,
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Execution History</DialogTitle>
          <DialogDescription>
            {strategy?.name} - Recent strategy executions (click row to expand order details)
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : executions?.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Clock className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No executions yet</p>
            <p className="text-sm">Run the strategy to see execution history</p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8"></TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Started</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead className="text-right">Symbols</TableHead>
                <TableHead className="text-right">Signals</TableHead>
                <TableHead className="text-right">Orders</TableHead>
                <TableHead className="text-right">Filled</TableHead>
                <TableHead className="text-right">P&L</TableHead>
                <TableHead>Error</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {executions?.map((execution) => (
                <ExecutionRow key={execution.id} execution={execution} />
              ))}
            </TableBody>
          </Table>
        )}
      </DialogContent>
    </Dialog>
  );
}

