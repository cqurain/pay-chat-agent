'use client';

import type { TransactionRecord } from '@/lib/types';

interface TransactionSidebarProps {
  open: boolean;
  transactions: TransactionRecord[];
  onClose: () => void;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);

  const sameDay = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate();

  if (sameDay(d, today)) return '今天';
  if (sameDay(d, yesterday)) return '昨天';
  return `${d.getMonth() + 1}月${d.getDate()}日`;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

function groupByDate(txs: TransactionRecord[]): { label: string; items: TransactionRecord[] }[] {
  const map = new Map<string, TransactionRecord[]>();
  for (const tx of txs) {
    const key = tx.timestamp.slice(0, 10);
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(tx);
  }
  return Array.from(map.entries())
    .sort((a, b) => b[0].localeCompare(a[0]))
    .map(([, items]) => ({
      label: formatDate(items[0].timestamp),
      items,
    }));
}

export default function TransactionSidebar({
  open,
  transactions,
  onClose,
}: TransactionSidebarProps) {
  const withdrawals7d = transactions.filter((tx) => {
    if (tx.type !== 'withdraw') return false;
    const days = (Date.now() - new Date(tx.timestamp).getTime()) / 86400000;
    return days <= 7;
  });
  const total7d = withdrawals7d.reduce((s, tx) => s + tx.amount, 0);
  const groups = groupByDate(transactions);

  return (
    <>
      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/20"
          onClick={onClose}
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={`fixed top-0 right-0 z-40 h-full w-72 bg-white border-l border-gray-200
                    shadow-xl flex flex-col transition-transform duration-300
                    ${open ? 'translate-x-0' : 'translate-x-full'}`}
      >
        {/* Header */}
        <div className="h-14 flex items-center justify-between px-4 border-b border-gray-200 shrink-0">
          <h2 className="font-semibold text-gray-900 text-sm">存取明细</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-lg leading-none"
          >
            ✕
          </button>
        </div>

        {/* 7-day summary */}
        {total7d > 0 && (
          <div className="px-4 py-3 bg-red-50 border-b border-red-100 shrink-0">
            <p className="text-xs text-red-600">
              近 7 天取出{' '}
              <span className="font-semibold">¥{total7d.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}</span>
              ，共 {withdrawals7d.length} 笔
            </p>
          </div>
        )}

        {/* Transaction list */}
        <div className="flex-1 overflow-y-auto">
          {groups.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-2 text-gray-400">
              <span className="text-3xl">📭</span>
              <p className="text-sm">还没有记录</p>
            </div>
          ) : (
            groups.map((group) => (
              <div key={group.label}>
                {/* Date label */}
                <div className="px-4 py-2 bg-gray-50 border-b border-gray-100">
                  <span className="text-xs font-medium text-gray-500">{group.label}</span>
                </div>
                {/* Items */}
                {group.items.map((tx) => (
                  <div
                    key={tx.id}
                    className="flex items-center justify-between px-4 py-3 border-b border-gray-100"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-base">
                        {tx.type === 'deposit' ? '💰' : '💸'}
                      </span>
                      <div>
                        <p className="text-xs font-medium text-gray-700">
                          {tx.type === 'deposit' ? '存入' : '取出'}
                        </p>
                        <p className="text-xs text-gray-400">{formatTime(tx.timestamp)}</p>
                      </div>
                    </div>
                    <span
                      className={`text-sm font-semibold ${
                        tx.type === 'deposit' ? 'text-green-600' : 'text-red-500'
                      }`}
                    >
                      {tx.type === 'deposit' ? '+' : '-'}¥
                      {tx.amount.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}
                    </span>
                  </div>
                ))}
              </div>
            ))
          )}
        </div>
      </aside>
    </>
  );
}
