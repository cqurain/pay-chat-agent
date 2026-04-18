'use client';

import { useState } from 'react';
import { DEFAULTS } from '@/lib/storage';

interface OnboardingModalProps {
  onComplete: (savings: number, target: number) => void;
}

export default function OnboardingModal({ onComplete }: OnboardingModalProps) {
  const [savings, setSavings] = useState('');
  const [target, setTarget] = useState('');

  const handleSubmit = () => {
    const s = parseFloat(savings) || DEFAULTS.SAVINGS;
    const t = parseFloat(target) || DEFAULTS.TARGET;
    onComplete(s, t > 0 ? t : DEFAULTS.TARGET);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-sm mx-4">
        {/* Icon + title */}
        <div className="text-center mb-6">
          <div className="text-4xl mb-3">🧧</div>
          <h1 className="text-xl font-bold text-gray-900">欢迎，财神来了</h1>
          <p className="text-sm text-gray-500 mt-1">先告诉我你的存款目标，我好盯着你</p>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              存款目标 <span className="text-gray-400 font-normal">（元）</span>
            </label>
            <input
              type="number"
              min="1"
              placeholder="例如：10000"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 text-sm
                         focus:outline-none focus:border-yellow-500 placeholder-gray-400"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              目前已存 <span className="text-gray-400 font-normal">（元，没有填 0）</span>
            </label>
            <input
              type="number"
              min="0"
              placeholder="例如：3000"
              value={savings}
              onChange={(e) => setSavings(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 text-sm
                         focus:outline-none focus:border-yellow-500 placeholder-gray-400"
            />
          </div>
        </div>

        <button
          onClick={handleSubmit}
          className="mt-6 w-full py-3 bg-yellow-500 hover:bg-yellow-400 text-gray-900
                     font-semibold rounded-lg transition-colors text-sm"
        >
          开始理财
        </button>

        <p className="text-xs text-gray-400 text-center mt-3">
          数据仅存本地，不会上传
        </p>
      </div>
    </div>
  );
}
