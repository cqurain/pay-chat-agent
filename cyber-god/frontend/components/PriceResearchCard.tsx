'use client';

import type { SavingsPayload, PriceSource } from '@/lib/types';

interface PriceResearchCardProps {
  payload: SavingsPayload;
  currentSavings: number;
  target: number;
}

function fmt(n: number) {
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

export default function PriceResearchCard({
  payload,
  currentSavings,
  target,
}: PriceResearchCardProps) {
  const { confidence, product_name, price_min, price_max, price_found, source,
          new_savings, progress_pct, delta, sources } = payload;

  const progressBefore = target > 0 ? Math.max(0, (currentSavings / target) * 100) : 0;
  const progressAfter  = Math.max(0, progress_pct);

  // Price unknown → ask-user state
  if (confidence === 'unknown') {
    return (
      <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm">
        <p className="font-medium text-amber-700">⚠️ 未能查到市场价格</p>
        <p className="text-amber-600 text-xs mt-0.5">财神正在向你确认金额…</p>
      </div>
    );
  }

  const hasPriceRange = price_min !== undefined && price_max !== undefined
                        && price_max > price_min;

  const sourceTag =
    confidence === 'user_stated'
      ? <span className="text-xs text-gray-400">你说的价格</span>
      : confidence === 'scraped'
      ? <span className="text-xs text-green-600">🔍 {source || '网络搜索'}</span>
      : <span className="text-xs text-amber-600">📊 {source || '市场参考价'}</span>;

  return (
    <div className="mb-3 rounded-lg border border-gray-200 bg-white shadow-sm text-sm overflow-hidden">
      {/* Top: product + price */}
      <div className="px-4 py-3 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="font-medium text-gray-800 truncate">
            🔍 {product_name || '该商品'}
          </p>
          {hasPriceRange ? (
            <p className="text-gray-600 mt-0.5">
              ¥{fmt(price_min!)}
              <span className="text-gray-400 mx-1">～</span>
              ¥{fmt(price_max!)}
            </p>
          ) : (
            <p className="text-gray-600 mt-0.5">¥{fmt(price_found ?? 0)}</p>
          )}
          <div className="mt-0.5">{sourceTag}</div>
          {confidence === 'scraped' && sources && sources.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {sources.map((s: PriceSource) => (
                <a
                  key={s.platform + s.price}
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full
                             text-xs font-medium bg-green-50 text-green-700
                             border border-green-200 hover:bg-green-100 transition-colors"
                >
                  {s.platform} ¥{fmt(s.price)}
                </a>
              ))}
            </div>
          )}
        </div>

        {/* Delta badge */}
        {delta !== 0 && (
          <div className={`shrink-0 px-2 py-1 rounded text-xs font-semibold
                          ${delta < 0 ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'}`}>
            {delta < 0 ? '-' : '+'}¥{fmt(Math.abs(delta))}
          </div>
        )}
      </div>

      {/* Divider */}
      <div className="border-t border-gray-100" />

      {/* Bottom: savings impact */}
      <div className="px-4 py-2.5 bg-gray-50">
        <div className="flex justify-between text-xs text-gray-500 mb-1.5">
          <span>
            存款&nbsp;
            <span className="text-gray-700 font-medium">¥{fmt(currentSavings)}</span>
            <span className="mx-1 text-gray-400">→</span>
            <span className={`font-medium ${new_savings < 0 ? 'text-red-500' : 'text-gray-700'}`}>
              ¥{fmt(new_savings)}
            </span>
          </span>
          <span>
            <span className="text-gray-500">{progressBefore.toFixed(1)}%</span>
            <span className="mx-1 text-gray-400">→</span>
            <span className={`font-medium ${progressAfter < progressBefore ? 'text-red-500' : 'text-green-600'}`}>
              {progressAfter.toFixed(1)}%
            </span>
          </span>
        </div>

        {/* Mini progress bar */}
        <div className="h-1.5 rounded-full bg-gray-200 overflow-hidden">
          <div
            className="h-full rounded-full bg-yellow-400 transition-all duration-500"
            style={{ width: `${Math.min(100, progressAfter)}%` }}
          />
        </div>
      </div>
    </div>
  );
}
