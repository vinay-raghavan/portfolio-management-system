'use client';

import { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, Loader2, ExternalLink } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { settingsApi, type DataProviderInfo, type DataProviderType } from '@/lib/api';
import { useNotificationStore } from '@/store';

export function DataProviderSettings() {
  const [providers, setProviders] = useState<DataProviderInfo[]>([]);
  const [currentProvider, setCurrentProvider] = useState<DataProviderType>('yahoo');
  const [isAvailable, setIsAvailable] = useState(true);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const { addNotification } = useNotificationStore();

  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    try {
      setLoading(true);
      const [providersRes, settingsRes] = await Promise.all([
        settingsApi.getProviders(),
        settingsApi.getSettings(),
      ]);
      setProviders(providersRes.data.providers);
      setCurrentProvider(settingsRes.data.data_provider);
      setIsAvailable(settingsRes.data.data_provider_available);
      setStatusMessage(settingsRes.data.data_provider_message);
    } catch (error) {
      console.error('Failed to load providers:', error);
      addNotification({
        type: 'error',
        title: 'Error',
        message: 'Failed to load data provider settings',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleProviderChange = async (provider: DataProviderType) => {
    try {
      setSaving(true);
      const response = await settingsApi.updateSettings({ data_provider: provider });
      setCurrentProvider(response.data.data_provider);
      setIsAvailable(response.data.data_provider_available);
      setStatusMessage(response.data.data_provider_message);
      addNotification({
        type: 'success',
        title: 'Settings Updated',
        message: `Data provider changed to ${provider.toUpperCase()}`,
      });
    } catch (error) {
      console.error('Failed to update provider:', error);
      addNotification({
        type: 'error',
        title: 'Error',
        message: 'Failed to update data provider',
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Data Provider</CardTitle>
        <CardDescription>
          Choose your market data source. Fyers provides real-time data if connected.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!isAvailable && statusMessage && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{statusMessage}</AlertDescription>
          </Alert>
        )}

        {isAvailable && statusMessage && (
          <Alert>
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            <AlertDescription>{statusMessage}</AlertDescription>
          </Alert>
        )}

        <RadioGroup
          value={currentProvider}
          onValueChange={(v) => handleProviderChange(v as DataProviderType)}
          disabled={saving}
        >
          {providers.map((provider) => (
            <div
              key={provider.id}
              className={`flex items-start space-x-3 rounded-lg border p-4 ${
                currentProvider === provider.id ? 'border-primary bg-primary/5' : ''
              } ${!provider.is_available && provider.requires_auth ? 'opacity-60' : ''}`}
            >
              <RadioGroupItem
                value={provider.id}
                id={provider.id}
                disabled={!provider.is_available && provider.requires_auth}
              />
              <div className="flex-1 space-y-1">
                <Label
                  htmlFor={provider.id}
                  className="flex items-center gap-2 font-medium cursor-pointer"
                >
                  {provider.name}
                  {provider.requires_auth && (
                    <span className="text-xs text-muted-foreground">(Requires login)</span>
                  )}
                  {provider.is_available && currentProvider === provider.id && (
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                  )}
                </Label>
                <p className="text-sm text-muted-foreground">{provider.description}</p>
                {provider.message && provider.id !== currentProvider && (
                  <p className="text-xs text-amber-600">{provider.message}</p>
                )}
              </div>
            </div>
          ))}
        </RadioGroup>

        {saving && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Saving...
          </div>
        )}
      </CardContent>
    </Card>
  );
}

