'use client';

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
  const [amount, setAmount] = useState('');

  useEffect(() => {
    setIsMounted(true);
    const storedSavings = Number(localStorage.getItem(STORAGE_KEYS.SAVINGS));
    const storedTarget = Number(localStorage.getItem(STORAGE_KEYS.TARGET));
    if (!isNaN(storedSavings) && storedSavings >= 0) onSavingsChange(storedSavings);
    if (!isNaN(storedTarget) && storedTarget > 0) onTargetChange(storedTarget);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const persist = (val: number) => {
    onSavingsChange(val);
    localStorage.setItem(STORAGE_KEYS.SAVINGS, String(val));
  };

  const handleSavingsInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Math.max(0, Number(e.target.value) || 0);
    persist(val);
  };

  const handleTargetChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Math.max(0, Number(e.target.value) || 0);
    onTargetChange(val);
    localStorage.setItem(STORAGE_KEYS.TARGET, String(val));
  };

  const handleDeposit = () => {
    const delta = parseFloat(amount);
    if (!delta || delta <= 0) return;
    persist(Math.max(0, savings + delta));
    setAmount('');
  };

  const handleWithdraw = () => {
    const delta = parseFloat(amount);
    if (!delta || delta <= 0) return;
    persist(Math.max(0, savings - delta));
    setAmount('');
  };

  const inputClass =
    'w-32 px-3 py-2 bg-white border border-gray-300 text-gray-900 rounded ' +
    'placeholder-gray-400 focus:outline-none focus:border-yellow-500 text-sm';

  return (
    <div className="shrink-0 border-b border-gray-200 bg-white px-6 py-3 space-y-3">
      {/* Row 1: goal inputs */}
      <div className="flex gap-8">
        <label className="flex flex-col gap-1">
          <span className="text-sm text-gray-600">已存金额</span>
          <input
            type="number"
            min="0"
            value={isMounted ? savings : DEFAULTS.SAVINGS}
            onChange={handleSavingsInput}
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

      {/* Row 2: deposit / withdraw */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500 shrink-0">记一笔</span>
        <input
          type="number"
          min="0"
          placeholder="金额"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleDeposit()}
          className="w-24 px-3 py-1.5 border border-gray-300 rounded text-sm text-gray-900
                     placeholder-gray-400 focus:outline-none focus:border-yellow-500"
        />
        <button
          onClick={handleDeposit}
          className="px-3 py-1.5 bg-green-500 hover:bg-green-600 text-white text-xs
                     font-medium rounded transition-colors"
        >
          + 存入
        </button>
        <button
          onClick={handleWithdraw}
          className="px-3 py-1.5 bg-red-400 hover:bg-red-500 text-white text-xs
                     font-medium rounded transition-colors"
        >
          − 取出
        </button>
      </div>
    </div>
  );
}
