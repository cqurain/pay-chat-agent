'use client';

import { useEffect, useRef, useState } from 'react';
import { STORAGE_KEYS, DEFAULTS } from '@/lib/storage';

interface SavingsPanelProps {
  savings: number;
  target: number;
  onSavingsChange: (value: number) => void;
  onTargetChange: (value: number) => void;
  onAddTransaction: (type: 'deposit' | 'withdraw', amount: number) => void;
}

export default function SavingsPanel({
  savings,
  target,
  onSavingsChange,
  onTargetChange,
  onAddTransaction,
}: SavingsPanelProps) {
  const [isMounted, setIsMounted] = useState(false);
  const [savingsStr, setSavingsStr] = useState('');
  const [targetStr, setTargetStr] = useState('');
  const [amount, setAmount] = useState('');
  const [amountError, setAmountError] = useState('');
  const savingsEditing = useRef(false);

  useEffect(() => {
    setIsMounted(true);
    const storedSavings = Number(localStorage.getItem(STORAGE_KEYS.SAVINGS));
    const storedTarget = Number(localStorage.getItem(STORAGE_KEYS.TARGET));
    const s = !isNaN(storedSavings) && storedSavings >= 0 ? storedSavings : DEFAULTS.SAVINGS;
    const t = !isNaN(storedTarget) && storedTarget > 0 ? storedTarget : DEFAULTS.TARGET;
    setSavingsStr(String(s));
    setTargetStr(String(t));
    onSavingsChange(s);
    onTargetChange(t);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync display when savings changes via deposit/withdraw (not while user is typing)
  useEffect(() => {
    if (isMounted && !savingsEditing.current) {
      setSavingsStr(String(savings));
    }
  }, [savings, isMounted]);

  const persistSavings = (val: number) => {
    onSavingsChange(val);
    localStorage.setItem(STORAGE_KEYS.SAVINGS, String(val));
  };

  const handleSavingsBlur = () => {
    savingsEditing.current = false;
    const num = parseFloat(savingsStr);
    if (savingsStr === '' || isNaN(num)) {
      setSavingsStr(String(savings)); // revert to last valid
    } else if (num < 0) {
      setSavingsStr('0');
      persistSavings(0);
    } else {
      setSavingsStr(String(num));
      persistSavings(num);
    }
  };

  const handleTargetBlur = () => {
    const num = parseFloat(targetStr);
    if (targetStr === '' || isNaN(num) || num <= 0) {
      setTargetStr(String(target)); // revert to last valid
    } else {
      setTargetStr(String(num));
      onTargetChange(num);
      localStorage.setItem(STORAGE_KEYS.TARGET, String(num));
    }
  };

  const handleDeposit = () => {
    const delta = parseFloat(amount);
    if (isNaN(delta) || delta <= 0) {
      setAmountError('请输入大于 0 的金额');
      return;
    }
    setAmountError('');
    persistSavings(Math.max(0, savings + delta));
    onAddTransaction('deposit', delta);
    setAmount('');
  };

  const handleWithdraw = () => {
    const delta = parseFloat(amount);
    if (isNaN(delta) || delta <= 0) {
      setAmountError('请输入大于 0 的金额');
      return;
    }
    setAmountError('');
    persistSavings(Math.max(0, savings - delta));
    onAddTransaction('withdraw', delta);
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
            value={isMounted ? savingsStr : ''}
            onChange={(e) => { savingsEditing.current = true; setSavingsStr(e.target.value); }}
            onBlur={handleSavingsBlur}
            className={inputClass}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm text-gray-600">目标金额</span>
          <input
            type="number"
            min="1"
            value={isMounted ? targetStr : ''}
            onChange={(e) => setTargetStr(e.target.value)}
            onBlur={handleTargetBlur}
            className={inputClass}
          />
        </label>
      </div>

      {/* Row 2: deposit / withdraw */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 shrink-0">记一笔</span>
          <input
            type="number"
            min="0"
            placeholder="金额"
            value={amount}
            onChange={(e) => { setAmount(e.target.value); setAmountError(''); }}
            onKeyDown={(e) => e.key === 'Enter' && handleDeposit()}
            className={`w-24 px-3 py-1.5 border rounded text-sm text-gray-900
                       placeholder-gray-400 focus:outline-none focus:border-yellow-500
                       ${amountError ? 'border-red-400' : 'border-gray-300'}`}
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
        {amountError && (
          <span className="text-xs text-red-500 pl-10">{amountError}</span>
        )}
      </div>
    </div>
  );
}
