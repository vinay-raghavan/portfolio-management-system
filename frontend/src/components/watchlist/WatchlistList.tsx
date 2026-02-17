'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragEndEvent } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Plus, Trash2, Star, GripVertical } from 'lucide-react';
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
import { watchlistApi } from '@/lib/api';
import { useNotificationStore } from '@/store';
import { cn } from '@/lib/utils';
import type { Watchlist } from '@/types';

interface WatchlistListProps {
  selectedId: string | null;
  onSelect: (id: string) => void;
}

interface SortableWatchlistItemProps {
  watchlist: Watchlist;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}

function SortableWatchlistItem({ watchlist, selectedId, onSelect, onDelete }: SortableWatchlistItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: watchlist.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors',
        selectedId === watchlist.id ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'
      )}
      onClick={() => onSelect(watchlist.id)}
    >
      <div className="flex items-center gap-2">
        <button
          className={cn('cursor-grab touch-none', selectedId === watchlist.id ? 'text-primary-foreground/70' : 'text-muted-foreground')}
          {...attributes}
          {...listeners}
          onClick={(e) => e.stopPropagation()}
        >
          <GripVertical className="h-4 w-4" />
        </button>
        <div>
          <div className="font-medium text-sm">{watchlist.name}</div>
          <div className={cn('text-xs', selectedId === watchlist.id ? 'text-primary-foreground/70' : 'text-muted-foreground')}>
            {watchlist.items_count} symbols
          </div>
        </div>
      </div>
      <Button
        variant="ghost"
        size="sm"
        className={cn('h-8 w-8 p-0', selectedId === watchlist.id && 'hover:bg-primary-foreground/10')}
        onClick={(e) => { e.stopPropagation(); onDelete(watchlist.id); }}
      >
        <Trash2 className="h-4 w-4" />
      </Button>
    </div>
  );
}

export function WatchlistList({ selectedId, onSelect }: WatchlistListProps) {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const queryClient = useQueryClient();
  const { addNotification } = useNotificationStore();

  const { data, isLoading } = useQuery({
    queryKey: ['watchlists'],
    queryFn: () => watchlistApi.getWatchlists().then((res) => res.data),
  });

  const createMutation = useMutation({
    mutationFn: () => watchlistApi.createWatchlist({ name: newName, description: newDescription || undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlists'] });
      setIsCreateOpen(false);
      setNewName('');
      setNewDescription('');
      addNotification({ type: 'success', title: 'Watchlist Created', message: `"${newName}" has been created` });
    },
    onError: (error: any) => {
      addNotification({ type: 'error', title: 'Error', message: error.response?.data?.detail || 'Failed to create watchlist' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => watchlistApi.deleteWatchlist(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlists'] });
      addNotification({ type: 'success', title: 'Watchlist Deleted', message: 'Watchlist has been deleted' });
    },
    onError: (error: any) => {
      addNotification({ type: 'error', title: 'Error', message: error.response?.data?.detail || 'Failed to delete watchlist' });
    },
  });

  const reorderMutation = useMutation({
    mutationFn: (items: { id: string; sort_order: number }[]) => watchlistApi.reorderWatchlists(items),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlists'] });
    },
    onError: (error: unknown) => {
      const err = error as { response?: { data?: { detail?: string } } };
      addNotification({ type: 'error', title: 'Error', message: err.response?.data?.detail || 'Failed to reorder watchlists' });
    },
  });

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const watchlists = data?.watchlists ?? [];

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = watchlists.findIndex((w) => w.id === active.id);
      const newIndex = watchlists.findIndex((w) => w.id === over.id);
      const reordered = arrayMove(watchlists, oldIndex, newIndex);
      const items = reordered.map((w, index) => ({ id: w.id, sort_order: index }));
      reorderMutation.mutate(items);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Star className="h-5 w-5" />
            Watchlists
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-10 bg-muted rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Star className="h-5 w-5" />
          Watchlists
        </CardTitle>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button variant="ghost" size="sm">
              <Plus className="h-4 w-4" />
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Watchlist</DialogTitle>
              <DialogDescription>Create a new watchlist to track your favorite stocks.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <Input
                placeholder="Watchlist name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
              <Input
                placeholder="Description (optional)"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
              />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateOpen(false)}>Cancel</Button>
              <Button onClick={() => createMutation.mutate()} disabled={!newName || createMutation.isPending}>
                {createMutation.isPending ? 'Creating...' : 'Create'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardHeader>
      <CardContent>
        {watchlists.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No watchlists yet. Create one to get started.
          </p>
        ) : (
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={watchlists.map((w) => w.id)} strategy={verticalListSortingStrategy}>
              <div className="space-y-1">
                {watchlists.map((watchlist: Watchlist) => (
                  <SortableWatchlistItem
                    key={watchlist.id}
                    watchlist={watchlist}
                    selectedId={selectedId}
                    onSelect={onSelect}
                    onDelete={(id) => deleteMutation.mutate(id)}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        )}
      </CardContent>
    </Card>
  );
}

