'use client';


import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Clock, Check, X, Bot, ChevronRight, Target, TrendingUp, BarChart3, Newspaper } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/components/ui/use-toast';
import { autoTradeApi } from '@/lib/api';
import { BrandedSpinner } from '@/components/shared';
import type { PendingAutoTrade } from '@/types';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';

// Mini bar for individual score
function ScoreBar({ value, maxValue, color }: { value: number; maxValue: number; color: string }) {
  const percentage = Math.max(0, Math.min(100, (value / maxValue) * 100));
  return (
    <div className="h-1.5 w-12 bg-muted rounded-full overflow-hidden">
      <div
        className={cn('h-full transition-all duration-300', color)}
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
}

// Scores object can be either flat or per-symbol keyed
interface SymbolScores {
  technical_score?: number;
  fundamental_score?: number;
  sentiment_score?: number;
  combined_score?: number;
  confidence_level?: string;
  signal_direction?: string;
  position_size_multiplier?: number;
}

// Helper to extract aggregated scores from the nested scores object
// Backend sends scores keyed by symbol - we average them for display
function getScores(trade: PendingAutoTrade) {
  const scores = trade.scores as Record<string, SymbolScores> | null;
  if (!scores) {
    return { technical: null, fundamental: null, sentiment: null, combined: null, confidence: null, direction: null };
  }

  // Check if it's per-symbol keyed (object with symbol keys) or flat
  const symbolKeys = Object.keys(scores).filter(key =>
    typeof scores[key] === 'object' && 'technical_score' in (scores[key] as object)
  );

  if (symbolKeys.length > 0) {
    // Per-symbol scores - average them
    const symbolScores = symbolKeys.map(k => scores[k] as SymbolScores);
    const avg = (arr: (number | undefined)[]) => {
      const valid = arr.filter((v): v is number => v !== undefined);
      return valid.length > 0 ? valid.reduce((a, b) => a + b, 0) / valid.length : null;
    };
    return {
      technical: avg(symbolScores.map(s => s.technical_score)),
      fundamental: avg(symbolScores.map(s => s.fundamental_score)),
      sentiment: avg(symbolScores.map(s => s.sentiment_score)),
      combined: avg(symbolScores.map(s => s.combined_score)),
      confidence: symbolScores[0]?.confidence_level ?? null,
      direction: symbolScores[0]?.signal_direction ?? null,
    };
  }

  // Flat scores format (fallback)
  const flat = scores as unknown as SymbolScores;
  return {
    technical: flat.technical_score ?? null,
    fundamental: flat.fundamental_score ?? null,
    sentiment: flat.sentiment_score ?? null,
    combined: flat.combined_score ?? null,
    confidence: (scores as { confidence?: string }).confidence ?? null,
    direction: (scores as { direction?: string }).direction ?? null,
  };
}

// Multi-factor score display component with mini bar chart
function MultiFactorScores({ trade }: { trade: PendingAutoTrade }) {
  const { technical, fundamental, sentiment, combined } = getScores(trade);
  const hasScores = technical !== null || fundamental !== null || sentiment !== null;
  if (!hasScores) return null;

  // Normalize sentiment from -100..+100 to 0..100 for bar display
  const normalizedSentiment = sentiment !== null ? (sentiment + 100) / 2 : null;

  return (
    <div className="space-y-1.5 mt-1.5 pt-1.5 border-t border-dashed">
      {/* Score bars visualization */}
      <div className="flex items-center gap-2">
        {technical !== null && (
          <div className="flex items-center gap-1" title={`Technical: ${technical.toFixed(0)}`}>
            <TrendingUp className="h-3 w-3 text-blue-500" />
            <ScoreBar value={technical} maxValue={100} color="bg-blue-500" />
          </div>
        )}
        {fundamental !== null && (
          <div className="flex items-center gap-1" title={`Fundamental: ${fundamental.toFixed(0)}`}>
            <BarChart3 className="h-3 w-3 text-purple-500" />
            <ScoreBar value={fundamental} maxValue={100} color="bg-purple-500" />
          </div>
        )}
        {normalizedSentiment !== null && (
          <div className="flex items-center gap-1" title={`Sentiment: ${sentiment! > 0 ? '+' : ''}${sentiment!.toFixed(0)}`}>
            <Newspaper className="h-3 w-3 text-orange-500" />
            <ScoreBar value={normalizedSentiment} maxValue={100} color="bg-orange-500" />
          </div>
        )}
      </div>
      {/* Text scores */}
      <div className="flex items-center gap-3 text-[10px]">
        {technical !== null && (
          <span className={cn('font-medium', technical >= 70 ? 'text-green-600' : technical >= 50 ? 'text-yellow-600' : 'text-muted-foreground')}>
            T:{technical.toFixed(0)}
          </span>
        )}
        {fundamental !== null && (
          <span className={cn('font-medium', fundamental >= 70 ? 'text-green-600' : fundamental >= 50 ? 'text-yellow-600' : 'text-muted-foreground')}>
            F:{fundamental.toFixed(0)}
          </span>
        )}
        {sentiment !== null && (
          <span className={cn('font-medium', sentiment > 0 ? 'text-green-600' : sentiment < 0 ? 'text-red-600' : 'text-muted-foreground')}>
            S:{sentiment > 0 ? '+' : ''}{sentiment.toFixed(0)}
          </span>
        )}
        {combined !== null && (
          <span className="font-semibold text-primary">
            ={combined.toFixed(0)}
          </span>
        )}
      </div>
    </div>
  );
}

function PendingTradeCard({
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
  const isExpiringSoon = new Date(trade.expires_at).getTime() - now < 3600000; // 1 hour
  const { combined, confidence, direction } = getScores(trade);

  // Display symbols as comma-separated list (max 3 shown inline)
  const symbolsDisplay = trade.symbols.length > 3
    ? `${trade.symbols.slice(0, 3).join(', ')} +${trade.symbols.length - 3} more`
    : trade.symbols.join(', ');

  // Direction badge variant (handle both lowercase and uppercase)
  const normalizedDirection = direction?.toUpperCase() || 'LONG';
  const directionVariant = normalizedDirection === 'LONG' ? 'default' : normalizedDirection === 'SHORT' ? 'destructive' : 'secondary';
  const directionLabel = normalizedDirection;

  return (
    <div className="p-3 border rounded-lg bg-card">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex flex-col">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-medium" title={trade.symbols.join(', ')}>{symbolsDisplay}</span>
              <Badge variant={directionVariant} className="text-xs">
                {directionLabel}
              </Badge>
              <Badge variant="outline" className="text-xs">{trade.category}</Badge>
              {confidence && (
                <Badge variant="secondary" className="text-xs capitalize">
                  <Target className="h-3 w-3 mr-1" />
                  {confidence}
                </Badge>
              )}
              {combined !== null && (
                <Badge variant="secondary" className="text-xs">
                  Score: {combined.toFixed(0)}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
              <span>{trade.recommended_strategy_type}</span>
              <span>·</span>
              <span>{trade.symbols.length} symbol{trade.symbols.length > 1 ? 's' : ''}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="text-right mr-2">
            <p className={`text-xs ${isExpiringSoon ? 'text-destructive' : 'text-muted-foreground'}`}>
              <Clock className="inline h-3 w-3 mr-1" />
              {expiresIn}
            </p>
          </div>
          <Button
            size="sm"
            variant="outline"
            className="text-green-600 border-green-600 hover:bg-green-50 dark:hover:bg-green-950"
            onClick={onApprove}
            disabled={isLoading}
          >
            <Check className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="text-red-600 border-red-600 hover:bg-red-50 dark:hover:bg-red-950"
            onClick={onReject}
            disabled={isLoading}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>
      {/* Multi-factor score breakdown */}
      <MultiFactorScores trade={trade} />
    </div>
  );
}

export function PendingAutoTradesPanel() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading, dataUpdatedAt } = useQuery({
    queryKey: ['pending-auto-trades'],
    queryFn: () => autoTradeApi.getPendingTrades('PENDING').then(r => r.data),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Use dataUpdatedAt as the "now" reference point for expiration calculations
  // This is pure (computed by React Query) and updates when data refetches
  const now = dataUpdatedAt || 0;

  const actionMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'approve' | 'reject' }) =>
      autoTradeApi.actionPendingTrade(id, { action }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['pending-auto-trades'] });
      toast({
        title: variables.action === 'approve' ? 'Trade approved' : 'Trade rejected',
        description: variables.action === 'approve' 
          ? 'Strategy will be created and executed'
          : 'Trade recommendation dismissed',
      });
    },
    onError: () => {
      toast({ title: 'Error', description: 'Failed to process trade', variant: 'destructive' });
    },
  });

  const pendingTrades = data?.pending_trades || [];
  const pendingCount = data?.pending_count || 0;

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            Pending Auto-Trades
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <BrandedSpinner />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            Pending Auto-Trades
            {pendingCount > 0 && (
              <Badge variant="secondary" className="ml-2">
                {pendingCount}
              </Badge>
            )}
          </CardTitle>
          <Link href="/settings/auto-trade">
            <Button variant="ghost" size="sm">
              Settings <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        {pendingTrades.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Bot className="h-10 w-10 text-muted-foreground mb-3" />
            <p className="text-sm text-muted-foreground">No pending auto-trades</p>
            <p className="text-xs text-muted-foreground mt-1">
              Configure auto-trade in settings to receive recommendations
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {pendingTrades.slice(0, 5).map((trade) => (
              <PendingTradeCard
                key={trade.id}
                trade={trade}
                onApprove={() => actionMutation.mutate({ id: trade.id, action: 'approve' })}
                onReject={() => actionMutation.mutate({ id: trade.id, action: 'reject' })}
                isLoading={actionMutation.isPending}
                now={now}
              />
            ))}
            {pendingTrades.length > 5 && (
              <p className="text-sm text-muted-foreground text-center pt-2">
                +{pendingTrades.length - 5} more pending trades
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

