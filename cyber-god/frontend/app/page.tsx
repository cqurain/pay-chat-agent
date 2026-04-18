'use client';

/**
 * Root page — single-page chat UI for 赛博财神爷.
 * Plan 02 established savings/progress wiring.
 * Plan 03 adds ChatArea + InputArea to complete the chat experience.
 */

import { useChat } from 'ai/react';
import { useEffect, useState } from 'react';
import Header from '@/components/Header';
import SavingsPanel from '@/components/SavingsPanel';
import ProgressBar from '@/components/ProgressBar';
import ChatArea from '@/components/ChatArea';
import InputArea from '@/components/InputArea';
import { DEFAULTS } from '@/lib/storage';
import type { SavingsPayload } from '@/lib/types';

export default function ChatPage() {
  // --- Savings state (SAVINGS-01, SAVINGS-02) ---
  const [savings, setSavings] = useState<number>(DEFAULTS.SAVINGS);
  const [target, setTarget] = useState<number>(DEFAULTS.TARGET);

  // --- Progress derived from 2: channel payload ---
  const [delta, setDelta] = useState<number | undefined>(undefined);

  // --- useChat hook (CHAT-01, SAVINGS-03) ---
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
  useEffect(() => {
    if (chatData && chatData.length > 0) {
      const raw = chatData[chatData.length - 1] as unknown;
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
        localStorage.setItem('gsd_savings', String(payload.new_savings));
      }
    }
  }, [chatData]);

  // --- Submit handler: send user message via useChat.append ---
  const handleSubmit = () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    append({ role: 'user', content: trimmed });
    setInput('');
  };

  // --- Example chip click: fill input with example text (D-22) ---
  const handleExampleClick = (text: string) => {
    setInput(text);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50 text-gray-900">
      {/* Fixed header (56px) */}
      <Header />

      {/* Savings panel (inputs, ~80px) */}
      <SavingsPanel
        savings={savings}
        target={target}
        onSavingsChange={setSavings}
        onTargetChange={setTarget}
      />

      {/* Progress bar (32px + padding) */}
      <ProgressBar savings={savings} target={target} delta={delta} />

      {/* Chat area (flex-grow, scrollable) + Input row (fixed at bottom) */}
      <main className="flex flex-col flex-1 min-h-0">
        <ChatArea
          messages={messages}
          isLoading={isLoading}
          dataLength={chatData?.length ?? 0}
          onExampleClick={handleExampleClick}
        />
        <InputArea
          input={input}
          isLoading={isLoading}
          error={error}
          onInputChange={setInput}
          onSubmit={handleSubmit}
          onStop={stop}
          onRetry={reload}
        />
      </main>
    </div>
  );
}
