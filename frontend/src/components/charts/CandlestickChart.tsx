'use client';

import { useEffect, useRef, useCallback } from 'react';
import {
  createChart,
  ColorType,
  CrosshairMode,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type HistogramData,
  type LineData,
  type Time,
  type MouseEventParams,
} from 'lightweight-charts';
import { useDrawingStore, type Drawing, type DrawingPoint } from '@/store';
import { useChartTheme } from '@/hooks';

interface ChartData {
  time: string | number; // string for daily "YYYY-MM-DD", number for Unix timestamp (seconds)
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface Indicator {
  type: 'sma' | 'ema' | 'bb';
  period: number;
  color: string;
  data?: LineData<Time>[];
}

interface CandlestickChartProps {
  data: ChartData[];
  indicators?: Indicator[];
  showVolume?: boolean;
  height?: number;
  symbol?: string;
  enableDrawing?: boolean;
}

export function CandlestickChart({
  data,
  indicators = [],
  showVolume = true,
  height = 400,
  symbol = '',
  enableDrawing = false,
}: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const indicatorSeriesRef = useRef<ISeriesApi<'Line'>[]>([]);
  const drawingSeriesRef = useRef<ISeriesApi<'Line'>[]>([]);

  const {
    activeTool,
    drawingColor,
    lineWidth,
    drawings,
    addDrawing,
    isDrawing,
    setIsDrawing,
    currentDrawingPoints,
    addDrawingPoint,
    clearCurrentDrawing,
  } = useDrawingStore();

  // Get theme-aware chart colors
  const { colors, isDark } = useChartTheme();

  useEffect(() => {
    if (!containerRef.current) return;

    // Create chart with theme-aware colors
    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: colors.background },
        textColor: colors.text,
      },
      grid: {
        vertLines: { color: colors.grid },
        horzLines: { color: colors.grid },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: colors.border,
      },
      timeScale: {
        borderColor: colors.border,
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // Create candlestick series with theme-aware colors
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: colors.profit,
      downColor: colors.loss,
      borderUpColor: colors.profit,
      borderDownColor: colors.loss,
      wickUpColor: colors.profit,
      wickDownColor: colors.loss,
    });
    candleSeriesRef.current = candleSeries;

