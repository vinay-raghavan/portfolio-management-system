'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Play, Trash2, Save, Bookmark } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { screenerApi, type FilterConfig, type CustomScreener } from '@/lib/api';
import { useNotificationStore } from '@/store';
import { cn } from '@/lib/utils';

interface SavedScreenersListProps {
  currentFilters: FilterConfig[];
  currentUniverse: string;
  onRunScreener: (screener: CustomScreener) => void;
  onLoadScreener: (screener: CustomScreener) => void;
}

export function SavedScreenersList({
  currentFilters,
  currentUniverse,
  onRunScreener,
  onLoadScreener,
}: SavedScreenersListProps) {
  const [isSaveOpen, setIsSaveOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const queryClient = useQueryClient();
  const { addNotification } = useNotificationStore();

  const { data, isLoading } = useQuery({
    queryKey: ['customScreeners'],
    queryFn: () => screenerApi.getCustomScreeners().then((res) => res.data),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      screenerApi.createCustomScreener({
        name: newName,
        description: newDescription || undefined,
        universe: currentUniverse,
        filters: currentFilters,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customScreeners'] });
      setIsSaveOpen(false);
      setNewName('');
      setNewDescription('');
      addNotification({ type: 'success', title: 'Screener Saved', message: `"${newName}" has been saved` });
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Error',
        message: error.response?.data?.detail || 'Failed to save screener',
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => screenerApi.deleteCustomScreener(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customScreeners'] });
      addNotification({ type: 'success', title: 'Deleted', message: 'Screener has been deleted' });
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Error',
        message: error.response?.data?.detail || 'Failed to delete screener',
      });
    },
  });

  const screeners = data?.screeners ?? [];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Bookmark className="h-5 w-5" />
          Saved Screeners
        </CardTitle>
        <Dialog open={isSaveOpen} onOpenChange={setIsSaveOpen}>
          <DialogTrigger asChild>
            <Button variant="ghost" size="sm" disabled={currentFilters.length === 0}>
              <Save className="h-4 w-4" />
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Save Screener</DialogTitle>
              <DialogDescription>Save your current filter configuration for quick access.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <Input placeholder="Screener name" value={newName} onChange={(e) => setNewName(e.target.value)} />
              <Input
                placeholder="Description (optional)"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
              />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsSaveOpen(false)}>
                Cancel
              </Button>
              <Button onClick={() => createMutation.mutate()} disabled={!newName || createMutation.isPending}>
                {createMutation.isPending ? 'Saving...' : 'Save'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-10 bg-muted rounded animate-pulse" />
            ))}
          </div>
        ) : screeners.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No saved screeners. Configure filters and save for quick access.
          </p>
        ) : (
          <div className="space-y-1">
            {screeners.map((screener: CustomScreener) => (
              <div
                key={screener.id}
                className="flex items-center justify-between p-2 rounded-lg hover:bg-muted cursor-pointer"
                onClick={() => onLoadScreener(screener)}
              >
                <div>
                  <div className="font-medium text-sm">{screener.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {screener.filters.length} filters • {screener.universe}
                  </div>
                </div>
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRunScreener(screener);
                    }}
                    title="Run screener"
                  >
                    <Play className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteMutation.mutate(screener.id);
                    }}
                    title="Delete screener"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

