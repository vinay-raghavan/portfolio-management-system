'use client';

import { useEffect, useRef, useMemo } from 'react';
import { createChart, IChartApi, ISeriesApi, Time, AreaSeries } from 'lightweight-charts';
import { useTheme } from 'next-themes';

interface EquityPoint {
  date: string;
  equity: number;
}

interface EquityCurveChartProps {
  data: EquityPoint[];
  initialCapital: number;
  height?: number;
}

export function EquityCurveChart({
  data,
  initialCapital,
  height = 300,
}: EquityCurveChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Area'> | null>(null);
  const { theme } = useTheme();

  const isDark = theme === 'dark';

  const chartData = useMemo(() => {
    return data.map((point) => ({
      time: point.date.split('T')[0] as Time,
      value: point.equity,
    }));
  }, [data]);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height,
      layout: {
        background: { color: 'transparent' },
        textColor: isDark ? '#a1a1aa' : '#71717a',
      },
      grid: {
        vertLines: { color: isDark ? '#27272a' : '#e4e4e7' },
        horzLines: { color: isDark ? '#27272a' : '#e4e4e7' },
      },
      rightPriceScale: {
        borderColor: isDark ? '#27272a' : '#e4e4e7',
      },
      timeScale: {
        borderColor: isDark ? '#27272a' : '#e4e4e7',
        timeVisible: true,
      },
      crosshair: {
        mode: 1,
      },
    });

    chartRef.current = chart;

    // Determine if overall performance is positive
    const lastEquity = data.length > 0 ? data[data.length - 1].equity : initialCapital;
    const isPositive = lastEquity >= initialCapital;

    const series = chart.addSeries(AreaSeries, {
      lineColor: isPositive ? '#22c55e' : '#ef4444',
      topColor: isPositive ? 'rgba(34, 197, 94, 0.4)' : 'rgba(239, 68, 68, 0.4)',
      bottomColor: isPositive ? 'rgba(34, 197, 94, 0.0)' : 'rgba(239, 68, 68, 0.0)',
      lineWidth: 2,
      priceFormat: {
        type: 'price',
        precision: 2,
        minMove: 0.01,
      },
    });

    seriesRef.current = series;
    series.setData(chartData);

    // Add initial capital line
    series.createPriceLine({
      price: initialCapital,
      color: isDark ? '#71717a' : '#a1a1aa',
      lineWidth: 1,
      lineStyle: 2, // Dashed
      axisLabelVisible: true,
      title: 'Initial',
    });

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [chartData, height, isDark, initialCapital, data]);

  // Update chart colors when theme changes
  useEffect(() => {
    if (!chartRef.current) return;

    chartRef.current.applyOptions({
      layout: {
        background: { color: 'transparent' },
        textColor: isDark ? '#a1a1aa' : '#71717a',
      },
      grid: {
        vertLines: { color: isDark ? '#27272a' : '#e4e4e7' },
        horzLines: { color: isDark ? '#27272a' : '#e4e4e7' },
      },
      rightPriceScale: {
        borderColor: isDark ? '#27272a' : '#e4e4e7',
      },
      timeScale: {
        borderColor: isDark ? '#27272a' : '#e4e4e7',
      },
    });
  }, [isDark]);

  return (
    <div className="w-full">
      <div ref={chartContainerRef} className="w-full" style={{ height }} />
      <div className="flex justify-between text-xs text-muted-foreground mt-2">
        <span>Initial: ${initialCapital.toLocaleString()}</span>
        {data.length > 0 && (
          <span>
            Final: ${data[data.length - 1].equity.toLocaleString()} (
            {(((data[data.length - 1].equity - initialCapital) / initialCapital) * 100).toFixed(2)}
            %)
          </span>
        )}
      </div>
    </div>
  );
}

