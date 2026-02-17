'use client';

import { useEffect, useRef, useMemo } from 'react';
import { createChart, IChartApi, ISeriesApi, Time, AreaSeries } from 'lightweight-charts';
import { useChartTheme } from '@/hooks';

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

  // Get theme-aware chart colors
  const { colors, isDark } = useChartTheme();

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
        textColor: colors.text,
      },
      grid: {
        vertLines: { color: colors.grid },
        horzLines: { color: colors.grid },
      },
      rightPriceScale: {
        borderColor: colors.border,
      },
      timeScale: {
        borderColor: colors.border,
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
      lineColor: isPositive ? colors.profit : colors.loss,
      topColor: isPositive ? colors.profitArea : colors.lossArea,
      bottomColor: 'transparent',
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
  }, [chartData, height, colors, isDark, initialCapital, data]);

  // Update chart colors when theme changes
  useEffect(() => {
    if (!chartRef.current) return;

    chartRef.current.applyOptions({
      layout: {
        background: { color: 'transparent' },
        textColor: colors.text,
      },
      grid: {
        vertLines: { color: colors.grid },
        horzLines: { color: colors.grid },
      },
      rightPriceScale: {
        borderColor: colors.border,
      },
      timeScale: {
        borderColor: colors.border,
      },
    });
  }, [colors]);

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

