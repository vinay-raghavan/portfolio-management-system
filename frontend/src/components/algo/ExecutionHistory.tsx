'use client';

import { useQuery } from '@tanstack/react-query';
import { Clock, CheckCircle, XCircle, AlertCircle, Loader2 } from 'lucide-react';
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
import type { AlgoStrategy, ExecutionStatus } from '@/types';

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

export function ExecutionHistory({ open, onOpenChange, strategy }: ExecutionHistoryProps) {
  const { data: executions, isLoading } = useQuery({
    queryKey: ['strategy-executions', strategy?.id],
    queryFn: () => algoApi.getExecutionHistory(strategy!.id).then((res) => res.data),
    enabled: !!strategy?.id && open,
  });

  const formatDuration = (ms: number | null) => {
    if (!ms) return '-';
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Execution History</DialogTitle>
          <DialogDescription>
            {strategy?.name} - Recent strategy executions
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
                <TableHead>Status</TableHead>
                <TableHead>Started</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead className="text-right">Symbols</TableHead>
                <TableHead className="text-right">Signals</TableHead>
                <TableHead className="text-right">Orders</TableHead>
                <TableHead className="text-right">Filled</TableHead>
                <TableHead>Error</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {executions?.map((execution) => (
                <TableRow key={execution.id}>
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
                  <TableCell className="max-w-[200px] truncate text-sm text-red-500">
                    {execution.error_message || '-'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DialogContent>
    </Dialog>
  );
}

