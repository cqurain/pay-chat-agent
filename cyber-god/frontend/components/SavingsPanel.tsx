'use client';

/**
 * Savings panel: two number inputs (已存金额 / 目标金额) with localStorage persistence (D-07, D-08).
 * Reads localStorage after hydration to prevent SSR mismatch.
 * Calls onSavingsChange / onTargetChange to lift state to page.tsx (for useChat body).
 *
 * Implements: SAVINGS-01, SAVINGS-02
 */
import { useEffect, useState } from 'react';
import { STORAGE_KEYS, DEFAULTS } from '@/lib/storage';

interface SavingsPanelProps {
  savings: number;
  target: number;
  onSavingsChange: (value: number) => void;
  onTargetChange: (value: number) => void;
}

export default function SavingsPanel({
  savings,
  target,
  onSavingsChange,
  onTargetChange,
}: SavingsPanelProps) {
  const [isMounted, setIsMounted] = useState(false);

  // Load localStorage after hydration only — prevents SSR/client mismatch
  useEffect(() => {
    setIsMounted(true);
    const storedSavings = Number(localStorage.getItem(STORAGE_KEYS.SAVINGS));
    const storedTarget = Number(localStorage.getItem(STORAGE_KEYS.TARGET));
    if (!isNaN(storedSavings) && storedSavings >= 0) {
      onSavingsChange(storedSavings);
    }
    if (!isNaN(storedTarget) && storedTarget > 0) {
      onTargetChange(storedTarget);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSavingsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Math.max(0, Number(e.target.value) || 0);
    onSavingsChange(val);
    localStorage.setItem(STORAGE_KEYS.SAVINGS, String(val));
  };

  const handleTargetChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Math.max(0, Number(e.target.value) || 0);
    onTargetChange(val);
    localStorage.setItem(STORAGE_KEYS.TARGET, String(val));
  };

  const inputClass =
    'w-32 px-3 py-2 bg-white border border-gray-300 text-gray-900 rounded ' +
    'placeholder-gray-400 focus:outline-none focus:border-yellow-500 text-sm';

  return (
    <div className="shrink-0 border-b border-gray-200 bg-white px-6 py-3">
      {/* Row 1: inputs */}
      <div className="flex gap-8 mb-3">
        <label className="flex flex-col gap-1">
          <span className="text-sm text-gray-600">已存金额</span>
          <input
            type="number"
            min="0"
            value={isMounted ? savings : DEFAULTS.SAVINGS}
            onChange={handleSavingsChange}
            className={inputClass}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm text-gray-600">目标金额</span>
          <input
            type="number"
            min="0"
            value={isMounted ? target : DEFAULTS.TARGET}
            onChange={handleTargetChange}
            className={inputClass}
          />
        </label>
      </div>
      {/* Row 2: progress bar container */}
      {/* ProgressBar is rendered by parent page.tsx, placed here as the target slot */}
    </div>
  );
}
