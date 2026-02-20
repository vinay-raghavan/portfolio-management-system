'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  FileText,
  ChevronLeft,
  ChevronRight,
  CheckCircle,
  XCircle,
  Clock,
  Activity,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { format } from 'date-fns';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
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
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { reportsApi } from '@/lib/api';
import { cn } from '@/lib/utils';

const BROKER_TYPES = [
  { value: 'ALL', label: 'All Brokers' },
  { value: 'fyers', label: 'Fyers' },
  { value: 'angelone', label: 'Angel One' },
  { value: 'dhan', label: 'Dhan' },
  { value: 'zerodha', label: 'Zerodha' },
];

const STATUS_FILTER = [
  { value: 'ALL', label: 'All Status' },
  { value: 'success', label: 'Success' },
  { value: 'failure', label: 'Failure' },
];

export default function APILogsPage() {
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [brokerType, setBrokerType] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  // Fetch API stats
  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['api-stats', brokerType === 'ALL' ? undefined : brokerType],
    queryFn: () =>
      reportsApi
        .getAPIStats({
          broker_type: brokerType === 'ALL' ? undefined : brokerType,
        })
        .then((res) => res.data),
  });

  // Fetch API logs
  const { data: logsData, isLoading: logsLoading } = useQuery({
    queryKey: ['api-logs', brokerType, statusFilter, page, pageSize],
    queryFn: () =>
      reportsApi
        .getAPILogs({
          broker_type: brokerType === 'ALL' ? undefined : brokerType,
          is_success: statusFilter === 'ALL' ? undefined : statusFilter === 'success',
          page,
          page_size: pageSize,
        })
        .then((res) => res.data),
  });

  const logs = logsData?.logs ?? [];
  const totalCount = logsData?.total ?? 0;
  const totalPages = logsData?.total_pages ?? 1;

  // Calculate overall stats
  const stats = statsData?.stats ?? [];
  const totalCalls = stats.reduce((acc, s) => acc + s.total_calls, 0);
  const successCount = stats.reduce((acc, s) => acc + s.success_count, 0);
  const overallSuccessRate = totalCalls > 0 ? (successCount / totalCalls) * 100 : 0;
  const avgLatency = stats.length > 0
    ? stats.reduce((acc, s) => acc + (s.avg_latency_ms ?? 0), 0) / stats.length
    : 0;

  const formatDate = (dateString: string) => {
    return format(new Date(dateString), 'MMM dd HH:mm:ss');
  };

  const toggleRow = (id: string) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const getLatencyColor = (latency: number | null) => {
    if (!latency) return 'text-muted-foreground';
    if (latency < 200) return 'text-emerald-600';
    if (latency < 500) return 'text-amber-600';
    return 'text-red-600';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <FileText className="h-8 w-8 text-purple-500" />
          Broker API Logs
        </h1>
        <p className="text-muted-foreground">
          API call history for debugging broker integrations
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Activity className="h-4 w-4 text-blue-500" />
              Total Calls
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <p className="text-2xl font-bold">{totalCalls.toLocaleString()}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-emerald-500" />
              Success Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <p className={cn(
                "text-2xl font-bold",
                overallSuccessRate >= 90 ? "text-emerald-600" : "text-amber-600"
              )}>
                {overallSuccessRate.toFixed(1)}%
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <XCircle className="h-4 w-4 text-red-500" />
              Failures
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <p className="text-2xl font-bold text-red-600">
                {(totalCalls - successCount).toLocaleString()}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Clock className="h-4 w-4 text-amber-500" />
              Avg Latency
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <p className={cn("text-2xl font-bold", getLatencyColor(avgLatency))}>
                {avgLatency.toFixed(0)}ms
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <Select value={brokerType} onValueChange={(v) => {
          setBrokerType(v);
          setPage(1);
        }}>
          <SelectTrigger className="w-[160px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {BROKER_TYPES.map((b) => (
              <SelectItem key={b.value} value={b.value}>
                {b.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={statusFilter} onValueChange={(v) => {
          setStatusFilter(v);
          setPage(1);
        }}>
          <SelectTrigger className="w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUS_FILTER.map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Logs Table */}
      <Card>
        <CardHeader>
          <CardTitle>API Logs ({totalCount})</CardTitle>
          <CardDescription>Recent broker API calls with request/response details</CardDescription>
        </CardHeader>
        <CardContent>
          {logsLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : logs.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              No API logs found
            </p>
          ) : (
            <>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-8"></TableHead>
                      <TableHead>Time</TableHead>
                      <TableHead>Broker</TableHead>
                      <TableHead>Action</TableHead>
                      <TableHead>Endpoint</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Latency</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.map((log) => (
                      <Collapsible key={log.id} asChild>
                        <>
                          <CollapsibleTrigger asChild>
                            <TableRow
                              className="cursor-pointer hover:bg-muted/50"
                              onClick={() => toggleRow(log.id)}
                            >
                              <TableCell>
                                {expandedRows.has(log.id) ? (
                                  <ChevronUp className="h-4 w-4" />
                                ) : (
                                  <ChevronDown className="h-4 w-4" />
                                )}
                              </TableCell>
                              <TableCell className="whitespace-nowrap">
                                {formatDate(log.request_at)}
                              </TableCell>
                              <TableCell>
                                <Badge variant="outline">{log.broker_type}</Badge>
                              </TableCell>
                              <TableCell className="font-medium">{log.action}</TableCell>
                              <TableCell className="max-w-[200px] truncate">
                                <code className="text-xs">{log.method} {log.endpoint}</code>
                              </TableCell>
                              <TableCell>
                                {log.is_success ? (
                                  <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20">
                                    <CheckCircle className="h-3 w-3 mr-1" />
                                    {log.status_code ?? 'OK'}
                                  </Badge>
                                ) : (
                                  <Badge className="bg-red-500/10 text-red-600 border-red-500/20">
                                    <XCircle className="h-3 w-3 mr-1" />
                                    {log.status_code ?? 'Error'}
                                  </Badge>
                                )}
                              </TableCell>
                              <TableCell className={cn("text-right", getLatencyColor(log.latency_ms))}>
                                {log.latency_ms ? `${log.latency_ms}ms` : '-'}
                              </TableCell>
                            </TableRow>
                          </CollapsibleTrigger>
                          <CollapsibleContent asChild>
                            <TableRow className="bg-muted/30">
                              <TableCell colSpan={7} className="py-4">
                                {log.error_message && (
                                  <div className="mb-3 p-3 rounded bg-red-500/10 text-red-600">
                                    <span className="font-medium">Error: </span>
                                    {log.error_message}
                                  </div>
                                )}
                                <p className="text-sm text-muted-foreground">
                                  Click to view detailed request/response data (requires fetching log detail)
                                </p>
                              </TableCell>
                            </TableRow>
                          </CollapsibleContent>
                        </>
                      </Collapsible>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              <div className="flex items-center justify-between mt-4">
                <p className="text-sm text-muted-foreground">
                  Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, totalCount)} of {totalCount}
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <span className="text-sm">Page {page} of {totalPages}</span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

