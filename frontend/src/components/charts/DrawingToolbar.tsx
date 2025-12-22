'use client';

import { MousePointer2, TrendingUp, Minus, MoveRight, Square, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import { useDrawingStore, type DrawingToolType } from '@/store';

const DRAWING_COLORS = [
  '#2962FF', // Blue
  '#FF6D00', // Orange
  '#00C853', // Green
  '#D50000', // Red
  '#AA00FF', // Purple
  '#FFD600', // Yellow
  '#00B8D4', // Cyan
  '#FFFFFF', // White
];

const LINE_WIDTHS = [1, 2, 3, 4];

interface DrawingToolbarProps {
  symbol: string;
  onClearDrawings?: () => void;
}

export function DrawingToolbar({ symbol, onClearDrawings }: DrawingToolbarProps) {
  const {
    activeTool,
    setActiveTool,
    drawingColor,
    setDrawingColor,
    lineWidth,
    setLineWidth,
    clearDrawings,
  } = useDrawingStore();

  const handleClearDrawings = () => {
    clearDrawings(symbol);
    onClearDrawings?.();
  };

  const tools: { type: DrawingToolType; icon: React.ReactNode; label: string }[] = [
    { type: 'none', icon: <MousePointer2 className="h-4 w-4" />, label: 'Select' },
    { type: 'trendline', icon: <TrendingUp className="h-4 w-4" />, label: 'Trend Line' },
    { type: 'horizontal', icon: <Minus className="h-4 w-4" />, label: 'Horizontal Line' },
    { type: 'ray', icon: <MoveRight className="h-4 w-4" />, label: 'Ray' },
    { type: 'rectangle', icon: <Square className="h-4 w-4" />, label: 'Rectangle' },
  ];

  return (
    <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-lg">
      {/* Drawing Tools */}
      {tools.map((tool) => (
        <Button
          key={tool.type}
          variant={activeTool === tool.type ? 'secondary' : 'ghost'}
          size="icon"
          className={cn('h-8 w-8', activeTool === tool.type && 'bg-primary/20')}
          onClick={() => setActiveTool(tool.type)}
          title={tool.label}
        >
          {tool.icon}
        </Button>
      ))}

      <Separator orientation="vertical" className="h-6 mx-1" />

      {/* Color Picker */}
      <Popover>
        <PopoverTrigger asChild>
          <Button variant="ghost" size="icon" className="h-8 w-8" title="Line Color">
            <div
              className="h-4 w-4 rounded-full border border-border"
              style={{ backgroundColor: drawingColor }}
            />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-2" align="start">
          <div className="grid grid-cols-4 gap-1">
            {DRAWING_COLORS.map((color) => (
              <button
                key={color}
                className={cn(
                  'h-6 w-6 rounded-full border-2 transition-transform hover:scale-110',
                  drawingColor === color ? 'border-primary' : 'border-transparent'
                )}
                style={{ backgroundColor: color }}
                onClick={() => setDrawingColor(color)}
              />
            ))}
          </div>
        </PopoverContent>
      </Popover>

      {/* Line Width */}
      <Popover>
        <PopoverTrigger asChild>
          <Button variant="ghost" size="icon" className="h-8 w-8" title="Line Width">
            <div className="flex items-center justify-center">
              <div
                className="rounded-full bg-foreground"
                style={{ width: lineWidth * 3, height: lineWidth * 3 }}
              />
            </div>
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-2" align="start">
          <div className="flex gap-2">
            {LINE_WIDTHS.map((width) => (
              <button
                key={width}
                className={cn(
                  'h-8 w-8 rounded flex items-center justify-center border transition-colors',
                  lineWidth === width
                    ? 'border-primary bg-primary/20'
                    : 'border-transparent hover:bg-muted'
                )}
                onClick={() => setLineWidth(width)}
              >
                <div
                  className="rounded-full bg-foreground"
                  style={{ width: width * 3, height: width * 3 }}
                />
              </button>
            ))}
          </div>
        </PopoverContent>
      </Popover>

      <Separator orientation="vertical" className="h-6 mx-1" />

      {/* Clear Drawings */}
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8 text-muted-foreground hover:text-destructive"
        onClick={handleClearDrawings}
        title="Clear All Drawings"
      >
        <Trash2 className="h-4 w-4" />
      </Button>
    </div>
  );
}

