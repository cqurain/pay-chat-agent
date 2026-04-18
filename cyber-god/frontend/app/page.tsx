'use client';

/**
 * Root page — single-page chat UI for 赛博财神爷.
 *
 * State owned here:
 *   - savings, target: persisted to localStorage, passed to useChat body (SAVINGS-03)
 *   - progressPct: derived from savings/target, updated when 2: data arrives (PROGRESS-01)
 *   - delta: latest savings impact from 2: channel, passed to ProgressBar for flash (PROGRESS-03)
 *
 * Plan 02 establishes the full layout skeleton and savings/progress wiring.
 * Plan 03 adds ChatArea + InputArea into the <main> section.
 */

import { useChat } from 'ai/react';
import { useEffect, useState } from 'react';
import Header from '@/components/Header';
import SavingsPanel from '@/components/SavingsPanel';
import ProgressBar from '@/components/ProgressBar';
import { DEFAULTS } from '@/lib/storage';
import type { SavingsPayload } from '@/lib/types';

export default function ChatPage() {
  // --- Savings state (SAVINGS-01, SAVINGS-02) ---
  // Initial values are DEFAULTS to avoid SSR mismatch; SavingsPanel loads from localStorage in useEffect
  const [savings, setSavings] = useState<number>(DEFAULTS.SAVINGS);
  const [target, setTarget] = useState<number>(DEFAULTS.TARGET);

  // --- Progress derived from 2: channel payload ---
  const [delta, setDelta] = useState<number | undefined>(undefined);

  // --- useChat hook (CHAT-01, SAVINGS-03) ---
  // api points directly at backend — NO Next.js proxy route (would kill streaming on Vercel)
  // body includes savings/target so backend ChatRequest receives real user numbers
  const {
    messages,
    input,
    setInput,
    append,
    isLoading,
    stop,
    reload,
    error,
    data: chatData,
  } = useChat({
    api: `${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/api/chat`,
    body: {
      savings,
      target,
    },
  });

  // --- Bridge: 2: channel → savings state + progress bar (D-12, PROGRESS-02, PROGRESS-03) ---
  // chatData is the useChat.data array; populated when backend emits 2:[{...}]
  // Always read the last element — data can accumulate across messages
  useEffect(() => {
    if (chatData && chatData.length > 0) {
      const raw = chatData[chatData.length - 1] as unknown;
      // Validate shape before trusting (T-02-04 mitigation)
      if (
        raw &&
        typeof (raw as SavingsPayload).new_savings === 'number' &&
        !isNaN((raw as SavingsPayload).new_savings) &&
        typeof (raw as SavingsPayload).progress_pct === 'number' &&
        typeof (raw as SavingsPayload).delta === 'number'
      ) {
        const payload = raw as SavingsPayload;
        setSavings(payload.new_savings);
        setDelta(payload.delta);
        // Persist updated savings to localStorage (savings changed by purchase)
        localStorage.setItem('gsd_savings', String(payload.new_savings));
      }
    }
  }, [chatData]);

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-gray-100">
      {/* Fixed header (56px) */}
      <Header />

      {/* Savings panel (inputs + progress bar, ~100px) */}
      <SavingsPanel
        savings={savings}
        target={target}
        onSavingsChange={setSavings}
        onTargetChange={setTarget}
      />
      <ProgressBar savings={savings} target={target} delta={delta} />

      {/* Chat area (flex-grow, scrollable) — ChatArea + InputArea added in Plan 03 */}
      <main className="flex flex-col flex-1 min-h-0">
        {/* Plan 03 inserts: <ChatArea ... /> and <InputArea ... /> here */}
        <div className="flex-1 flex items-center justify-center text-gray-600 text-sm">
          Chat area (Plan 03)
        </div>
      </main>
    </div>
  );
}
