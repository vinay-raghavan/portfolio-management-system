'use client';

import { useEffect, useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { AlertList, CreateAlertForm, NotificationPreferences } from '@/components/alerts';
import { useUIStore, type Currency } from '@/store';

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