    // Create volume series with theme-aware color
    if (showVolume) {
      const volumeSeries = chart.addSeries(HistogramSeries, {
        color: colors.volume,
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
      });
      volumeSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      });
      volumeSeriesRef.current = volumeSeries;
    }

    // Handle resize
    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [height, colors, showVolume]);

  // Update data with theme-aware volume colors
  useEffect(() => {
    if (!candleSeriesRef.current || data.length === 0) return;

    const candleData: CandlestickData<Time>[] = data.map((d) => ({
      time: d.time as Time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));

    candleSeriesRef.current.setData(candleData);

    if (volumeSeriesRef.current) {
      const volumeData: HistogramData<Time>[] = data.map((d) => ({
        time: d.time as Time,
        value: d.volume,
        color: d.close >= d.open ? `${colors.profit}50` : `${colors.loss}50`,
      }));
      volumeSeriesRef.current.setData(volumeData);
    }

    // Fit content
    chartRef.current?.timeScale().fitContent();
  }, [data, colors.profit, colors.loss]);

  // Update indicators
  useEffect(() => {
    if (!chartRef.current) return;

    // Remove old indicator series
    indicatorSeriesRef.current.forEach((series) => {
      try {
        if (series && chartRef.current) {
          chartRef.current.removeSeries(series);
        }
      } catch {
        // Series might already be removed
      }
    });
    indicatorSeriesRef.current = [];

    // Add new indicator series
    indicators.forEach((indicator) => {
      if (indicator.data && indicator.data.length > 0) {
        const series = chartRef.current!.addSeries(LineSeries, {
          color: indicator.color,
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        series.setData(indicator.data);
        indicatorSeriesRef.current.push(series);
      }
    });
  }, [indicators]);

  // Render saved drawings as line series
  useEffect(() => {
    if (!chartRef.current || !enableDrawing) return;

    // Remove old drawing series
    drawingSeriesRef.current.forEach((series) => {
      try {
        if (series && chartRef.current) {
          chartRef.current.removeSeries(series);
        }
      } catch {
        // Series might already be removed
      }
    });
    drawingSeriesRef.current = [];

    // Get drawings for this symbol
    const symbolDrawings = drawings.filter((d) => d.symbol === symbol);

    // Render each drawing
    symbolDrawings.forEach((drawing) => {
      if (drawing.type === 'horizontal') {
        // Horizontal line only needs one point
        if (drawing.points.length < 1) return;
        // Horizontal line - extends across visible range
        const series = chartRef.current!.addSeries(LineSeries, {
          color: drawing.color,
          lineWidth: drawing.lineWidth as 1 | 2 | 3 | 4,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        });
        // Create line data spanning first and last data points
        if (data.length >= 2) {
          const lineData: LineData<Time>[] = [
            { time: data[0].time as Time, value: drawing.points[0].price },
            { time: data[data.length - 1].time as Time, value: drawing.points[0].price },
          ];
          series.setData(lineData);
          drawingSeriesRef.current.push(series);
        }
      } else if (drawing.type === 'trendline' || drawing.type === 'ray') {
        // Trend line or ray requires 2 points
        if (drawing.points.length < 2) return;
        const series = chartRef.current!.addSeries(LineSeries, {
          color: drawing.color,
          lineWidth: drawing.lineWidth as 1 | 2 | 3 | 4,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        });
        const lineData: LineData<Time>[] = drawing.points.map((p) => ({
          time: p.time,
          value: p.price,
        }));
        series.setData(lineData);
        drawingSeriesRef.current.push(series);
      }
    });
  }, [drawings, symbol, enableDrawing, data]);

  // Handle drawing clicks
  const handleChartClick = useCallback(
    (param: MouseEventParams) => {
      if (!enableDrawing || activeTool === 'none' || !param.time || !param.point) return;
      if (!candleSeriesRef.current) return;

      // Get the price at click position
      const price = candleSeriesRef.current.coordinateToPrice(param.point.y);
      if (price === null) return;

      const point: DrawingPoint = { time: param.time, price };

      if (activeTool === 'horizontal') {
        // Horizontal line only needs one click
        const newDrawing: Drawing = {
          id: `drawing-${Date.now()}`,
          type: 'horizontal',
          points: [point],
          color: drawingColor,
          lineWidth,
          symbol,
        };
        addDrawing(newDrawing);
      } else if (activeTool === 'trendline' || activeTool === 'ray') {
        if (!isDrawing) {
          // First click - start drawing
          setIsDrawing(true);
          addDrawingPoint(point);
        } else {
          // Second click - complete drawing
          const newDrawing: Drawing = {
            id: `drawing-${Date.now()}`,
            type: activeTool,
            points: [...currentDrawingPoints, point],
            color: drawingColor,
            lineWidth,
            symbol,
          };
          addDrawing(newDrawing);
          clearCurrentDrawing();
        }
      }
    },
    [
      enableDrawing,
      activeTool,
      drawingColor,
      lineWidth,
      symbol,
      isDrawing,
      currentDrawingPoints,
      addDrawing,
      addDrawingPoint,
      setIsDrawing,
      clearCurrentDrawing,
    ]
  );

  // Subscribe to chart clicks for drawing
  useEffect(() => {
    if (!chartRef.current || !enableDrawing) return;

    chartRef.current.subscribeClick(handleChartClick);

    return () => {
      chartRef.current?.unsubscribeClick(handleChartClick);
    };
  }, [enableDrawing, handleChartClick]);

  // Change cursor based on active tool
  useEffect(() => {
    if (!containerRef.current) return;

    if (enableDrawing && activeTool !== 'none') {
      containerRef.current.style.cursor = 'crosshair';
    } else {
      containerRef.current.style.cursor = 'default';
    }
  }, [enableDrawing, activeTool]);

  // Generate chart description for screen readers
  const chartDescription = symbol
    ? `Candlestick chart for ${symbol}. This chart shows price movements over time with candlestick patterns${showVolume ? ' and volume' : ''}.`
    : 'Candlestick chart showing price movements over time.';

  return (
    <div
      ref={containerRef}
      className="w-full"
      role="img"
      aria-label={chartDescription}
      tabIndex={0}
    >
      <span className="sr-only">{chartDescription}</span>
    </div>
  );
}

