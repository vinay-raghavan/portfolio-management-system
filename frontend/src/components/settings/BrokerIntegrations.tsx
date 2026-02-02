'use client';

import { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ExternalLink, Check, Loader2, Settings2, Trash2, Unplug } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { brokersApi, type BrokerType, type BrokerCredentialStatus } from '@/lib/api';
import { useNotificationStore } from '@/store';

interface BrokerConfig {
  type: BrokerType;
  name: string;
  description: string;
  logo?: string;
  docsUrl: string;
  defaultRedirectUri: string;
}

const BROKER_CONFIGS: BrokerConfig[] = [
  {
    type: 'fyers',
    name: 'Fyers',
    description: 'Trade stocks, F&O on NSE/BSE with Fyers API v3',
    docsUrl: 'https://myapi.fyers.in/docs/',
    defaultRedirectUri: typeof window !== 'undefined' 
      ? `${window.location.origin}/settings?broker=fyers`
      : 'http://localhost:3001/settings?broker=fyers',
  },
];

export function BrokerIntegrations() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { addNotification } = useNotificationStore();
  const [configDialog, setConfigDialog] = useState<BrokerConfig | null>(null);
  const [deleteDialog, setDeleteDialog] = useState<BrokerCredentialStatus | null>(null);
  const [isProcessingCallback, setIsProcessingCallback] = useState(false);

  // Form state
  const [clientId, setClientId] = useState('');
  const [secretKey, setSecretKey] = useState('');
  const [redirectUri, setRedirectUri] = useState('');

  // Fetch broker statuses
  const { data: brokersData, isLoading } = useQuery({
    queryKey: ['brokers'],
    queryFn: () => brokersApi.listBrokers(),
    select: (res) => res.data,
  });

  // Save credentials mutation
  const saveMutation = useMutation({
    mutationFn: brokersApi.saveCredentials,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brokers'] });
      addNotification({ type: 'success', title: 'Credentials saved', message: 'Broker credentials saved successfully' });
      setConfigDialog(null);
      resetForm();
    },
    onError: (err: Error) => {
      addNotification({ type: 'error', title: 'Save failed', message: err.message });
    },
  });

  // Get auth URL mutation
  const authUrlMutation = useMutation({
    mutationFn: brokersApi.getFyersAuthUrl,
    onSuccess: (res) => {
      // Redirect to Fyers login
      window.location.href = res.data.auth_url;
    },
    onError: (err: Error) => {
      addNotification({ type: 'error', title: 'Auth failed', message: err.message });
    },
  });

  // Disconnect mutation
  const disconnectMutation = useMutation({
    mutationFn: (brokerType: BrokerType) => brokersApi.disconnectBroker(brokerType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brokers'] });
      addNotification({ type: 'info', title: 'Disconnected', message: 'Broker disconnected' });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (brokerType: BrokerType) => brokersApi.deleteBroker(brokerType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brokers'] });
      addNotification({ type: 'info', title: 'Deleted', message: 'Broker credentials deleted' });
      setDeleteDialog(null);
    },
  });

  // Fyers callback mutation
  const fyersCallbackMutation = useMutation({
    mutationFn: brokersApi.fyersCallback,
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['brokers'] });
      addNotification({
        type: 'success',
        title: 'Connected!',
        message: res.data.message,
      });
      setIsProcessingCallback(false);
    },
    onError: (err: Error) => {
      addNotification({
        type: 'error',
        title: 'Connection failed',
        message: err.message,
      });
      setIsProcessingCallback(false);
    },
  });

  // Handle OAuth callback from URL params
  useEffect(() => {
    const authCode = searchParams.get('auth_code');
    const broker = searchParams.get('broker');
    const state = searchParams.get('state');

    // Fyers sometimes returns malformed URLs like ?broker=fyers?s=ok&auth_code=...
    // So we check if broker starts with 'fyers' or if state contains our identifier
    const isFyersCallback = broker?.startsWith('fyers') || state?.includes('portfolio');

    if (authCode && isFyersCallback && !isProcessingCallback) {
      setIsProcessingCallback(true);
      // Clear URL params
      router.replace('/settings?tab=brokers', { scroll: false });
      // Exchange auth code for token
      fyersCallbackMutation.mutate({ auth_code: authCode, state: state || undefined });
    }
  }, [searchParams]);

  const resetForm = () => {
    setClientId('');
    setSecretKey('');
    setRedirectUri('');
  };

  const handleOpenConfig = (config: BrokerConfig) => {
    setRedirectUri(config.defaultRedirectUri);
    setConfigDialog(config);
  };

  const handleSaveCredentials = () => {
    if (!configDialog) return;
    saveMutation.mutate({
      broker_type: configDialog.type,
      client_id: clientId,
      secret_key: secretKey,
      redirect_uri: redirectUri,
    });
  };

  const handleConnect = (brokerType: BrokerType) => {
    if (brokerType === 'fyers') {
      authUrlMutation.mutate();
    }
  };

  const getBrokerStatus = (brokerType: BrokerType): BrokerCredentialStatus | undefined => {
    return brokersData?.brokers.find((b) => b.broker_type === brokerType);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium">Broker Integrations</h3>
        <p className="text-sm text-muted-foreground">
          Connect your broker accounts to enable live trading
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {BROKER_CONFIGS.map((config) => {
          const status = getBrokerStatus(config.type);
          const isConfigured = status?.is_configured ?? false;
          const isConnected = status?.is_connected ?? false;

          return (
            <Card key={config.type}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{config.name}</CardTitle>
                  {isConnected ? (
                    <Badge variant="default" className="bg-green-600">
                      <Check className="mr-1 h-3 w-3" /> Connected
                    </Badge>
                  ) : isConfigured ? (
                    <Badge variant="secondary">
                      <Settings2 className="mr-1 h-3 w-3" /> Configured
                    </Badge>
                  ) : (
                    <Badge variant="outline">Not configured</Badge>
                  )}
                </div>
                <CardDescription>{config.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {!isConfigured && (
                    <Button size="sm" onClick={() => handleOpenConfig(config)}>
                      <Settings2 className="mr-2 h-4 w-4" />
                      Configure
                    </Button>
                  )}
                  {isConfigured && !isConnected && (
                    <>
                      <Button
                        size="sm"
                        onClick={() => handleConnect(config.type)}
                        disabled={authUrlMutation.isPending}
                      >
                        {authUrlMutation.isPending ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <ExternalLink className="mr-2 h-4 w-4" />
                        )}
                        Connect
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => handleOpenConfig(config)}>
                        Edit
                      </Button>
                    </>
                  )}
                  {isConnected && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => disconnectMutation.mutate(config.type)}
                      disabled={disconnectMutation.isPending}
                    >
                      <Unplug className="mr-2 h-4 w-4" />
                      Disconnect
                    </Button>
                  )}
                  {isConfigured && (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-destructive hover:text-destructive"
                      onClick={() => setDeleteDialog(status!)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                  <Button size="sm" variant="ghost" asChild>
                    <a href={config.docsUrl} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="mr-2 h-4 w-4" />
                      Docs
                    </a>
                  </Button>
                </div>
                {status?.last_used_at && (
                  <p className="mt-2 text-xs text-muted-foreground">
                    Last used: {new Date(status.last_used_at).toLocaleDateString()}
                  </p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Configure Dialog */}
      <Dialog open={!!configDialog} onOpenChange={() => { setConfigDialog(null); resetForm(); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Configure {configDialog?.name}</DialogTitle>
            <DialogDescription>
              Enter your API credentials from the {configDialog?.name} developer portal.
              Credentials are encrypted at rest.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="client_id">Client ID / App ID</Label>
              <Input
                id="client_id"
                value={clientId}
                onChange={(e) => setClientId(e.target.value)}
                placeholder="e.g., XXXXX-100"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="secret_key">Secret Key</Label>
              <Input
                id="secret_key"
                type="password"
                value={secretKey}
                onChange={(e) => setSecretKey(e.target.value)}
                placeholder="Your API secret key"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="redirect_uri">Redirect URI</Label>
              <Input
                id="redirect_uri"
                value={redirectUri}
                onChange={(e) => setRedirectUri(e.target.value)}
                placeholder="OAuth callback URL"
              />
              <p className="text-xs text-muted-foreground">
                Must match the redirect URI registered in your {configDialog?.name} app
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setConfigDialog(null); resetForm(); }}>
              Cancel
            </Button>
            <Button
              onClick={handleSaveCredentials}
              disabled={!clientId || !secretKey || !redirectUri || saveMutation.isPending}
            >
              {saveMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save Credentials
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={!!deleteDialog} onOpenChange={() => setDeleteDialog(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete broker credentials?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete your {deleteDialog?.broker_type} credentials.
              You will need to reconfigure the integration to use it again.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleteDialog && deleteMutation.mutate(deleteDialog.broker_type as BrokerType)}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

