'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { formatDistanceToNow, format } from 'date-fns';
import { Bookmark, ArrowLeft, Play, Trash2, Settings2, Bot, Clock, RefreshCw, MoreVertical, ExternalLink } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { useToast } from '@/components/ui/use-toast';
import { screenerApi, type CustomScreener } from '@/lib/api';
import { BrandedSpinner } from '@/components/shared';

function SavedScreenerCard({
  screener,
  onRun,
  onRunAutoTrade,
  onDelete,
  isRunning,
}: {
  screener: CustomScreener;
  onRun: () => void;
  onRunAutoTrade: () => void;
  onDelete: () => void;
  isRunning: boolean;
}) {
  const hasAutoTrade = screener.is_auto_trade_enabled;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="flex items-center gap-2 text-lg">
              {screener.name}
              {hasAutoTrade && (
                <Badge variant="default" className="ml-2 text-xs">
                  <Bot className="h-3 w-3 mr-1" /> Auto-Trade
                </Badge>
              )}
            </CardTitle>
            <CardDescription className="mt-1">
              {screener.description || 'No description'}
            </CardDescription>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onRun}>
                <Play className="h-4 w-4 mr-2" /> Run Screener
              </DropdownMenuItem>
              {hasAutoTrade && (
                <DropdownMenuItem onClick={onRunAutoTrade}>
                  <Bot className="h-4 w-4 mr-2" /> Run Auto-Trade
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <Link href={`/screener?load=${screener.id}`}>
                <DropdownMenuItem>
                  <ExternalLink className="h-4 w-4 mr-2" /> Edit Filters
                </DropdownMenuItem>
              </Link>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={onDelete} className="text-destructive">
                <Trash2 className="h-4 w-4 mr-2" /> Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4 text-sm mb-4">
          <div>
            <p className="text-muted-foreground">Filters</p>
            <p className="font-medium">{screener.filters.length}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Universe</p>
            <p className="font-medium">{screener.universe}</p>
          </div>
        </div>

        {hasAutoTrade && (
          <div className="border-t pt-3 mt-3 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Schedule:</span>
              <Badge variant="outline" className="capitalize">{screener.run_frequency}</Badge>
            </div>
            {screener.inferred_strategy_type && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Strategy:</span>
                <Badge variant="secondary">{screener.inferred_strategy_type}</Badge>
              </div>
            )}
            {screener.last_run_at && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Last run:</span>
                <span>{formatDistanceToNow(new Date(screener.last_run_at), { addSuffix: true })}</span>
              </div>
            )}
            {screener.next_run_at && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground flex items-center gap-1">
                  <Clock className="h-3 w-3" /> Next run:
                </span>
                <span>{format(new Date(screener.next_run_at), 'MMM d, HH:mm')}</span>
              </div>
            )}
          </div>
        )}

        <div className="flex gap-2 mt-4">
          <Button variant="outline" size="sm" onClick={onRun} disabled={isRunning} className="flex-1">
            {isRunning ? <RefreshCw className="h-4 w-4 mr-1 animate-spin" /> : <Play className="h-4 w-4 mr-1" />}
            Run
          </Button>
          {hasAutoTrade && (
            <Button variant="default" size="sm" onClick={onRunAutoTrade} disabled={isRunning} className="flex-1">
              <Bot className="h-4 w-4 mr-1" /> Auto-Trade
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default function SavedScreenersPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [deleteScreener, setDeleteScreener] = useState<CustomScreener | null>(null);
  const [runningId, setRunningId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['customScreeners'],
    queryFn: () => screenerApi.getCustomScreeners().then(res => res.data),
  });

  const runMutation = useMutation({
    mutationFn: (id: string) => {
      setRunningId(id);
      return screenerApi.runCustomScreener(id);
    },
    onSuccess: (res) => {
      toast({
        title: 'Screener Complete',
        description: `Found ${res.data.passed_count} stocks out of ${res.data.total_screened}`,
      });
      setRunningId(null);
    },
    onError: (error: any) => {
      toast({ title: 'Error', description: error.response?.data?.detail || 'Failed to run screener', variant: 'destructive' });
      setRunningId(null);
    },
  });

  const runAutoTradeMutation = useMutation({
    mutationFn: (id: string) => {
      setRunningId(id);
      return screenerApi.runAutoTrade(id);
    },
    onSuccess: (res) => {
      toast({
        title: 'Auto-Trade Complete',
        description: `Created ${res.data.trades_created} trades, ${res.data.pending_trades_created} pending`,
      });
      setRunningId(null);
    },
    onError: (error: any) => {
      toast({ title: 'Error', description: error.response?.data?.detail || 'Failed to run auto-trade', variant: 'destructive' });
      setRunningId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => screenerApi.deleteCustomScreener(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customScreeners'] });
      setDeleteScreener(null);
      toast({ title: 'Screener deleted' });
    },
    onError: (error: any) => {
      toast({ title: 'Error', description: error.response?.data?.detail || 'Failed to delete screener', variant: 'destructive' });
    },
  });

  const screeners = data?.screeners ?? [];
  const autoTradeScreeners = screeners.filter(s => s.is_auto_trade_enabled);
  const regularScreeners = screeners.filter(s => !s.is_auto_trade_enabled);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <BrandedSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/screener">
            <Button variant="ghost" size="icon"><ArrowLeft className="h-5 w-5" /></Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <Bookmark className="h-8 w-8" />
              Saved Screeners
            </h1>
            <p className="text-muted-foreground">Manage your saved screener configurations</p>
          </div>
        </div>
        <Link href="/settings/auto-trade">
          <Button variant="outline">
            <Settings2 className="h-4 w-4 mr-2" /> Auto-Trade Settings
          </Button>
        </Link>
      </div>

      {screeners.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Bookmark className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No saved screeners</h3>
            <p className="text-muted-foreground mb-4 text-center">
              Create custom filters and save them for quick access
            </p>
            <Link href="/screener">
              <Button>Go to Screener</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <>
          {autoTradeScreeners.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <Bot className="h-5 w-5" /> Auto-Trade Enabled ({autoTradeScreeners.length})
              </h2>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {autoTradeScreeners.map((screener) => (
                  <SavedScreenerCard
                    key={screener.id}
                    screener={screener}
                    onRun={() => runMutation.mutate(screener.id)}
                    onRunAutoTrade={() => runAutoTradeMutation.mutate(screener.id)}
                    onDelete={() => setDeleteScreener(screener)}
                    isRunning={runningId === screener.id}
                  />
                ))}
              </div>
            </div>
          )}

          {regularScreeners.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-xl font-semibold">
                Regular Screeners ({regularScreeners.length})
              </h2>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {regularScreeners.map((screener) => (
                  <SavedScreenerCard
                    key={screener.id}
                    screener={screener}
                    onRun={() => runMutation.mutate(screener.id)}
                    onRunAutoTrade={() => {}}
                    onDelete={() => setDeleteScreener(screener)}
                    isRunning={runningId === screener.id}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      )}

      <AlertDialog open={!!deleteScreener} onOpenChange={() => setDeleteScreener(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Screener</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &quot;{deleteScreener?.name}&quot;? This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground"
              onClick={() => deleteScreener && deleteMutation.mutate(deleteScreener.id)}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

