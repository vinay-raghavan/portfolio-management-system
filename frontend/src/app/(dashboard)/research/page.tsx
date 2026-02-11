'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Search,
  TrendingUp,
  TrendingDown,
  Newspaper,
  BarChart3,
  Zap,
  ArrowRight,
} from 'lucide-react';
import { researchApi } from '@/lib/api';
import { cn, formatPercent } from '@/lib/utils';
import { SectorHeatmap, DigestWidget } from '@/components/research';
import type { NewsArticle } from '@/types';

export default function ResearchPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState('overview');

  // Fetch market news
  const { data: newsData, isLoading: newsLoading } = useQuery({
    queryKey: ['research-market-news'],
    queryFn: () => researchApi.getMarketNews(10),
    staleTime: 5 * 60 * 1000,
  });

  const news = newsData?.data?.articles || [];

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/research/${searchQuery.trim().toUpperCase()}`);
    }
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

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Research</h1>
          <p className="text-muted-foreground">Market analysis, news, and stock research</p>
        </div>

        {/* Symbol Search */}
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search symbol..."
              className="pl-9 w-[200px]"
            />
          </div>
          <Button type="submit">Research</Button>
        </form>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="sectors">Sectors</TabsTrigger>
          <TabsTrigger value="news">Market News</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Daily Digest Widget */}
            <DigestWidget />

            {/* Sector Heatmap (compact) */}
            <SectorHeatmap compact />
          </div>

          {/* Latest News */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Newspaper className="h-5 w-5" />
                  Latest Market News
                </CardTitle>
                <CardDescription>Top market-moving headlines</CardDescription>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setActiveTab('news')}>
                View All
                <ArrowRight className="h-4 w-4 ml-1" />
              </Button>
            </CardHeader>
            <CardContent>
              {newsLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Skeleton key={i} className="h-16" />
                  ))}
                </div>
              ) : (
                <div className="space-y-3">
                  {news.slice(0, 5).map((article: NewsArticle, idx: number) => (
                    <a
                      key={idx}
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block p-3 border rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <p className="font-medium line-clamp-1">{article.title}</p>
                          <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                            {article.source && <span>{article.source}</span>}
                            {article.published_at && (
                              <span>{new Date(article.published_at).toLocaleDateString()}</span>
                            )}
                          </div>
                        </div>
                        {article.sentiment && (
                          <Badge className={getSentimentColor(article.sentiment)} variant="outline">
                            {article.sentiment}
                          </Badge>
                        )}
                      </div>
                    </a>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Sectors Tab */}
        <TabsContent value="sectors" className="space-y-6">
          <SectorHeatmap />
        </TabsContent>

        {/* Market News Tab */}
        <TabsContent value="news" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Newspaper className="h-5 w-5" />
                Market News
              </CardTitle>
              <CardDescription>Latest market headlines and analysis</CardDescription>
            </CardHeader>
            <CardContent>
              {newsLoading ? (
                <div className="space-y-4">
                  {Array.from({ length: 10 }).map((_, i) => (
                    <Skeleton key={i} className="h-20" />
                  ))}
                </div>
              ) : news.length > 0 ? (
                <div className="space-y-4">
                  {news.map((article: NewsArticle, idx: number) => (
                    <a
                      key={idx}
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <p className="font-medium line-clamp-2">{article.title}</p>
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
                            {article.related_symbols && article.related_symbols.length > 0 && (
                              <div className="flex gap-1">
                                {article.related_symbols.slice(0, 3).map((sym) => (
                                  <Badge key={sym} variant="outline" className="text-xs">
                                    {sym}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                        {article.sentiment && (
                          <Badge className={getSentimentColor(article.sentiment)}>
                            {article.sentiment}
                          </Badge>
                        )}
                      </div>
                    </a>
                  ))}
                </div>
              ) : (
                <div className="text-center text-muted-foreground py-8">
                  No news articles available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
