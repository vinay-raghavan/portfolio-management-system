'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { templateApi } from '@/lib/api';
import { useTradingStore, useNotificationStore } from '@/store';
import { cn } from '@/lib/utils';
import { BookmarkIcon, Star, ChevronDown, Plus, Trash2 } from 'lucide-react';
import type { OrderTemplate, OrderTemplateCreate, OrderSide, OrderType } from '@/types';

interface TemplateSelectorProps {
  onTemplateSelect?: (template: OrderTemplate) => void;
}

export function TemplateSelector({ onTemplateSelect }: TemplateSelectorProps) {
  const queryClient = useQueryClient();
  const { formState, updateForm } = useTradingStore();
  const { addNotification } = useNotificationStore();
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [templateName, setTemplateName] = useState('');
  const [isFavorite, setIsFavorite] = useState(false);

  const { data: templateData, isLoading } = useQuery({
    queryKey: ['orderTemplates'],
    queryFn: () => templateApi.getTemplates().then((res) => res.data),
  });

  const templates = templateData?.templates || [];
  const favorites = templates.filter((t) => t.is_favorite);
  const others = templates.filter((t) => !t.is_favorite);

  const createMutation = useMutation({
    mutationFn: (data: OrderTemplateCreate) => templateApi.createTemplate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orderTemplates'] });
      addNotification({ type: 'success', title: 'Template Saved', message: `Template "${templateName}" saved successfully` });
      setShowSaveDialog(false);
      setTemplateName('');
      setIsFavorite(false);
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      addNotification({ type: 'error', title: 'Save Failed', message: error.response?.data?.detail || 'Failed to save template' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => templateApi.deleteTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orderTemplates'] });
      addNotification({ type: 'success', title: 'Template Deleted', message: 'Template deleted successfully' });
    },
  });

  const handleSelectTemplate = (template: OrderTemplate) => {
    updateForm({
      symbol: template.symbol,
      side: template.side,
      orderType: template.order_type,
      quantity: template.quantity || 1,
    });
    onTemplateSelect?.(template);
    addNotification({ type: 'info', title: 'Template Applied', message: `Using template "${template.name}"` });
  };

  const handleSaveTemplate = () => {
    if (!templateName.trim() || !formState.symbol) {
      addNotification({ type: 'error', title: 'Validation Error', message: 'Template name and symbol are required' });
      return;
    }
    createMutation.mutate({
      name: templateName,
      symbol: formState.symbol,
      side: formState.side,
      order_type: formState.orderType,
      quantity: formState.quantity || null,
      stop_loss_pct: formState.stopLoss ? null : null,
      take_profit_pct: formState.takeProfit ? null : null,
      is_favorite: isFavorite,
    });
  };

  return (
    <div className="flex items-center gap-2 mb-4" role="group" aria-label="Order templates">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="h-8 gap-1" disabled={isLoading}>
            <BookmarkIcon className="h-4 w-4" aria-hidden="true" />
            <span>Templates</span>
            <ChevronDown className="h-3 w-3 opacity-50" aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-56">
          {favorites.length > 0 && (
            <>
              <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">Favorites</div>
              {favorites.map((template) => (
                <DropdownMenuItem key={template.id} className="flex items-center justify-between cursor-pointer" onSelect={() => handleSelectTemplate(template)}>
                  <span className="flex items-center gap-2">
                    <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" aria-hidden="true" />
                    <span>{template.name}</span>
                  </span>
                  <span className={cn('text-xs', template.side === 'BUY' ? 'text-profit' : 'text-loss')}>{template.side}</span>
                </DropdownMenuItem>
              ))}
              <DropdownMenuSeparator />
            </>
          )}
          {others.length > 0 && (
            <>
              <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">All Templates</div>
              {others.map((template) => (
                <DropdownMenuItem key={template.id} className="flex items-center justify-between cursor-pointer" onSelect={() => handleSelectTemplate(template)}>
                  <span>{template.name}</span>
                  <span className={cn('text-xs', template.side === 'BUY' ? 'text-profit' : 'text-loss')}>{template.side}</span>
                </DropdownMenuItem>
              ))}
              <DropdownMenuSeparator />
            </>
          )}
          {templates.length === 0 && (
            <div className="px-2 py-4 text-sm text-muted-foreground text-center">No templates saved yet</div>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={showSaveDialog} onOpenChange={setShowSaveDialog}>
        <DialogTrigger asChild>
          <Button variant="ghost" size="sm" className="h-8 gap-1" disabled={!formState.symbol} title="Save current settings as template">
            <Plus className="h-4 w-4" aria-hidden="true" />
            <span className="sr-only sm:not-sr-only">Save</span>
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save Order Template</DialogTitle>
            <DialogDescription>Save your current order settings as a reusable template.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="template-name">Template Name</Label>
              <Input id="template-name" value={templateName} onChange={(e) => setTemplateName(e.target.value)} placeholder="e.g., Quick AAPL Buy" />
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" id="is-favorite" checked={isFavorite} onChange={(e) => setIsFavorite(e.target.checked)} className="h-4 w-4 rounded border-gray-300" />
              <Label htmlFor="is-favorite" className="font-normal cursor-pointer">Add to favorites</Label>
            </div>
            <div className="p-3 bg-muted rounded-lg text-sm space-y-1">
              <div className="flex justify-between"><span className="text-muted-foreground">Symbol:</span><span className="font-medium">{formState.symbol || '-'}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Side:</span><span className={cn('font-medium', formState.side === 'BUY' ? 'text-profit' : 'text-loss')}>{formState.side}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Type:</span><span className="font-medium">{formState.orderType}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Quantity:</span><span className="font-medium">{formState.quantity || '-'}</span></div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSaveDialog(false)}>Cancel</Button>
            <Button onClick={handleSaveTemplate} disabled={createMutation.isPending || !templateName.trim()}>{createMutation.isPending ? 'Saving...' : 'Save Template'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

