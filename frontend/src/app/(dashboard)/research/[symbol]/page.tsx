'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Newspaper,
  Users,
  StickyNote,
  Star,
  Plus,
  Bell,
  ShoppingCart,
  RefreshCw,
  ExternalLink,
  Trash2,
  Edit,
} from 'lucide-react';
import { researchApi, marketDataApi, watchlistApi } from '@/lib/api';
import { cn, formatPercent, formatCompactNumber } from '@/lib/utils';
import { useNotificationStore, useUIStore } from '@/store';
import { useCurrency } from '@/hooks';
import type {
  FundamentalsResponse,
  NewsArticle,
  PeerStock,
  ResearchNote,
  ResearchNoteCreate,
} from '@/types';

export default function StockResearchPage() {
  const params = useParams();
  const router = useRouter();
  const symbol = (params.symbol as string)?.toUpperCase() || '';
  const queryClient = useQueryClient();
  const { addNotification } = useNotificationStore();
  const { setSelectedSymbol } = useUIStore();
  const { format: formatPrice } = useCurrency();

  const [activeTab, setActiveTab] = useState('technical');
  const [noteDialogOpen, setNoteDialogOpen] = useState(false);
  const [editingNote, setEditingNote] = useState<ResearchNote | null>(null);
  const [noteForm, setNoteForm] = useState<Partial<ResearchNoteCreate>>({
    symbol,
    title: '',
    content: '',
    rating: 'hold',
    target_price: undefined,
    tags: [],
  });

  // Fetch stock quote
  const { data: quoteData, isLoading: quoteLoading } = useQuery({
    queryKey: ['quote', symbol],
    queryFn: () => marketDataApi.getQuote(symbol),
    enabled: !!symbol,
    staleTime: 30 * 1000,
  });

  // Fetch fundamentals
  const { data: fundamentalsData, isLoading: fundamentalsLoading } = useQuery({
    queryKey: ['research-fundamentals', symbol],
    queryFn: () => researchApi.getFundamentals(symbol),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,
  });

  // Fetch news
  const { data: newsData, isLoading: newsLoading } = useQuery({
    queryKey: ['research-news', symbol],
    queryFn: () => researchApi.getNews(symbol, 20),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,
  });

  // Fetch peers
  const { data: peersData, isLoading: peersLoading } = useQuery({
    queryKey: ['research-peers', symbol],
    queryFn: () => researchApi.getPeers(symbol, 10),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,
  });

  // Fetch notes
  const { data: notesData, isLoading: notesLoading, refetch: refetchNotes } = useQuery({
    queryKey: ['research-notes', symbol],
    queryFn: () => researchApi.getNotes(symbol),
    enabled: !!symbol,
    staleTime: 60 * 1000,
  });

  const quote = quoteData?.data;
  const fundamentals = fundamentalsData?.data;
  const news = newsData?.data?.articles || [];
  const peers = peersData?.data?.peers || [];
  const notes = notesData?.data?.notes || [];

  // Create note mutation
  const createNoteMutation = useMutation({
    mutationFn: (data: ResearchNoteCreate) => researchApi.createNote(data),
    onSuccess: () => {
      addNotification({ type: 'success', title: 'Note Created', message: 'Research note saved' });
      setNoteDialogOpen(false);
      resetNoteForm();
      refetchNotes();
    },
    onError: () => {
      addNotification({ type: 'error', title: 'Error', message: 'Failed to save note' });
    },
  });

  // Update note mutation
  const updateNoteMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ResearchNoteCreate> }) =>
      researchApi.updateNote(id, data),
    onSuccess: () => {
      addNotification({ type: 'success', title: 'Note Updated', message: 'Research note updated' });
      setNoteDialogOpen(false);
      setEditingNote(null);
      resetNoteForm();
      refetchNotes();
    },
    onError: () => {
      addNotification({ type: 'error', title: 'Error', message: 'Failed to update note' });
    },
  });

  // Delete note mutation
  const deleteNoteMutation = useMutation({
    mutationFn: (id: string) => researchApi.deleteNote(id),
    onSuccess: () => {
      addNotification({ type: 'success', title: 'Note Deleted', message: 'Research note deleted' });
      refetchNotes();
    },
    onError: () => {
      addNotification({ type: 'error', title: 'Error', message: 'Failed to delete note' });
    },
  });

  const resetNoteForm = () => {
    setNoteForm({ symbol, title: '', content: '', rating: 'hold', target_price: undefined, tags: [] });
  };

  const handleSaveNote = () => {
    const data: ResearchNoteCreate = {
      symbol,
      title: noteForm.title || '',
      content: noteForm.content || '',
      rating: noteForm.rating,
      target_price: noteForm.target_price,
      tags: noteForm.tags,
    };
    if (editingNote) {
      updateNoteMutation.mutate({ id: editingNote.id, data });
    } else {
      createNoteMutation.mutate(data);
    }
  };

  const handleEditNote = (note: ResearchNote) => {
    setEditingNote(note);
    setNoteForm({
      symbol: note.symbol,
      title: note.title,
      content: note.content,
      rating: note.rating || 'hold',
      target_price: note.target_price ?? undefined,
      tags: note.tags || [],
    });
    setNoteDialogOpen(true);
  };

  const getSentimentColor = (sentiment: string | null | undefined): string => {
    if (!sentiment) return 'bg-gray-100 text-gray-800';
    switch (sentiment.toLowerCase()) {
      case 'positive':
      case 'bullish':
        return 'bg-green-100 text-green-800';
      case 'negative':
      case 'bearish':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-yellow-100 text-yellow-800';
    }
  };

  const getRatingColor = (rating: string | null | undefined): string => {
    if (!rating) return 'bg-gray-100 text-gray-800';
    switch (rating.toLowerCase()) {
      case 'buy':
      case 'strong buy':
        return 'bg-green-100 text-green-800';
      case 'sell':
      case 'strong sell':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-yellow-100 text-yellow-800';
    }
  };

  if (!symbol) {
    return (
      <div className="p-6 text-center text-muted-foreground">
        No symbol specified
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header Section */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{symbol}</h1>
              {quote && (
                <Badge variant={quote.change_pct >= 0 ? 'default' : 'destructive'}>
                  {quote.change_pct >= 0 ? <TrendingUp className="h-3 w-3 mr-1" /> : <TrendingDown className="h-3 w-3 mr-1" />}
                  {formatPercent(quote.change_pct)}
                </Badge>
              )}
            </div>
            {quoteLoading ? (
              <Skeleton className="h-4 w-40 mt-1" />
            ) : (
              <p className="text-muted-foreground">
                {fundamentals?.sector} • {fundamentals?.industry}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {quote && (
            <div className="text-right mr-4">
              <div className="text-2xl font-bold">{formatPrice(quote.ltp)}</div>
              <div className={cn('text-sm', quote.change >= 0 ? 'text-green-600' : 'text-red-600')}>
                {quote.change >= 0 ? '+' : ''}{formatPrice(quote.change)}
              </div>
            </div>
          )}
          <Button variant="outline" size="sm" onClick={() => setSelectedSymbol(symbol)}>
            <ShoppingCart className="h-4 w-4 mr-1" />
            Trade
          </Button>
          <Button variant="outline" size="sm">
            <Star className="h-4 w-4 mr-1" />
            Watchlist
          </Button>
          <Button variant="outline" size="sm">
            <Bell className="h-4 w-4 mr-1" />
            Alert
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="technical" className="flex items-center gap-1">
            <BarChart3 className="h-4 w-4" />
            Technical
          </TabsTrigger>
          <TabsTrigger value="fundamental" className="flex items-center gap-1">
            <TrendingUp className="h-4 w-4" />
            Fundamental
          </TabsTrigger>
          <TabsTrigger value="news" className="flex items-center gap-1">
            <Newspaper className="h-4 w-4" />
            News
          </TabsTrigger>
          <TabsTrigger value="peers" className="flex items-center gap-1">
            <Users className="h-4 w-4" />
            Peers
          </TabsTrigger>
          <TabsTrigger value="notes" className="flex items-center gap-1">
            <StickyNote className="h-4 w-4" />
            Notes ({notes.length})
          </TabsTrigger>
        </TabsList>

        {/* Technical Analysis Tab */}
        <TabsContent value="technical" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Technical Analysis</CardTitle>
              <CardDescription>Price chart with technical indicators</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[400px] flex items-center justify-center bg-muted/50 rounded-lg">
                <div className="text-center text-muted-foreground">
                  <BarChart3 className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>Chart placeholder - Navigate to Analysis page for full charting</p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-4"
                    onClick={() => {
                      setSelectedSymbol(symbol);
                      router.push('/analysis');
                    }}
                  >
                    Open in Analysis
                    <ExternalLink className="h-4 w-4 ml-2" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick Technical Stats */}
          {fundamentals && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card>
                <CardContent className="p-4">
                  <div className="text-sm text-muted-foreground">52W High</div>
                  <div className="text-lg font-bold">{formatPrice(fundamentals.fifty_two_week_high)}</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="text-sm text-muted-foreground">52W Low</div>
                  <div className="text-lg font-bold">{formatPrice(fundamentals.fifty_two_week_low)}</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="text-sm text-muted-foreground">Avg Volume</div>
                  <div className="text-lg font-bold">{formatCompactNumber(fundamentals.avg_volume)}</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="text-sm text-muted-foreground">Beta</div>
                  <div className="text-lg font-bold">{fundamentals.beta?.toFixed(2) || '-'}</div>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>



        {/* Fundamental Analysis Tab */}
        <TabsContent value="fundamental" className="space-y-4">
          {fundamentalsLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Array.from({ length: 12 }).map((_, i) => (
                <Skeleton key={i} className="h-20" />
              ))}
            </div>
          ) : fundamentals ? (
            <>
              {/* Valuation Metrics */}
              <Card>
                <CardHeader>
                  <CardTitle>Valuation Metrics</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <div className="text-sm text-muted-foreground">P/E Ratio</div>
                      <div className="text-lg font-bold">{fundamentals.pe_ratio?.toFixed(2) || '-'}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Forward P/E</div>
                      <div className="text-lg font-bold">{fundamentals.forward_pe?.toFixed(2) || '-'}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">P/B Ratio</div>
                      <div className="text-lg font-bold">{fundamentals.pb_ratio?.toFixed(2) || '-'}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">P/S Ratio</div>
                      <div className="text-lg font-bold">{fundamentals.ps_ratio?.toFixed(2) || '-'}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">PEG Ratio</div>
                      <div className="text-lg font-bold">{fundamentals.peg_ratio?.toFixed(2) || '-'}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Market Cap</div>
                      <div className="text-lg font-bold">{formatCompactNumber(fundamentals.market_cap)}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Enterprise Value</div>
                      <div className="text-lg font-bold">{formatCompactNumber(fundamentals.enterprise_value)}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Profitability Metrics */}
              <Card>
                <CardHeader>
                  <CardTitle>Profitability</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <div className="text-sm text-muted-foreground">EPS</div>
                      <div className="text-lg font-bold">{formatPrice(fundamentals.eps)}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">EPS Growth</div>
                      <div className={cn('text-lg font-bold', (fundamentals.eps_growth ?? 0) >= 0 ? 'text-green-600' : 'text-red-600')}>
                        {formatPercent(fundamentals.eps_growth)}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Revenue</div>
                      <div className="text-lg font-bold">{formatCompactNumber(fundamentals.revenue)}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Revenue Growth</div>
                      <div className={cn('text-lg font-bold', (fundamentals.revenue_growth ?? 0) >= 0 ? 'text-green-600' : 'text-red-600')}>
                        {formatPercent(fundamentals.revenue_growth)}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Profit Margin</div>
                      <div className="text-lg font-bold">{formatPercent(fundamentals.profit_margin)}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Operating Margin</div>
                      <div className="text-lg font-bold">{formatPercent(fundamentals.operating_margin)}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">ROE</div>
                      <div className="text-lg font-bold">{formatPercent(fundamentals.roe)}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">ROA</div>
                      <div className="text-lg font-bold">{formatPercent(fundamentals.roa)}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Financial Health */}
              <Card>
                <CardHeader>
                  <CardTitle>Financial Health & Dividends</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <div className="text-sm text-muted-foreground">Debt/Equity</div>
                      <div className="text-lg font-bold">{fundamentals.debt_to_equity?.toFixed(2) || '-'}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Current Ratio</div>
                      <div className="text-lg font-bold">{fundamentals.current_ratio?.toFixed(2) || '-'}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Dividend Yield</div>
                      <div className="text-lg font-bold">{formatPercent(fundamentals.dividend_yield)}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Payout Ratio</div>
                      <div className="text-lg font-bold">{formatPercent(fundamentals.payout_ratio)}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card>
              <CardContent className="p-6 text-center text-muted-foreground">
                No fundamental data available
              </CardContent>
            </Card>
          )}
        </TabsContent>


        {/* News & Sentiment Tab */}
        <TabsContent value="news" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recent News</CardTitle>
              <CardDescription>Latest news articles for {symbol}</CardDescription>
            </CardHeader>
            <CardContent>
              {newsLoading ? (
                <div className="space-y-4">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Skeleton key={i} className="h-20" />
                  ))}
                </div>
              ) : news.length > 0 ? (
                <div className="space-y-4">
                  {news.map((article: NewsArticle, idx: number) => (
                    <div key={idx} className="p-4 border rounded-lg hover:bg-muted/50 transition-colors">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <a
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-medium hover:underline line-clamp-2"
                          >
                            {article.title}
                          </a>
                          {article.summary && (
                            <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                              {article.summary}
                            </p>
                          )}
                          <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                            {article.source && <span>{article.source}</span>}
                            {article.published_at && (
                              <span>{new Date(article.published_at).toLocaleDateString()}</span>
                            )}
                          </div>
                        </div>
                        {article.sentiment && (
                          <Badge className={getSentimentColor(article.sentiment)}>
                            {article.sentiment}
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-muted-foreground py-8">
                  No news articles found
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Peer Comparison Tab */}
        <TabsContent value="peers" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Peer Comparison</CardTitle>
              <CardDescription>Compare {symbol} with industry peers</CardDescription>
            </CardHeader>
            <CardContent>
              {peersLoading ? (
                <Skeleton className="h-64" />
              ) : peers.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Symbol</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead className="text-right">Price</TableHead>
                      <TableHead className="text-right">Change %</TableHead>
                      <TableHead className="text-right">P/E</TableHead>
                      <TableHead className="text-right">Market Cap</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {peers.map((peer: PeerStock) => (
                      <TableRow key={peer.symbol} className="cursor-pointer hover:bg-muted/50"
                        onClick={() => router.push(`/research/${peer.symbol}`)}>
                        <TableCell className="font-medium">{peer.symbol}</TableCell>
                        <TableCell className="max-w-[200px] truncate">{peer.name}</TableCell>
                        <TableCell className="text-right">{formatPrice(peer.close)}</TableCell>
                        <TableCell className={cn(
                          'text-right font-medium',
                          peer.change_pct >= 0 ? 'text-green-600' : 'text-red-600'
                        )}>
                          {formatPercent(peer.change_pct)}
                        </TableCell>
                        <TableCell className="text-right">{peer.pe_ratio?.toFixed(2) || '-'}</TableCell>
                        <TableCell className="text-right">{formatCompactNumber(peer.market_cap)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center text-muted-foreground py-8">
                  No peer data available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>


        {/* Notes Tab */}
        <TabsContent value="notes" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Research Notes</CardTitle>
                <CardDescription>Your personal research notes for {symbol}</CardDescription>
              </div>
              <Dialog open={noteDialogOpen} onOpenChange={(open) => {
                setNoteDialogOpen(open);
                if (!open) {
                  setEditingNote(null);
                  resetNoteForm();
                }
              }}>
                <DialogTrigger asChild>
                  <Button size="sm">
                    <Plus className="h-4 w-4 mr-1" />
                    Add Note
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl">
                  <DialogHeader>
                    <DialogTitle>{editingNote ? 'Edit Note' : 'New Research Note'}</DialogTitle>
                    <DialogDescription>
                      Save your research findings for {symbol}
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div>
                      <Label>Title</Label>
                      <Input
                        value={noteForm.title || ''}
                        onChange={(e) => setNoteForm({ ...noteForm, title: e.target.value })}
                        placeholder="Note title..."
                      />
                    </div>
                    <div>
                      <Label>Content</Label>
                      <Textarea
                        value={noteForm.content || ''}
                        onChange={(e) => setNoteForm({ ...noteForm, content: e.target.value })}
                        placeholder="Your research notes..."
                        rows={6}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label>Rating</Label>
                        <Select
                          value={noteForm.rating || 'hold'}
                          onValueChange={(v) => setNoteForm({ ...noteForm, rating: v })}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="strong buy">Strong Buy</SelectItem>
                            <SelectItem value="buy">Buy</SelectItem>
                            <SelectItem value="hold">Hold</SelectItem>
                            <SelectItem value="sell">Sell</SelectItem>
                            <SelectItem value="strong sell">Strong Sell</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label>Target Price</Label>
                        <Input
                          type="number"
                          value={noteForm.target_price || ''}
                          onChange={(e) => setNoteForm({ ...noteForm, target_price: e.target.value ? Number(e.target.value) : undefined })}
                          placeholder="Optional target price..."
                        />
                      </div>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setNoteDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button onClick={handleSaveNote} disabled={!noteForm.title || !noteForm.content}>
                      {editingNote ? 'Update' : 'Save'} Note
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              {notesLoading ? (
                <div className="space-y-4">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <Skeleton key={i} className="h-24" />
                  ))}
                </div>
              ) : notes.length > 0 ? (
                <div className="space-y-4">
                  {notes.map((note: ResearchNote) => (
                    <div key={note.id} className="p-4 border rounded-lg">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <h4 className="font-medium">{note.title}</h4>
                            {note.rating && (
                              <Badge className={getRatingColor(note.rating)}>
                                {note.rating}
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground mt-1 whitespace-pre-wrap">
                            {note.content}
                          </p>
                          <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                            {note.target_price && (
                              <span>Target: {formatPrice(note.target_price)}</span>
                            )}
                            <span>{new Date(note.updated_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleEditNote(note)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => deleteNoteMutation.mutate(note.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-muted-foreground py-8">
                  <StickyNote className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>No research notes yet</p>
                  <p className="text-sm">Click &quot;Add Note&quot; to save your first note</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}