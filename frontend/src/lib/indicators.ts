import type { LineData } from 'lightweight-charts';

interface OHLC {
  time: string | number; // string for daily "YYYY-MM-DD", number for Unix timestamp (seconds)
  open: number;
  high: number;
  low: number;
  close: number;
}

/**
 * Calculate Simple Moving Average
 */
export function calculateSMA(data: OHLC[], period: number): LineData[] {
  const result: LineData[] = [];
  
  for (let i = period - 1; i < data.length; i++) {
    let sum = 0;
    for (let j = 0; j < period; j++) {
      sum += data[i - j].close;
    }
    result.push({
      time: data[i].time as any,
      value: sum / period,
    });
  }
  
  return result;
}

/**
 * Calculate Exponential Moving Average
 */
export function calculateEMA(data: OHLC[], period: number): LineData[] {
  const result: LineData[] = [];
  const multiplier = 2 / (period + 1);
  
  // Start with SMA for first value
  let sum = 0;
  for (let i = 0; i < period; i++) {
    sum += data[i].close;
  }
  let ema = sum / period;
  result.push({
    time: data[period - 1].time as any,
    value: ema,
  });
  
  // Calculate EMA for remaining values
  for (let i = period; i < data.length; i++) {
    ema = (data[i].close - ema) * multiplier + ema;
    result.push({
      time: data[i].time as any,
      value: ema,
    });
  }
  
  return result;
}

/**
 * Calculate Bollinger Bands
 */
export function calculateBollingerBands(
  data: OHLC[],
  period: number = 20,
  stdDev: number = 2
): { upper: LineData[]; middle: LineData[]; lower: LineData[] } {
  const upper: LineData[] = [];
  const middle: LineData[] = [];
  const lower: LineData[] = [];
  
  for (let i = period - 1; i < data.length; i++) {
    // Calculate SMA
    let sum = 0;
    for (let j = 0; j < period; j++) {
      sum += data[i - j].close;
    }
    const sma = sum / period;
    
    // Calculate standard deviation
    let squaredDiffSum = 0;
    for (let j = 0; j < period; j++) {
      squaredDiffSum += Math.pow(data[i - j].close - sma, 2);
    }
    const std = Math.sqrt(squaredDiffSum / period);
    
    const time = data[i].time as any;
    middle.push({ time, value: sma });
    upper.push({ time, value: sma + stdDev * std });
    lower.push({ time, value: sma - stdDev * std });
  }
  
  return { upper, middle, lower };
}

/**
 * Calculate RSI
 */
export function calculateRSI(data: OHLC[], period: number = 14): LineData[] {
  const result: LineData[] = [];
  const gains: number[] = [];
  const losses: number[] = [];
  
  // Calculate price changes
  for (let i = 1; i < data.length; i++) {
    const change = data[i].close - data[i - 1].close;
    gains.push(change > 0 ? change : 0);
    losses.push(change < 0 ? -change : 0);
  }
  
  // Calculate initial average gain/loss
  let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period;
  let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period;
  
  // Calculate RSI
  for (let i = period; i < data.length; i++) {
    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
    const rsi = 100 - (100 / (1 + rs));
    
    result.push({
      time: data[i].time as any,
      value: rsi,
    });
    
    // Update averages
    avgGain = (avgGain * (period - 1) + gains[i - 1]) / period;
    avgLoss = (avgLoss * (period - 1) + losses[i - 1]) / period;
  }
  
  return result;
}

