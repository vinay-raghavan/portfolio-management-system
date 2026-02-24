'use client';

import Link from 'next/link';
import { AlertTriangle, RefreshCw, Settings, ExternalLink } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

export interface DataSourceError {
  type: 'auth' | 'connection' | 'rate_limit' | 'unknown';
  provider: string;
  message: string;
}

interface DataSourceErrorBannerProps {
  error: DataSourceError;
  onRetry?: () => void;
  isRetrying?: boolean;
  className?: string;
}

/**
 * Parse error details from API error response to determine if it's a data source issue
 */
export function parseDataSourceError(error: unknown): DataSourceError | null {
  if (!error || typeof error !== 'object') return null;
  
  const err = error as Record<string, unknown>;
  const responseData = (err.response as Record<string, unknown>)?.data as Record<string, unknown>;
  const detail = responseData?.detail as string || err.message as string || '';
  const detailLower = detail.toLowerCase();
  
  // Check for Fyers authentication errors
  if (
    detailLower.includes('could not authenticate') ||
    detailLower.includes('authentication') ||
    detailLower.includes('invalid token') ||
    detailLower.includes('token expired') ||
    detailLower.includes('access_token') ||
    detailLower.includes('unauthorized')
  ) {
    // Try to detect which provider
    if (detailLower.includes('fyers') || detail.includes('FY')) {
      return {
        type: 'auth',
        provider: 'Fyers',
        message: 'Fyers authentication expired. Please re-authenticate to continue using real-time data.',
      };
    }
    return {
      type: 'auth',
      provider: 'Data Provider',
      message: 'Data provider authentication failed. Please check your settings.',
    };
  }
  
  // Check for rate limit errors
  if (detailLower.includes('rate limit') || detailLower.includes('too many requests')) {
    return {
      type: 'rate_limit',
      provider: 'Data Provider',
      message: 'Rate limit exceeded. Please wait a moment before trying again.',
    };
  }
  
  // Check for connection errors
  if (detailLower.includes('connection') || detailLower.includes('timeout') || detailLower.includes('network')) {
    return {
      type: 'connection',
      provider: 'Data Provider',
      message: 'Connection error. Please check your network and try again.',
    };
  }
  
  return null;
}

/**
 * Check if screener results might indicate a data source issue
 * (0 results when screening a large universe)
 */
export function checkScreenerResultsForDataIssue(
  resultsCount: number,
  totalScreened: number,
  universeSize: number | undefined
): DataSourceError | null {
  // If we screened many stocks but got 0 results, and universe is large, might be data issue
  if (
    resultsCount === 0 &&
    totalScreened > 0 &&
    totalScreened === universeSize &&
    totalScreened >= 50
  ) {
    return {
      type: 'unknown',
      provider: 'Data Provider',
      message: 'No stocks passed the filters. If this is unexpected, your data provider connection may need to be refreshed.',
    };
  }
  return null;
}

export function DataSourceErrorBanner({
  error,
  onRetry,
  isRetrying,
  className = '',
}: DataSourceErrorBannerProps) {
  const isAuthError = error.type === 'auth';
  
  return (
    <Alert variant="destructive" className={`border-orange-500/50 bg-orange-500/10 ${className}`}>
      <AlertTriangle className="h-4 w-4" />
      <AlertTitle className="flex items-center gap-2">
        {error.provider} {error.type === 'auth' ? 'Connection Expired' : 'Issue'}
      </AlertTitle>
      <AlertDescription className="mt-2">
        <p className="text-sm mb-3">{error.message}</p>
        <div className="flex flex-wrap gap-2">
          {isAuthError && (
            <Button variant="outline" size="sm" asChild>
              <Link href="/settings" className="flex items-center gap-1">
                <Settings className="h-3 w-3" />
                Go to Settings
                <ExternalLink className="h-3 w-3" />
              </Link>
            </Button>
          )}
          {onRetry && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRetry}
              disabled={isRetrying}
              className="flex items-center gap-1"
            >
              <RefreshCw className={`h-3 w-3 ${isRetrying ? 'animate-spin' : ''}`} />
              {isRetrying ? 'Retrying...' : 'Retry'}
            </Button>
          )}
        </div>
      </AlertDescription>
    </Alert>
  );
}

