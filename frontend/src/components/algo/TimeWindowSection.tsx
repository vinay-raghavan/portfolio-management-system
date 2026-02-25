'use client';

import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Clock } from 'lucide-react';

// Common IANA timezones for trading
const TIMEZONE_OPTIONS = [
  { value: 'Asia/Kolkata', label: 'India (IST)' },
  { value: 'America/New_York', label: 'New York (EST/EDT)' },
  { value: 'America/Chicago', label: 'Chicago (CST/CDT)' },
  { value: 'America/Los_Angeles', label: 'Los Angeles (PST/PDT)' },
  { value: 'Europe/London', label: 'London (GMT/BST)' },
  { value: 'Europe/Paris', label: 'Paris (CET/CEST)' },
  { value: 'Asia/Tokyo', label: 'Tokyo (JST)' },
  { value: 'Asia/Shanghai', label: 'Shanghai (CST)' },
  { value: 'Asia/Singapore', label: 'Singapore (SGT)' },
  { value: 'Australia/Sydney', label: 'Sydney (AEST/AEDT)' },
];

// Days of week (0=Monday, 6=Sunday to match Python weekday())
const DAYS_OF_WEEK = [
  { value: 0, label: 'Mon' },
  { value: 1, label: 'Tue' },
  { value: 2, label: 'Wed' },
  { value: 3, label: 'Thu' },
  { value: 4, label: 'Fri' },
  { value: 5, label: 'Sat' },
  { value: 6, label: 'Sun' },
];

interface TimeWindowSectionProps {
  enabled: boolean;
  onEnabledChange: (enabled: boolean) => void;
  startTime: string;
  onStartTimeChange: (time: string) => void;
  endTime: string;
  onEndTimeChange: (time: string) => void;
  timezone: string;
  onTimezoneChange: (timezone: string) => void;
  activeDays: number[];
  onActiveDaysChange: (days: number[]) => void;
}

export function TimeWindowSection({
  enabled,
  onEnabledChange,
  startTime,
  onStartTimeChange,
  endTime,
  onEndTimeChange,
  timezone,
  onTimezoneChange,
  activeDays,
  onActiveDaysChange,
}: TimeWindowSectionProps) {
  const toggleDay = (day: number) => {
    if (activeDays.includes(day)) {
      onActiveDaysChange(activeDays.filter((d) => d !== day));
    } else {
      onActiveDaysChange([...activeDays, day].sort());
    }
  };

  const selectWeekdays = () => {
    onActiveDaysChange([0, 1, 2, 3, 4]); // Mon-Fri
  };

  const selectAll = () => {
    onActiveDaysChange([0, 1, 2, 3, 4, 5, 6]); // All days
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-muted-foreground" />
          <Label className="text-base font-medium">Trading Time Window</Label>
        </div>
        <Switch checked={enabled} onCheckedChange={onEnabledChange} />
      </div>

      {enabled && (
        <div className="space-y-4 pl-6 border-l-2 border-muted">
          {/* Time Range */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Start Time</Label>
              <Input
                type="time"
                value={startTime}
                onChange={(e) => onStartTimeChange(e.target.value)}
                step="60"
              />
            </div>
            <div className="space-y-2">
              <Label>End Time</Label>
              <Input
                type="time"
                value={endTime}
                onChange={(e) => onEndTimeChange(e.target.value)}
                step="60"
              />
            </div>
          </div>

          {/* Timezone */}
          <div className="space-y-2">
            <Label>Timezone</Label>
            <Select value={timezone} onValueChange={onTimezoneChange}>
              <SelectTrigger>
                <SelectValue placeholder="Select timezone" />
              </SelectTrigger>
              <SelectContent>
                {TIMEZONE_OPTIONS.map((tz) => (
                  <SelectItem key={tz.value} value={tz.value}>
                    {tz.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Active Trading Days */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Active Trading Days</Label>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="text-xs text-muted-foreground hover:text-foreground"
                  onClick={selectWeekdays}
                >
                  Weekdays
                </button>
                <span className="text-xs text-muted-foreground">|</span>
                <button
                  type="button"
                  className="text-xs text-muted-foreground hover:text-foreground"
                  onClick={selectAll}
                >
                  All
                </button>
              </div>
            </div>
            <div className="flex gap-2 flex-wrap">
              {DAYS_OF_WEEK.map((day) => (
                <label
                  key={day.value}
                  className="flex items-center gap-1.5 px-2 py-1 rounded border cursor-pointer hover:bg-muted"
                >
                  <Checkbox
                    checked={activeDays.includes(day.value)}
                    onCheckedChange={() => toggleDay(day.value)}
                  />
                  <span className="text-sm">{day.label}</span>
                </label>
              ))}
            </div>
          </div>

          <p className="text-xs text-muted-foreground">
            Strategy will only execute trades during the specified time window and on active days.
          </p>
        </div>
      )}
    </div>
  );
}

