'use client';

import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { TrendingUp } from 'lucide-react';

interface BrandedSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  label?: string;
}

const sizeClasses = {
  sm: 'h-6 w-6',
  md: 'h-8 w-8',
  lg: 'h-12 w-12',
  xl: 'h-16 w-16',
};

const iconSizeClasses = {
  sm: 'h-3 w-3',
  md: 'h-4 w-4',
  lg: 'h-6 w-6',
  xl: 'h-8 w-8',
};

export function BrandedSpinner({ size = 'md', className, label }: BrandedSpinnerProps) {
  return (
    <div className={cn('flex flex-col items-center gap-2', className)} role="status" aria-label={label || 'Loading'}>
      <div className={cn('relative', sizeClasses[size])}>
        {/* Outer spinning ring */}
        <div className={cn(
          'absolute inset-0 rounded-full border-2 border-primary/30 border-t-primary animate-spin',
          sizeClasses[size]
        )} />
        {/* Inner logo icon */}
        <div className="absolute inset-0 flex items-center justify-center">
          <TrendingUp className={cn('text-primary animate-pulse', iconSizeClasses[size])} />
        </div>
      </div>
      {label && <span className="text-sm text-muted-foreground">{label}</span>}
    </div>
  );
}

interface FullPageLoadingProps {
  message?: string;
}

export function FullPageLoading({ message = 'Loading...' }: FullPageLoadingProps) {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm">
      <BrandedSpinner size="xl" />
      <p className="mt-4 text-lg font-medium text-foreground">{message}</p>
    </div>
  );
}

interface SkeletonCardProps {
  className?: string;
  showHeader?: boolean;
  lines?: number;
}

export function SkeletonCard({ className, showHeader = true, lines = 3 }: SkeletonCardProps) {
  return (
    <div className={cn('rounded-lg border bg-card p-4 space-y-3', className)}>
      {showHeader && (
        <div className="flex items-center justify-between">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-4 w-16" />
        </div>
      )}
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className={cn('h-4', i === lines - 1 ? 'w-3/4' : 'w-full')} />
      ))}
    </div>
  );
}

interface SkeletonTableProps {
  rows?: number;
  columns?: number;
  className?: string;
}

export function SkeletonTable({ rows = 5, columns = 4, className }: SkeletonTableProps) {
  return (
    <div className={cn('rounded-lg border', className)}>
      {/* Header */}
      <div className="flex gap-4 p-3 border-b bg-muted/50">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} className="h-4 flex-1" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex gap-4 p-3 border-b last:border-b-0">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={colIndex} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

interface SkeletonChartProps {
  height?: number;
  className?: string;
}

export function SkeletonChart({ height = 300, className }: SkeletonChartProps) {
  return (
    <div className={cn('rounded-lg border bg-card p-4', className)} style={{ height }}>
      <div className="flex justify-between items-center mb-4">
        <Skeleton className="h-5 w-24" />
        <div className="flex gap-2">
          <Skeleton className="h-6 w-12" />
          <Skeleton className="h-6 w-12" />
          <Skeleton className="h-6 w-12" />
        </div>
      </div>
      <div className="flex items-end gap-1 h-[calc(100%-60px)]">
        {/* Deterministic pattern for skeleton chart bars */}
        {[65, 45, 72, 38, 55, 80, 42, 68, 50, 75, 35, 62, 48, 70, 40, 58, 78, 44, 66, 52].map((h, i) => (
          <Skeleton
            key={i}
            className="flex-1"
            style={{ height: `${h}%` }}
          />
        ))}
      </div>
    </div>
  );
}

interface ProgressIndicatorProps {
  value: number;
  label?: string;
  showPercentage?: boolean;
  status?: string;
  className?: string;
}

export function ProgressIndicator({ 
  value, 
  label, 
  showPercentage = true, 
  status,
  className 
}: ProgressIndicatorProps) {
  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex justify-between items-center text-sm">
        {label && <span className="font-medium">{label}</span>}
        {showPercentage && <span className="text-muted-foreground">{Math.round(value)}%</span>}
      </div>
      <Progress value={value} className="h-2" />
      {status && <p className="text-xs text-muted-foreground">{status}</p>}
    </div>
  );
}

