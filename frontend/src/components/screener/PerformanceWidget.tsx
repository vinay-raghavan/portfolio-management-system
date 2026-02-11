'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/components/ui/use-toast';

import {
  TrendingUp,
  TrendingDown,
  Target,
  BarChart3,
  Trophy,
  Zap,
  Flame,
  Timer,
  CircleDot,
  ChevronDown,
  ChevronRight,
  Star,
  Eye,
  Bookmark,
  Maximize2,
} from 'lucide-react';
import { screenerApi, watchlistApi, RecommendationItem } from '@/lib/api';
import { cn } from '@/lib/utils';

interface PerformanceWidgetProps {
  days?: number;
  compact?: boolean;
}

export function PerformanceWidget({ days = 30, compact = false }: PerformanceWidgetProps) {
  const [showWatchlistDialog, setShowWatchlistDialog] = useState(false);
  const [watchlistName, setWatchlistName] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch performance stats
  const { data, isLoading, error } = useQuery({
    queryKey: ['screener-performance', days],
    queryFn: () => screenerApi.getPerformance(days),
    staleTime: 5 * 60 * 1000,
  });

  // Fetch recommendations from 8 days ago to show stocks with 1D and 1W returns
  // 1D returns are populated after 1 day, 1W after 7 days
  // Using 8 days ensures at least 1D and 1W returns are available
  // (1M returns will show when data is 30+ days old)
  const getDateWithReturns = () => {
    const date = new Date();
    date.setDate(date.getDate() - 8);
    return date.toISOString().split('T')[0];
  };

  const { data: recommendationsData, error: recommendationsError } = useQuery({
    queryKey: ['screener-recommendations-with-returns'],
    queryFn: () => screenerApi.getRecommendations(getDateWithReturns()),
    staleTime: 5 * 60 * 1000,
  });

  // State for expanding compact view
  const [isExpanded, setIsExpanded] = useState(false);

  // Create watchlist mutation - create watchlist first, then add items
  const createWatchlistMutation = useMutation({
    mutationFn: async ({ name, symbols }: { name: string; symbols: string[] }) => {
      // First create the watchlist
      const response = await watchlistApi.createWatchlist({
        name,
        description: `Screener recommendations from ${selectedCategory}`
      });
      const watchlistId = response.data.id;

      // Then add each symbol
      for (const symbol of symbols) {
        await watchlistApi.addItem(watchlistId, symbol);
      }

      return response;
    },
    onSuccess: () => {
      toast({
        title: 'Watchlist Created',
        description: `Successfully created watchlist "${watchlistName}"`,
      });
      setShowWatchlistDialog(false);
      setWatchlistName('');
      setSelectedCategory(null);
      queryClient.invalidateQueries({ queryKey: ['watchlists'] });
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to create watchlist',
        variant: 'destructive',
      });
    },
  });

  const handleSaveAsWatchlist = (category: string, symbols: string[]) => {
    setSelectedCategory(category);
    setWatchlistName(`${category.charAt(0).toUpperCase() + category.slice(1)} Picks - ${new Date().toLocaleDateString()}`);
    setShowWatchlistDialog(true);
  };

  const confirmCreateWatchlist = () => {
    if (!selectedCategory || !recommendationsData?.data) return;
    const categoryData = recommendationsData.data.categories.find(c => c.category === selectedCategory);
    if (!categoryData) return;
    const symbols = categoryData.recommendations.map(r => r.symbol);
    createWatchlistMutation.mutate({ name: watchlistName, symbols });
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-32" />
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || !data?.data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Screener Performance
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">Unable to load performance data</p>
        </CardContent>
      </Card>
    );
  }

  const stats = data.data;
  const recommendations = recommendationsData?.data?.categories || [];

  // Determine overall trend
  const overallTrend = stats.overall_avg_return_1m !== null && stats.overall_avg_return_1m > 0;

  // Get all symbols from recommendations for compact view
  const allSymbols = recommendations.flatMap(cat =>
    cat.recommendations.slice(0, 3).map(r => ({ symbol: r.symbol, score: r.score, category: cat.category }))
  );

  // Format helper
  const formatPercent = (val: number | null) =>
    val !== null ? `${val >= 0 ? '+' : ''}${val.toFixed(1)}%` : '-';

  // Always show compact card, with Sheet for expanded view
  return (
    <>
      <Card className="overflow-hidden">
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className={cn(
                "p-1.5 rounded-lg",
                overallTrend ? "bg-green-100 dark:bg-green-900/40" : "bg-muted"
              )}>
                <BarChart3 className={cn(
                  "h-4 w-4",
                  overallTrend ? "text-green-600 dark:text-green-400" : ""
                )} />
              </div>
              <div>
                <p className="text-sm font-medium">Screener Performance</p>
                <p className="text-xs text-muted-foreground">{stats.unique_symbols} stocks tracked</p>
              </div>
            </div>
            {stats.total_recommendations > 0 && (
              <div className="text-right">
                <p className={cn(
                  "text-lg font-bold",
                  overallTrend ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
                )}>
                  {formatPercent(stats.overall_avg_return_1m)}
                </p>
                <p className="text-xs text-muted-foreground">1M avg</p>
              </div>
            )}
          </div>

          {stats.total_recommendations > 0 ? (
            <>
              {/* Compact stats row */}
              <div className="flex items-center gap-4 text-xs mb-3">
                <div className="flex items-center gap-1">
                  <Zap className="h-3 w-3 text-blue-500" />
                  <span className="text-muted-foreground">1D:</span>
                  <span className={cn("font-medium", stats.overall_win_rate_1d && stats.overall_win_rate_1d >= 50 ? "text-green-600" : "text-red-600")}>
                    {stats.overall_win_rate_1d?.toFixed(0) ?? '-'}%
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <Timer className="h-3 w-3 text-purple-500" />
                  <span className="text-muted-foreground">1W:</span>
                  <span className={cn("font-medium", stats.overall_win_rate_1w && stats.overall_win_rate_1w >= 50 ? "text-green-600" : "text-red-600")}>
                    {stats.overall_win_rate_1w?.toFixed(0) ?? '-'}%
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <Flame className="h-3 w-3 text-orange-500" />
                  <span className="text-muted-foreground">1M:</span>
                  <span className={cn("font-medium", stats.overall_win_rate_1m && stats.overall_win_rate_1m >= 50 ? "text-green-600" : "text-red-600")}>
                    {stats.overall_win_rate_1m?.toFixed(0) ?? '-'}%
                  </span>
                </div>
              </div>

              {/* Top symbols row */}
              {allSymbols.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {allSymbols.slice(0, 6).map((item, idx) => (
                    <Badge
                      key={`${item.symbol}-${idx}`}
                      variant="secondary"
                      className="text-xs font-mono px-2 py-0.5"
                    >
                      {item.symbol}
                    </Badge>
                  ))}
                  {allSymbols.length > 6 && (
                    <Badge variant="outline" className="text-xs px-2 py-0.5">
                      +{allSymbols.length - 6} more
                    </Badge>
                  )}
                </div>
              )}

              {/* Expand button */}
              <Button
                variant="ghost"
                size="sm"
                className="w-full h-7 text-xs"
                onClick={() => setIsExpanded(true)}
              >
                <Maximize2 className="h-3 w-3 mr-1.5" />
                View Details
              </Button>
            </>
          ) : (
            <p className="text-xs text-muted-foreground text-center py-2">
              No recommendations yet
            </p>
          )}
        </CardContent>
      </Card>

      {/* Expanded View Sheet */}
      <Sheet open={isExpanded} onOpenChange={setIsExpanded}>
        <SheetContent side="right" className="w-full sm:max-w-lg overflow-y-auto">
          <SheetHeader className="pb-4">
            <SheetTitle className="flex items-center gap-2">
              <div className={cn(
                "p-1.5 rounded-lg",
                overallTrend ? "bg-green-100 dark:bg-green-900/40" : "bg-muted"
              )}>
                <BarChart3 className={cn(
                  "h-4 w-4",
                  overallTrend ? "text-green-600 dark:text-green-400" : ""
                )} />
              </div>
              Screener Performance
              {overallTrend && (
                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-400 dark:border-green-800 text-xs ml-2">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  Profitable
                </Badge>
              )}
            </SheetTitle>
            <SheetDescription>
              Last {days} days • {stats.total_recommendations} recommendations • {stats.unique_symbols} unique stocks
            </SheetDescription>
          </SheetHeader>

          {stats.total_recommendations > 0 && (
            <div className="space-y-6">
              {/* Win Rate Cards */}
              <div className="grid grid-cols-3 gap-3">
                <WinRateCard
                  label="1 Day"
                  icon={<Zap className="h-3.5 w-3.5" />}
                  winRate={stats.overall_win_rate_1d}
                  avgReturn={stats.overall_avg_return_1d}
                  color="blue"
                />
                <WinRateCard
                  label="1 Week"
                  icon={<Timer className="h-3.5 w-3.5" />}
                  winRate={stats.overall_win_rate_1w}
                  avgReturn={stats.overall_avg_return_1w}
                  color="purple"
                />
                <WinRateCard
                  label="1 Month"
                  icon={<Flame className="h-3.5 w-3.5" />}
                  winRate={stats.overall_win_rate_1m}
                  avgReturn={stats.overall_avg_return_1m}
                  color="orange"
                />
              </div>

              {/* Category Tabs */}
              {stats.categories.length > 0 && (
                <Tabs defaultValue={stats.categories[0]?.category || 'momentum'}>
                  <TabsList className="mb-4 w-full grid h-9" style={{ gridTemplateColumns: `repeat(${stats.categories.length}, 1fr)` }}>
                    {stats.categories.map((cat) => (
                      <TabsTrigger
                        key={cat.category}
                        value={cat.category}
                        className="capitalize text-xs"
                      >
                        {getCategoryIcon(cat.category)}
                        <span className="ml-1.5">{cat.category}</span>
                      </TabsTrigger>
                    ))}
                  </TabsList>
                  {stats.categories.map((cat) => {
                    const categoryRecs = recommendations.find(r => r.category === cat.category);
                    return (
                      <TabsContent key={cat.category} value={cat.category} className="mt-0">
                        <CategoryStats
                          stats={cat}
                          recommendations={categoryRecs?.recommendations || []}
                          onSaveAsWatchlist={(symbols) => handleSaveAsWatchlist(cat.category, symbols)}
                        />
                      </TabsContent>
                    );
                  })}
                </Tabs>
              )}
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Save as Watchlist Dialog */}
      <Dialog open={showWatchlistDialog} onOpenChange={setShowWatchlistDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Bookmark className="h-5 w-5" />
              Save as Watchlist
            </DialogTitle>
            <DialogDescription>
              Create a watchlist from the {selectedCategory} recommendations to track their performance.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="watchlist-name">Watchlist Name</Label>
            <Input
              id="watchlist-name"
              value={watchlistName}
              onChange={(e) => setWatchlistName(e.target.value)}
              placeholder="Enter watchlist name"
              className="mt-2"
            />
            {selectedCategory && recommendationsData?.data && (
              <p className="text-sm text-muted-foreground mt-2">
                {recommendationsData.data.categories.find(c => c.category === selectedCategory)?.recommendations.length || 0} stocks will be added
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowWatchlistDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={confirmCreateWatchlist}
              disabled={!watchlistName.trim() || createWatchlistMutation.isPending}
            >
              {createWatchlistMutation.isPending ? 'Creating...' : 'Create Watchlist'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// Helper to get category-specific icon
function getCategoryIcon(category: string) {
  switch (category.toLowerCase()) {
    case 'momentum':
      return <TrendingUp className="h-3.5 w-3.5" />;
    case 'breakout':
      return <Zap className="h-3.5 w-3.5" />;
    case 'pullback':
    case 'value':
      return <Target className="h-3.5 w-3.5" />;
    case 'sector':
      return <Flame className="h-3.5 w-3.5" />;
    default:
      return <CircleDot className="h-3.5 w-3.5" />;
  }
}

// Enhanced Win Rate Card with Progress Bar
function WinRateCard({
  label,
  icon,
  winRate,
  avgReturn,
  color,
}: {
  label: string;
  icon: React.ReactNode;
  winRate: number | null;
  avgReturn: number | null;
  color: 'blue' | 'purple' | 'orange';
}) {
  const formatPercent = (val: number | null) =>
    val !== null ? `${val >= 0 ? '+' : ''}${val.toFixed(2)}%` : '-';

  const winRateValue = winRate ?? 0;
  const isPositiveReturn = avgReturn !== null && avgReturn > 0;

  const colorClasses = {
    blue: {
      bg: 'bg-blue-50 dark:bg-blue-950/30',
      icon: 'bg-blue-100 text-blue-600 dark:bg-blue-900/50 dark:text-blue-400',
      progress: 'bg-blue-500',
      text: 'text-blue-600 dark:text-blue-400'
    },
    purple: {
      bg: 'bg-purple-50 dark:bg-purple-950/30',
      icon: 'bg-purple-100 text-purple-600 dark:bg-purple-900/50 dark:text-purple-400',
      progress: 'bg-purple-500',
      text: 'text-purple-600 dark:text-purple-400'
    },
    orange: {
      bg: 'bg-orange-50 dark:bg-orange-950/30',
      icon: 'bg-orange-100 text-orange-600 dark:bg-orange-900/50 dark:text-orange-400',
      progress: 'bg-orange-500',
      text: 'text-orange-600 dark:text-orange-400'
    }
  };

  const colors = colorClasses[color];

  return (
    <div className={cn("rounded-lg p-3 border", colors.bg)}>
      <div className="flex items-center gap-1.5 mb-2">
        <div className={cn("p-1 rounded", colors.icon)}>
          {icon}
        </div>
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
      </div>

      {/* Win Rate with Progress */}
      <div className="mb-2">
        <div className="flex items-baseline justify-between mb-1">
          <span className="text-xl font-bold">
            {winRate !== null ? `${winRate.toFixed(0)}%` : '-'}
          </span>
          <span className="text-xs text-muted-foreground">win rate</span>
        </div>
        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
          <div
            className={cn("h-full rounded-full transition-all duration-500", colors.progress)}
            style={{ width: `${Math.min(winRateValue, 100)}%` }}
          />
        </div>
      </div>

      {/* Average Return */}
      <div className={cn(
        "flex items-center gap-1 text-sm font-medium",
        isPositiveReturn ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
      )}>
        {isPositiveReturn ? (
          <TrendingUp className="h-3.5 w-3.5" />
        ) : avgReturn !== null ? (
          <TrendingDown className="h-3.5 w-3.5" />
        ) : null}
        <span>{formatPercent(avgReturn)} avg</span>
      </div>
    </div>
  );
}

// Compact Win Rate Card for expanded view
function CompactWinRateCard({
  label,
  icon,
  winRate,
  avgReturn,
  color,
}: {
  label: string;
  icon: React.ReactNode;
  winRate: number | null;
  avgReturn: number | null;
  color: 'blue' | 'purple' | 'orange';
}) {
  const formatPercent = (val: number | null) =>
    val !== null ? `${val >= 0 ? '+' : ''}${val.toFixed(1)}%` : '-';

  const isPositiveReturn = avgReturn !== null && avgReturn > 0;
  const winRateValue = winRate ?? 0;

  const colorClasses = {
    blue: { bg: 'bg-blue-50 dark:bg-blue-950/30', icon: 'text-blue-500', progress: 'bg-blue-500' },
    purple: { bg: 'bg-purple-50 dark:bg-purple-950/30', icon: 'text-purple-500', progress: 'bg-purple-500' },
    orange: { bg: 'bg-orange-50 dark:bg-orange-950/30', icon: 'text-orange-500', progress: 'bg-orange-500' }
  };

  const colors = colorClasses[color];

  return (
    <div className={cn("rounded-lg p-2 border", colors.bg)}>
      <div className="flex items-center gap-1 mb-1">
        <span className={colors.icon}>{icon}</span>
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-bold">
          {winRate !== null ? `${winRate.toFixed(0)}%` : '-'}
        </span>
        <span className={cn(
          "text-xs font-medium",
          isPositiveReturn ? "text-green-600 dark:text-green-400" : avgReturn !== null ? "text-red-600 dark:text-red-400" : "text-muted-foreground"
        )}>
          {formatPercent(avgReturn)}
        </span>
      </div>
      <div className="h-1 bg-muted rounded-full overflow-hidden mt-1">
        <div
          className={cn("h-full rounded-full", colors.progress)}
          style={{ width: `${Math.min(winRateValue, 100)}%` }}
        />
      </div>
    </div>
  );
}

import { CategoryPerformanceStats } from '@/lib/api';

function CategoryStats({
  stats,
  recommendations,
  onSaveAsWatchlist,
}: {
  stats: CategoryPerformanceStats;
  recommendations: RecommendationItem[];
  onSaveAsWatchlist: (symbols: string[]) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  const formatPercent = (val: number | null | undefined) =>
    val !== null && val !== undefined ? `${val >= 0 ? '+' : ''}${val.toFixed(1)}%` : '-';

  const getReturnColor = (val: number | null | undefined) => {
    if (val === null || val === undefined) return 'text-muted-foreground';
    return val >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';
  };

  return (
    <div className="space-y-3">
      {/* Top Performers - Compact */}
      {(stats.best_pick_1d || stats.best_pick_1w || stats.best_pick_1m) && (
        <div className="flex flex-wrap gap-1.5">
          <Trophy className="h-3.5 w-3.5 text-amber-500" />
          {stats.best_pick_1d && (
            <Badge variant="secondary" className="text-xs gap-1">
              {stats.best_pick_1d}
              <span className={getReturnColor(stats.best_return_1d)}>{formatPercent(stats.best_return_1d)}</span>
            </Badge>
          )}
          {stats.best_pick_1w && (
            <Badge variant="secondary" className="text-xs gap-1">
              {stats.best_pick_1w}
              <span className={getReturnColor(stats.best_return_1w)}>{formatPercent(stats.best_return_1w)}</span>
            </Badge>
          )}
          {stats.best_pick_1m && (
            <Badge variant="secondary" className="text-xs gap-1">
              {stats.best_pick_1m}
              <span className={getReturnColor(stats.best_return_1m)}>{formatPercent(stats.best_return_1m)}</span>
            </Badge>
          )}
        </div>
      )}

      {/* Expandable Stock List */}
      {recommendations.length > 0 && (
        <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
          <div className="flex items-center justify-between">
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" className="gap-1.5 text-xs h-7 px-2">
                {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                <Eye className="h-3 w-3" />
                {recommendations.length} Stocks
              </Button>
            </CollapsibleTrigger>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs h-7 px-2"
              onClick={() => onSaveAsWatchlist(recommendations.map(r => r.symbol))}
            >
              <Bookmark className="h-3 w-3" />
              Save
            </Button>
          </div>

          <CollapsibleContent className="mt-2">
            <div className="rounded border overflow-hidden text-xs">
              {/* Header */}
              <div className="grid grid-cols-10 gap-1 px-2 py-1.5 bg-muted/50 font-medium text-muted-foreground">
                <div className="col-span-3">Symbol</div>
                <div className="col-span-1 text-right">Score</div>
                <div className="col-span-2 text-right">1D</div>
                <div className="col-span-2 text-right">1W</div>
                <div className="col-span-2 text-right">1M</div>
              </div>
              {/* Rows */}
              <div className="divide-y max-h-48 overflow-y-auto">
                {recommendations.map((rec, idx) => (
                  <div
                    key={rec.symbol}
                    className={cn(
                      "grid grid-cols-10 gap-1 px-2 py-1.5 items-center",
                      idx % 2 === 0 ? "bg-background" : "bg-muted/10"
                    )}
                  >
                    <div className="col-span-3 font-medium flex items-center gap-1">
                      {idx < 3 && <Star className="h-2.5 w-2.5 text-amber-500 fill-amber-500" />}
                      {rec.symbol}
                    </div>
                    <div className="col-span-1 text-right font-mono">{rec.score.toFixed(0)}</div>
                    <div className={cn("col-span-2 text-right font-mono", getReturnColor(rec.return_1d))}>
                      {formatPercent(rec.return_1d)}
                    </div>
                    <div className={cn("col-span-2 text-right font-mono", getReturnColor(rec.return_1w))}>
                      {formatPercent(rec.return_1w)}
                    </div>
                    <div className={cn("col-span-2 text-right font-mono", getReturnColor(rec.return_1m))}>
                      {formatPercent(rec.return_1m)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CollapsibleContent>
        </Collapsible>
      )}

      {/* Fallback */}
      {recommendations.length === 0 && (
        <p className="text-xs text-muted-foreground">{stats.total_recommendations} recommendations</p>
      )}
    </div>
  );
}

