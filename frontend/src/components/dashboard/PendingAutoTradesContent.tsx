'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Clock, Check, X, Bot, ChevronRight, Target } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/components/ui/use-toast';
import { autoTradeApi } from '@/lib/api';
import { BrandedSpinner } from '@/components/shared';
import type { PendingAutoTrade } from '@/types';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';

/**
 * Compact pending trade card for the carousel view.
 */
function CompactTradeCard({
  trade,
  onApprove,
  onReject,
  isLoading,
  now,
}: {
  trade: PendingAutoTrade;
  onApprove: () => void;
  onReject: () => void;
  isLoading: boolean;
  now: number;
}) {
  const expiresIn = formatDistanceToNow(new Date(trade.expires_at), { addSuffix: true });
  const isExpiringSoon = new Date(trade.expires_at).getTime() - now < 3600000;
  
  // Get combined score from scores object
  const scores = trade.scores as Record<string, { combined_score?: number; confidence_level?: string }> | null;
  let combinedScore: number | null = null;
  let confidence: string | null = null;
  
  if (scores) {
    const symbolKeys = Object.keys(scores).filter(k => typeof scores[k] === 'object');
    if (symbolKeys.length > 0) {
      const values = symbolKeys.map(k => scores[k].combined_score).filter((v): v is number => v !== undefined);
      combinedScore = values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : null;
      confidence = (scores[symbolKeys[0]] as { confidence_level?: string })?.confidence_level ?? null;
    }
  }

  return (
    <div className="flex items-center justify-between p-2 border rounded-lg bg-muted/30">
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="font-medium text-sm truncate max-w-[100px]" title={trade.symbols.join(', ')}>
              {trade.symbols.length > 2 ? `${trade.symbols.slice(0, 2).join(', ')}...` : trade.symbols.join(', ')}
            </span>
            <Badge variant="outline" className="text-[10px] px-1 py-0">{trade.category}</Badge>
            {combinedScore !== null && (
              <Badge variant="secondary" className="text-[10px] px-1 py-0">{combinedScore.toFixed(0)}</Badge>
            )}
            {confidence && (
              <Badge variant="secondary" className="text-[10px] px-1 py-0 capitalize">
                <Target className="h-2.5 w-2.5 mr-0.5" />
                {confidence}
              </Badge>
            )}
          </div>
          <div className={`text-[10px] ${isExpiringSoon ? 'text-destructive' : 'text-muted-foreground'}`}>
            <Clock className="inline h-2.5 w-2.5 mr-0.5" />{expiresIn}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-1 ml-2">
        <Button size="icon" variant="ghost" className="h-6 w-6 text-green-600 hover:bg-green-50" onClick={onApprove} disabled={isLoading}>
          <Check className="h-3.5 w-3.5" />
        </Button>
        <Button size="icon" variant="ghost" className="h-6 w-6 text-red-600 hover:bg-red-50" onClick={onReject} disabled={isLoading}>
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}

/**
 * PendingAutoTradesContent - Compact content for the AlgoCarousel pending tab.
 */
export function PendingAutoTradesContent() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading, dataUpdatedAt } = useQuery({
    queryKey: ['pending-auto-trades'],
    queryFn: () => autoTradeApi.getPendingTrades('pending').then(r => r.data),
    refetchInterval: 30000,
  });

  const now = dataUpdatedAt || 0;

  const actionMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'approve' | 'reject' }) =>
      autoTradeApi.actionPendingTrade(id, { action }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['pending-auto-trades'] });
      toast({
        title: variables.action === 'approve' ? 'Trade approved' : 'Trade rejected',
        description: variables.action === 'approve' ? 'Strategy created' : 'Dismissed',
      });
    },
    onError: () => {
      toast({ title: 'Error', description: 'Failed to process', variant: 'destructive' });
    },
  });

  const pendingTrades = data?.pending_trades || [];

  if (isLoading) {
    return <div className="flex items-center justify-center py-6"><BrandedSpinner /></div>;
  }

  if (pendingTrades.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-6 text-center">
        <Bot className="h-8 w-8 text-muted-foreground mb-2" />
        <p className="text-sm text-muted-foreground">No pending trades</p>
        <Link href="/settings/auto-trade">
          <Button variant="link" size="sm" className="mt-1 h-6 text-xs">
            Configure <ChevronRight className="h-3 w-3 ml-0.5" />
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-2 py-2">
      {pendingTrades.slice(0, 3).map((trade) => (
        <CompactTradeCard
          key={trade.id}
          trade={trade}
          onApprove={() => actionMutation.mutate({ id: trade.id, action: 'approve' })}
          onReject={() => actionMutation.mutate({ id: trade.id, action: 'reject' })}
          isLoading={actionMutation.isPending}
          now={now}
        />
      ))}
      {pendingTrades.length > 3 && (
        <Link href="/settings/auto-trade" className="block">
          <Button variant="link" size="sm" className="w-full h-6 text-xs">
            +{pendingTrades.length - 3} more <ChevronRight className="h-3 w-3 ml-1" />
          </Button>
        </Link>
      )}
    </div>
  );
}

