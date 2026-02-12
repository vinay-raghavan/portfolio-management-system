'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
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
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { ChevronDown, ChevronRight, Star, TrendingUp, TrendingDown, Zap } from 'lucide-react';
import { researchApi } from '@/lib/api';
import { cn, formatNumber, formatPercent } from '@/lib/utils';
import type { RecommendationStock } from '@/types';

const CATEGORIES = [
  { value: 'all', label: 'All Categories' },
  { value: 'quality', label: 'Quality' },
  { value: 'value', label: 'Value' },
  { value: 'growth', label: 'Growth' },
  { value: 'dividend', label: 'Dividend' },
];

interface RecommendationsPanelProps {
  compact?: boolean;
}

export function RecommendationsPanel({ compact = false }: RecommendationsPanelProps) {
  const [category, setCategory] = useState('all');
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['research-recommendations', category],
    queryFn: async () => {
      const catParam = category === 'all' ? undefined : category;
      return researchApi.getRecommendations(catParam, compact ? 10 : 20);
    },
    staleTime: 5 * 60 * 1000,
    refetchOnMount: true,
  });

  const recommendations = data?.data?.recommendations || [];

  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case 'quality': return 'bg-blue-100 text-blue-800';
      case 'value': return 'bg-green-100 text-green-800';
      case 'growth': return 'bg-purple-100 text-purple-800';
      case 'dividend': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 75) return 'text-green-600';
    if (score >= 60) return 'text-green-500';
    if (score >= 40) return 'text-yellow-600';
    return 'text-red-500';
  };

  const getScoreBadgeVariant = (score: number): 'default' | 'secondary' | 'destructive' | 'outline' => {
    if (score >= 70) return 'default';
    if (score >= 50) return 'secondary';
    return 'outline';
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Star className="h-5 w-5" />
              Daily Recommendations
            </CardTitle>
            <CardDescription>
              Top picks combining fundamental quality (60%) + technical timing (40%)
            </CardDescription>
          </div>
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="All Categories" />
            </SelectTrigger>
            <SelectContent>
              {CATEGORIES.map((cat) => (
                <SelectItem key={cat.value} value={cat.value}>
                  {cat.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: compact ? 5 : 10 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full" />
            ))}
          </div>
        ) : error ? (
          <div className="text-center text-red-500 py-8">Failed to load recommendations</div>
        ) : recommendations.length === 0 ? (
          <div className="text-center text-muted-foreground py-8">
            No recommendations available
          </div>
        ) : (
          <div className="space-y-2">
            {recommendations.map((rec) => (
              <Collapsible
                key={rec.symbol}
                open={expandedSymbol === rec.symbol}
                onOpenChange={(open) => setExpandedSymbol(open ? rec.symbol : null)}
              >
                <CollapsibleTrigger asChild>
                  <div className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 cursor-pointer">
                    <div className="flex items-center gap-3">
                      {expandedSymbol === rec.symbol ? (
                        <ChevronDown className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      )}
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold">{rec.symbol}</span>
                          <Badge className={getCategoryColor(rec.category)} variant="outline">
                            {rec.category}
                          </Badge>
                        </div>
                        {rec.thesis && (
                          <p className="text-sm text-muted-foreground line-clamp-1">
                            {rec.thesis}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      {rec.current_price && (
                        <div className="text-right">
                          <div className="font-mono">₹{formatNumber(rec.current_price)}</div>
                          {rec.price_change_pct != null && (
                            <span className={cn(
                              'text-xs flex items-center gap-1 justify-end',
                              rec.price_change_pct >= 0 ? 'text-green-600' : 'text-red-600'
                            )}>
                              {rec.price_change_pct >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                              {formatPercent(rec.price_change_pct / 100)}
                            </span>
                          )}
                        </div>
                      )}
                      <Badge variant={getScoreBadgeVariant(rec.combined_score)} className="min-w-[50px] justify-center">
                        <Zap className="h-3 w-3 mr-1" />
                        {rec.combined_score.toFixed(0)}
                      </Badge>
                    </div>
                  </div>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <div className="px-8 pb-3 space-y-3">
                    {/* Score breakdown */}
                    <div className="grid grid-cols-3 gap-4 p-3 bg-muted/30 rounded-lg">
                      <div className="text-center">
                        <div className="text-xs text-muted-foreground">Fundamental</div>
                        <div className={cn('text-lg font-semibold', getScoreColor(rec.fundamental_score))}>
                          {rec.fundamental_score.toFixed(0)}
                        </div>
                      </div>
                      <div className="text-center">
                        <div className="text-xs text-muted-foreground">Technical</div>
                        <div className={cn('text-lg font-semibold', getScoreColor(rec.technical_score))}>
                          {rec.technical_score.toFixed(0)}
                        </div>
                      </div>
                      <div className="text-center">
                        <div className="text-xs text-muted-foreground">Combined</div>
                        <div className={cn('text-lg font-bold', getScoreColor(rec.combined_score))}>
                          {rec.combined_score.toFixed(0)}
                        </div>
                      </div>
                    </div>

                    {/* Metrics */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                      {rec.pe_ratio && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">P/E:</span>
                          <span className="font-mono">{rec.pe_ratio.toFixed(1)}</span>
                        </div>
                      )}
                      {rec.roe && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">ROE:</span>
                          <span className="font-mono">{rec.roe.toFixed(1)}%</span>
                        </div>
                      )}
                      {rec.debt_to_equity && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">D/E:</span>
                          <span className="font-mono">{rec.debt_to_equity.toFixed(2)}</span>
                        </div>
                      )}
                      {rec.dividend_yield && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Div:</span>
                          <span className="font-mono">{rec.dividend_yield.toFixed(1)}%</span>
                        </div>
                      )}
                      {rec.rsi && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">RSI:</span>
                          <span className="font-mono">{rec.rsi.toFixed(0)}</span>
                        </div>
                      )}
                      {rec.above_200ma !== null && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">200 MA:</span>
                          <span className={rec.above_200ma ? 'text-green-600' : 'text-red-600'}>
                            {rec.above_200ma ? 'Above' : 'Below'}
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Reasons */}
                    {rec.reasons && rec.reasons.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {rec.reasons.map((reason, idx) => (
                          <Badge key={idx} variant="outline" className="text-xs">
                            {reason}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                </CollapsibleContent>
              </Collapsible>
            ))}
          </div>
        )}

        {/* Summary footer */}
        {!isLoading && recommendations.length > 0 && data?.data?.by_category && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t text-sm text-muted-foreground">
            <span>
              Avg Scores: Fund {data.data.avg_fundamental_score?.toFixed(0) || '-'} |
              Tech {data.data.avg_technical_score?.toFixed(0) || '-'}
            </span>
            <div className="flex gap-2">
              {Object.entries(data.data.by_category).map(([cat, count]) => (
                <Badge key={cat} className={getCategoryColor(cat)}>
                  {cat}: {count}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

