'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { AlertList, CreateAlertForm, NotificationPreferences } from '@/components/alerts';
import { BrokerIntegrations, DataProviderSettings } from '@/components/settings';
import { useUIStore, type Currency } from '@/store';
import { Bot, ChevronRight, Settings2, Zap, Clock } from 'lucide-react';

const CURRENCIES: { value: Currency; label: string; symbol: string }[] = [
  { value: 'INR', label: 'Indian Rupee', symbol: '₹' },
  { value: 'USD', label: 'US Dollar', symbol: '$' },
  { value: 'EUR', label: 'Euro', symbol: '€' },
  { value: 'GBP', label: 'British Pound', symbol: '£' },
];

export default function SettingsPage() {
  const [mounted, setMounted] = useState(false);
  const { currency, setCurrency, theme, setTheme } = useUIStore();

  // Prevent hydration mismatch with persisted state
  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Manage your preferences, alerts and notifications</p>
      </div>

      <Tabs defaultValue="general">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="brokers">Broker Integrations</TabsTrigger>
          <TabsTrigger value="auto-trade">Auto-Trade</TabsTrigger>
          <TabsTrigger value="alerts">Price Alerts</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="mt-4">
          <div className="max-w-2xl space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Display Preferences</CardTitle>
                <CardDescription>Customize how information is displayed</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid gap-2">
                  <Label htmlFor="currency">Currency</Label>
                  {mounted ? (
                    <Select
                      value={currency}
                      onValueChange={(v) => setCurrency(v as Currency)}
                    >
                      <SelectTrigger id="currency" className="w-[250px]">
                        <SelectValue placeholder="Select currency" />
                      </SelectTrigger>
                      <SelectContent>
                        {CURRENCIES.map((c) => (
                          <SelectItem key={c.value} value={c.value}>
                            {c.symbol} {c.label} ({c.value})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <div className="h-10 w-[250px] rounded-md border border-input bg-background px-3 py-2 text-sm">
                      Loading...
                    </div>
                  )}
                  <p className="text-sm text-muted-foreground">
                    Currency used for displaying prices and portfolio values
                  </p>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="theme">Theme</Label>
                  {mounted ? (
                    <Select
                      value={theme}
                      onValueChange={(v) => setTheme(v as 'light' | 'dark' | 'system')}
                    >
                      <SelectTrigger id="theme" className="w-[250px]">
                        <SelectValue placeholder="Select theme" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="light">Light</SelectItem>
                        <SelectItem value="dark">Dark</SelectItem>
                        <SelectItem value="system">System</SelectItem>
                      </SelectContent>
                    </Select>
                  ) : (
                    <div className="h-10 w-[250px] rounded-md border border-input bg-background px-3 py-2 text-sm">
                      Loading...
                    </div>
                  )}
                  <p className="text-sm text-muted-foreground">
                    Choose your preferred color theme
                  </p>
                </div>
              </CardContent>
            </Card>

            <DataProviderSettings />
          </div>
        </TabsContent>

        <TabsContent value="brokers" className="mt-4">
          <div className="max-w-4xl">
            <BrokerIntegrations />
          </div>
        </TabsContent>

        <TabsContent value="auto-trade" className="mt-4">
          <div className="max-w-4xl space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bot className="h-5 w-5" />
                  Auto-Trade Settings
                </CardTitle>
                <CardDescription>
                  Configure automated trading rules based on screener results and recommendations
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <Card className="border-dashed">
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-3 mb-3">
                        <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                          <Settings2 className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <h4 className="font-medium">Category Rules</h4>
                          <p className="text-sm text-muted-foreground">Configure per-category settings</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="border-dashed">
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-3 mb-3">
                        <div className="h-10 w-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                          <Zap className="h-5 w-5 text-blue-500" />
                        </div>
                        <div>
                          <h4 className="font-medium">Multi-Factor Scoring</h4>
                          <p className="text-sm text-muted-foreground">Technical, fundamental &amp; sentiment</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="border-dashed">
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-3 mb-3">
                        <div className="h-10 w-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                          <Clock className="h-5 w-5 text-green-500" />
                        </div>
                        <div>
                          <h4 className="font-medium">Scheduled Runs</h4>
                          <p className="text-sm text-muted-foreground">Set daily run times</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                <div className="pt-4">
                  <Button asChild>
                    <Link href="/settings/auto-trade" className="flex items-center gap-2">
                      <Bot className="h-4 w-4" />
                      Open Auto-Trade Settings
                      <ChevronRight className="h-4 w-4" />
                    </Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="alerts" className="mt-4">
          <div className="grid gap-6 md:grid-cols-[1fr_350px]">
            <AlertList />
            <CreateAlertForm />
          </div>
        </TabsContent>

        <TabsContent value="notifications" className="mt-4">
          <div className="max-w-2xl">
            <NotificationPreferences />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

