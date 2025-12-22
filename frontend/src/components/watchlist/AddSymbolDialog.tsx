'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Search } from 'lucide-react';
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
import { useSymbolSearch } from '@/hooks';
import { useNotificationStore } from '@/store';
import { cn } from '@/lib/utils';
import type { SearchResult } from '@/types';

interface AddSymbolDialogProps {
  watchlistId: string | null;
}

export function AddSymbolDialog({ watchlistId }: AddSymbolDialogProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const { addNotification } = useNotificationStore();

  const { query, setQuery, results, isLoading, clear } = useSymbolSearch({
    minLength: 1,
    debounceMs: 300,
  });

  const addMutation = useMutation({
    mutationFn: (symbol: string) => watchlistApi.addItem(watchlistId!, symbol),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist', watchlistId] });
      queryClient.invalidateQueries({ queryKey: ['watchlists'] });
      addNotification({
        type: 'success',
        title: 'Symbol Added',
        message: `${selectedSymbol} has been added to the watchlist`,
      });
      handleClose();
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Error',
        message: error.response?.data?.detail || 'Failed to add symbol',
      });
    },
  });

  const handleClose = () => {
    setIsOpen(false);
    setSelectedSymbol(null);
    clear();
  };

  const handleAdd = () => {
    if (selectedSymbol) {
      addMutation.mutate(selectedSymbol);
    }
  };

  const handleSelectResult = (result: SearchResult) => {
    setSelectedSymbol(result.symbol);
    setQuery(result.symbol);
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => open ? setIsOpen(true) : handleClose()}>
      <DialogTrigger asChild>
        <Button disabled={!watchlistId}>
          <Plus className="h-4 w-4 mr-2" />
          Add Symbol
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add Symbol</DialogTitle>
          <DialogDescription>
            Search for a stock symbol to add to your watchlist.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search symbols..."
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSelectedSymbol(null);
              }}
              className="pl-10"
            />
          </div>

          {/* Search Results */}
          {query.length > 0 && (
            <div className="max-h-60 overflow-y-auto border rounded-lg">
              {isLoading ? (
                <div className="p-4 text-center text-muted-foreground">
                  Searching...
                </div>
              ) : results.length === 0 ? (
                <div className="p-4 text-center text-muted-foreground">
                  No results found
                </div>
              ) : (
                <div className="divide-y">
                  {results.map((result: SearchResult) => (
                    <div
                      key={result.symbol}
                      className={cn(
                        'p-3 cursor-pointer hover:bg-muted transition-colors',
                        selectedSymbol === result.symbol && 'bg-primary/10'
                      )}
                      onClick={() => handleSelectResult(result)}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="font-medium">{result.symbol}</div>
                          <div className="text-sm text-muted-foreground truncate max-w-[250px]">
                            {result.name}
                          </div>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {result.exchange}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            onClick={handleAdd}
            disabled={!selectedSymbol || addMutation.isPending}
          >
            {addMutation.isPending ? 'Adding...' : 'Add Symbol'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

