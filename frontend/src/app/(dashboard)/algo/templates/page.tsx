'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FileCode2, Plus, Pencil, Trash2, Copy, ArrowLeft } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { useToast } from '@/components/ui/use-toast';
import { autoTradeApi } from '@/lib/api';
import { BrandedSpinner } from '@/components/shared';
import type { StrategyTemplate, StrategyTemplateCreate, StrategyTemplateUpdate } from '@/types';
import Link from 'next/link';

const STRATEGY_TYPES = [
  { value: 'MOMENTUM', label: 'Momentum' },
  { value: 'MEAN_REVERSION', label: 'Mean Reversion' },
  { value: 'BREAKOUT', label: 'Breakout' },
  { value: 'TREND_FOLLOWING', label: 'Trend Following' },
  { value: 'CUSTOM', label: 'Custom' },
];

function TemplateForm({
  template,
  onSave,
  onCancel,
  isLoading,
}: {
  template?: StrategyTemplate;
  onSave: (data: StrategyTemplateCreate | StrategyTemplateUpdate) => void;
  onCancel: () => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState({
    name: template?.name || '',
    description: template?.description || '',
    strategy_type: template?.strategy_type || 'MOMENTUM',
    default_quantity: template?.default_quantity || 1,
    stop_loss_pct: template?.stop_loss_pct || 2,
    take_profit_pct: template?.take_profit_pct || 5,
    trailing_stop_enabled: template?.trailing_stop_enabled || false,
    trailing_stop_pct: template?.trailing_stop_pct || 1.5,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="name">Template Name *</Label>
          <Input
            id="name"
            value={formData.name}
            onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
            placeholder="My Strategy Template"
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="strategy_type">Strategy Type</Label>
          <Select
            value={formData.strategy_type}
            onValueChange={(v) => setFormData(prev => ({ ...prev, strategy_type: v }))}
          >
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {STRATEGY_TYPES.map((t) => (
                <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Textarea
          id="description"
          value={formData.description}
          onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
          placeholder="Describe the strategy template..."
          rows={2}
        />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="default_quantity">Default Quantity</Label>
          <Input
            id="default_quantity"
            type="number"
            min={1}
            value={formData.default_quantity}
            onChange={(e) => setFormData(prev => ({ ...prev, default_quantity: parseInt(e.target.value) || 1 }))}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="stop_loss_pct">Stop Loss (%)</Label>
          <Input
            id="stop_loss_pct"
            type="number"
            min={0.1}
            max={50}
            step={0.1}
            value={formData.stop_loss_pct}
            onChange={(e) => setFormData(prev => ({ ...prev, stop_loss_pct: parseFloat(e.target.value) || 2 }))}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="take_profit_pct">Take Profit (%)</Label>
          <Input
            id="take_profit_pct"
            type="number"
            min={0.1}
            max={100}
            step={0.1}
            value={formData.take_profit_pct}
            onChange={(e) => setFormData(prev => ({ ...prev, take_profit_pct: parseFloat(e.target.value) || 5 }))}
          />
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Switch
            id="trailing_stop_enabled"
            checked={formData.trailing_stop_enabled}
            onCheckedChange={(v) => setFormData(prev => ({ ...prev, trailing_stop_enabled: v }))}
          />
          <Label htmlFor="trailing_stop_enabled">Enable Trailing Stop</Label>
        </div>
        {formData.trailing_stop_enabled && (
          <div className="flex items-center gap-2">
            <Label htmlFor="trailing_stop_pct" className="text-sm">Pct:</Label>
            <Input
              id="trailing_stop_pct"
              type="number"
              min={0.1}
              max={20}
              step={0.1}
              className="w-20"
              value={formData.trailing_stop_pct}
              onChange={(e) => setFormData(prev => ({ ...prev, trailing_stop_pct: parseFloat(e.target.value) || 1.5 }))}
            />
          </div>
        )}
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
        <Button type="submit" disabled={isLoading || !formData.name}>
          {isLoading ? 'Saving...' : template ? 'Update Template' : 'Create Template'}
        </Button>
      </DialogFooter>
    </form>
  );
}

function TemplateCard({
  template,
  onEdit,
  onDuplicate,
  onDelete,
}: {
  template: StrategyTemplate;
  onEdit: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <FileCode2 className="h-5 w-5 text-primary" />
              {template.name}
            </CardTitle>
            <CardDescription className="mt-1">
              {template.description || 'No description'}
            </CardDescription>
          </div>
          <Badge variant="outline">{template.strategy_type}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4 text-sm mb-4">
          <div>
            <p className="text-muted-foreground">Quantity</p>
            <p className="font-medium">{template.default_quantity}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Stop Loss</p>
            <p className="font-medium">{template.stop_loss_pct}%</p>
          </div>
          <div>
            <p className="text-muted-foreground">Take Profit</p>
            <p className="font-medium">{template.take_profit_pct}%</p>
          </div>
        </div>
        {template.trailing_stop_enabled && (
          <Badge variant="secondary" className="mb-3">
            Trailing Stop: {template.trailing_stop_pct}%
          </Badge>
        )}
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onEdit}>
            <Pencil className="h-4 w-4 mr-1" /> Edit
          </Button>
          <Button variant="outline" size="sm" onClick={onDuplicate}>
            <Copy className="h-4 w-4 mr-1" /> Duplicate
          </Button>
          <Button variant="outline" size="sm" className="text-destructive" onClick={onDelete}>
            <Trash2 className="h-4 w-4 mr-1" /> Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function StrategyTemplatesPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<StrategyTemplate | null>(null);
  const [deleteTemplate, setDeleteTemplate] = useState<StrategyTemplate | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['strategy-templates'],
    queryFn: () => autoTradeApi.getTemplates().then(r => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: StrategyTemplateCreate) => autoTradeApi.createTemplate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategy-templates'] });
      setDialogOpen(false);
      toast({ title: 'Template created', description: 'Strategy template saved successfully' });
    },
    onError: () => toast({ title: 'Error', description: 'Failed to create template', variant: 'destructive' }),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: StrategyTemplateUpdate }) =>
      autoTradeApi.updateTemplate(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategy-templates'] });
      setDialogOpen(false);
      setEditingTemplate(null);
      toast({ title: 'Template updated', description: 'Changes saved successfully' });
    },
    onError: () => toast({ title: 'Error', description: 'Failed to update template', variant: 'destructive' }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => autoTradeApi.deleteTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategy-templates'] });
      setDeleteTemplate(null);
      toast({ title: 'Template deleted' });
    },
    onError: () => toast({ title: 'Error', description: 'Failed to delete template', variant: 'destructive' }),
  });

  const handleSave = (formData: StrategyTemplateCreate | StrategyTemplateUpdate) => {
    if (editingTemplate) {
      updateMutation.mutate({ id: editingTemplate.id, data: formData });
    } else {
      createMutation.mutate(formData as StrategyTemplateCreate);
    }
  };

  const handleDuplicate = (template: StrategyTemplate) => {
    createMutation.mutate({
      name: `${template.name} (Copy)`,
      description: template.description,
      strategy_type: template.strategy_type,
      default_quantity: template.default_quantity,
      stop_loss_pct: template.stop_loss_pct,
      take_profit_pct: template.take_profit_pct,
      trailing_stop_enabled: template.trailing_stop_enabled,
      trailing_stop_pct: template.trailing_stop_pct,
      parameters: template.parameters,
    });
  };

  const templates = data?.templates || [];

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><BrandedSpinner size="lg" /></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/settings/auto-trade">
            <Button variant="ghost" size="icon"><ArrowLeft className="h-5 w-5" /></Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <FileCode2 className="h-8 w-8" />
              Strategy Templates
            </h1>
            <p className="text-muted-foreground">Reusable strategy configurations for auto-trading</p>
          </div>
        </div>
        <Button onClick={() => { setEditingTemplate(null); setDialogOpen(true); }}>
          <Plus className="h-4 w-4 mr-2" /> New Template
        </Button>
      </div>

      {templates.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <FileCode2 className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No templates yet</h3>
            <p className="text-muted-foreground mb-4">Create your first strategy template</p>
            <Button onClick={() => setDialogOpen(true)}><Plus className="h-4 w-4 mr-2" /> Create Template</Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {templates.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              onEdit={() => { setEditingTemplate(template); setDialogOpen(true); }}
              onDuplicate={() => handleDuplicate(template)}
              onDelete={() => setDeleteTemplate(template)}
            />
          ))}
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{editingTemplate ? 'Edit Template' : 'Create Template'}</DialogTitle>
            <DialogDescription>
              {editingTemplate ? 'Update strategy template settings' : 'Create a reusable strategy configuration'}
            </DialogDescription>
          </DialogHeader>
          <TemplateForm
            template={editingTemplate || undefined}
            onSave={handleSave}
            onCancel={() => { setDialogOpen(false); setEditingTemplate(null); }}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!deleteTemplate} onOpenChange={() => setDeleteTemplate(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Template</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{deleteTemplate?.name}"? This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground"
              onClick={() => deleteTemplate && deleteMutation.mutate(deleteTemplate.id)}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

