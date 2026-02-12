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
  // Real-time data provider
  const [currentProvider, setCurrentProvider] = useState<DataProviderType>('yahoo');
  const [isAvailable, setIsAvailable] = useState(true);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  // Research/Fundamental data provider
  const [researchProvider, setResearchProvider] = useState<DataProviderType>('yahoo');
  const [researchAvailable, setResearchAvailable] = useState(true);
  const [researchMessage, setResearchMessage] = useState<string | null>(null);
  // Loading states
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingResearch, setSavingResearch] = useState(false);
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
      // Real-time provider
      setCurrentProvider(settingsRes.data.data_provider);
      setIsAvailable(settingsRes.data.data_provider_available);
      setStatusMessage(settingsRes.data.data_provider_message);
      // Research provider
      setResearchProvider(settingsRes.data.research_data_provider);
      setResearchAvailable(settingsRes.data.research_data_provider_available);
      setResearchMessage(settingsRes.data.research_data_provider_message);
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
        message: `Real-time data provider changed to ${provider.toUpperCase()}`,
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

  const handleResearchProviderChange = async (provider: DataProviderType) => {
    try {
      setSavingResearch(true);
      const response = await settingsApi.updateSettings({ research_data_provider: provider });
      setResearchProvider(response.data.research_data_provider);
      setResearchAvailable(response.data.research_data_provider_available);
      setResearchMessage(response.data.research_data_provider_message);
      addNotification({
        type: 'success',
        title: 'Settings Updated',
        message: `Research data provider changed to ${provider.toUpperCase()}`,
      });
    } catch (error) {
      console.error('Failed to update research provider:', error);
      addNotification({
        type: 'error',
        title: 'Error',
        message: 'Failed to update research data provider',
      });
    } finally {
      setSavingResearch(false);
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

  // Render a provider radio group section
  const renderProviderOptions = (
    selected: DataProviderType,
    onChange: (p: DataProviderType) => void,
    isSaving: boolean,
    idPrefix: string
  ) => (
    <RadioGroup
      value={selected}
      onValueChange={(v) => onChange(v as DataProviderType)}
      disabled={isSaving}
    >
      {providers.map((provider) => (
        <div
          key={`${idPrefix}-${provider.id}`}
          className={`flex items-start space-x-3 rounded-lg border p-4 ${
            selected === provider.id ? 'border-primary bg-primary/5' : ''
          } ${!provider.is_available && provider.requires_auth ? 'opacity-60' : ''}`}
        >
          <RadioGroupItem
            value={provider.id}
            id={`${idPrefix}-${provider.id}`}
            disabled={!provider.is_available && provider.requires_auth}
          />
          <div className="flex-1 space-y-1">
            <Label
              htmlFor={`${idPrefix}-${provider.id}`}
              className="flex items-center gap-2 font-medium cursor-pointer"
            >
              {provider.name}
              {provider.requires_auth && (
                <span className="text-xs text-muted-foreground">(Requires login)</span>
              )}
              {provider.is_available && selected === provider.id && (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              )}
            </Label>
            <p className="text-sm text-muted-foreground">{provider.description}</p>
            {provider.message && provider.id !== selected && (
              <p className="text-xs text-amber-600">{provider.message}</p>
            )}
          </div>
        </div>
      ))}
    </RadioGroup>
  );

  return (
    <div className="space-y-6">
      {/* Real-time Data Provider */}
      <Card>
        <CardHeader>
          <CardTitle>Real-time Data Provider</CardTitle>
          <CardDescription>
            Choose your source for real-time quotes and price data. Fyers provides live data if connected.
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

          {renderProviderOptions(currentProvider, handleProviderChange, saving, 'realtime')}

          {saving && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Saving...
            </div>
          )}
        </CardContent>
      </Card>

      {/* Research/Fundamental Data Provider */}
      <Card>
        <CardHeader>
          <CardTitle>Research Data Provider</CardTitle>
          <CardDescription>
            Choose your source for fundamental data used in Research and Recommendations.
            Yahoo is recommended as it provides the most comprehensive fundamental data.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!researchAvailable && researchMessage && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{researchMessage}</AlertDescription>
            </Alert>
          )}

          {researchAvailable && researchMessage && (
            <Alert>
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <AlertDescription>{researchMessage}</AlertDescription>
            </Alert>
          )}

          {renderProviderOptions(researchProvider, handleResearchProviderChange, savingResearch, 'research')}

          {savingResearch && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Saving...
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

