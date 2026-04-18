'use client';

/**
 * Gold progress bar showing savings / target percentage (D-09).
 * Flashes red for 1.5s when delta < 0 (purchase approved, savings decrease) (D-10).
 *
 * Implements: PROGRESS-01, PROGRESS-02, PROGRESS-03
 */
import { useEffect, useState } from 'react';

interface ProgressBarProps {
  savings: number;
  target: number;
  delta?: number; // undefined until 2: arrives; negative triggers red flash
}

export default function ProgressBar({ savings, target, delta }: ProgressBarProps) {
  const [isFlashing, setIsFlashing] = useState(false);
  const [prevDelta, setPrevDelta] = useState<number | undefined>(undefined);

  // Trigger red flash when a new negative delta arrives (D-10)
  useEffect(() => {
    if (delta !== undefined && delta !== prevDelta) {
      setPrevDelta(delta);
      if (delta < 0) {
        setIsFlashing(true);
        const timer = setTimeout(() => setIsFlashing(false), 1500);
        return () => clearTimeout(timer);
      }
    }
  }, [delta]); // eslint-disable-line react-hooks/exhaustive-deps

  const pct = target > 0 ? Math.min((savings / target) * 100, 100) : 0;
  const displayPct = Math.round(pct);

  return (
    <div className="px-6 py-2 shrink-0 bg-gray-950">
      {/* Track */}
      <div className="w-full h-8 bg-gray-800 rounded overflow-hidden relative">
        {/* Fill — transitions width smoothly (D-09) */}
        <div
          className={`
            h-full flex items-center justify-center
            transition-all duration-500
            ${isFlashing ? 'animate-[flash-red_1.5s_ease-in-out_1] bg-red-600' : 'bg-yellow-500'}
          `}
          style={{ width: `${displayPct}%`, minWidth: displayPct > 0 ? '2rem' : '0' }}
          role="progressbar"
          aria-valuenow={displayPct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`储蓄进度 ${displayPct}%`}
        >
          {displayPct > 5 && (
            <span className="text-sm font-semibold text-gray-900">{displayPct}%</span>
          )}
        </div>
        {/* Show pct outside bar when fill is too narrow */}
        {displayPct <= 5 && (
          <span className="absolute left-2 top-1/2 -translate-y-1/2 text-sm font-semibold text-gray-400">
            {displayPct}%
          </span>
        )}
      </div>
    </div>
  );
}
