'use client';

import { useMemo } from 'react';
import { ArrowDown, GitMerge } from 'lucide-react';
import type { CombineLogic, CompositeStrategyComponent } from '@/types';

interface CompositeFlowDiagramProps {
  components: CompositeStrategyComponent[];
  combineLogic: CombineLogic;
  minAgreementPct?: number;
}

const logicLabels: Record<CombineLogic, string> = {
  AND: 'All Must Agree (AND)',
  OR: 'Any Triggers (OR)',
  MAJORITY: 'Majority Vote',
  WEIGHTED: 'Weighted Sum',
};

const logicColors: Record<CombineLogic, string> = {
  AND: 'bg-blue-500',
  OR: 'bg-green-500',
  MAJORITY: 'bg-purple-500',
  WEIGHTED: 'bg-orange-500',
};

export function CompositeFlowDiagram({
  components,
  combineLogic,
  minAgreementPct = 0.5,
}: CompositeFlowDiagramProps) {
  const validComponents = useMemo(
    () => components.filter((c) => c.strategy),
    [components]
  );

  if (validComponents.length === 0) {
    return (
      <div className="p-4 text-center text-muted-foreground text-sm">
        Select strategies to see the flow diagram
      </div>
    );
  }

  const totalWeight = validComponents.reduce((sum, c) => sum + (c.weight || 1), 0);

  return (
    <div className="p-4 space-y-3">
      {/* Component Strategies */}
      <div className="flex flex-wrap justify-center gap-3">
        {validComponents.map((comp, idx) => {
          const weightPct = combineLogic === 'WEIGHTED' 
            ? Math.round(((comp.weight || 1) / totalWeight) * 100) 
            : null;
          return (
            <div
              key={idx}
              className="flex flex-col items-center"
            >
              <div className="px-4 py-2 rounded-lg border-2 border-primary bg-primary/10 text-center min-w-[100px]">
                <div className="font-medium text-sm capitalize">{comp.strategy}</div>
                {combineLogic === 'WEIGHTED' && (
                  <div className="text-xs text-muted-foreground mt-0.5">
                    Weight: {comp.weight || 1} ({weightPct}%)
                  </div>
                )}
                {comp.required && (
                  <div className="text-xs text-red-500 mt-0.5">Required</div>
                )}
              </div>
              <ArrowDown className="h-4 w-4 text-muted-foreground mt-1" />
            </div>
          );
        })}
      </div>

      {/* Combine Logic Node */}
      <div className="flex flex-col items-center">
        <div className={`flex items-center gap-2 px-4 py-2 rounded-lg text-white ${logicColors[combineLogic]}`}>
          <GitMerge className="h-4 w-4" />
          <span className="font-medium text-sm">{logicLabels[combineLogic]}</span>
          {combineLogic === 'MAJORITY' && (
            <span className="text-xs opacity-80">({Math.round(minAgreementPct * 100)}% min)</span>
          )}
        </div>
        <ArrowDown className="h-4 w-4 text-muted-foreground mt-1" />
      </div>

      {/* Final Signal Output */}
      <div className="flex justify-center">
        <div className="px-6 py-3 rounded-lg bg-gradient-to-r from-green-500 to-emerald-600 text-white text-center">
          <div className="font-semibold">Final Signal</div>
          <div className="text-xs opacity-80 mt-0.5">BUY / SELL / HOLD</div>
        </div>
      </div>

      {/* Legend */}
      <div className="mt-4 p-3 bg-muted/50 rounded-lg">
        <div className="text-xs text-muted-foreground space-y-1">
          {combineLogic === 'AND' && (
            <p>All {validComponents.length} strategies must agree on the same signal direction.</p>
          )}
          {combineLogic === 'OR' && (
            <p>Any single strategy signal is enough to trigger the final signal.</p>
          )}
          {combineLogic === 'MAJORITY' && (
            <p>At least {Math.ceil(validComponents.length * minAgreementPct)} of {validComponents.length} strategies must agree.</p>
          )}
          {combineLogic === 'WEIGHTED' && (
            <p>Signals are weighted by their assigned weights. Stronger weighted signals have more influence.</p>
          )}
        </div>
      </div>
    </div>
  );
}

