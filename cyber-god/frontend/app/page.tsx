'use client';

import { useChat } from 'ai/react';
import { useEffect, useState } from 'react';
import Header from '@/components/Header';
import SavingsPanel from '@/components/SavingsPanel';
import ProgressBar from '@/components/ProgressBar';
import ChatArea from '@/components/ChatArea';
import InputArea from '@/components/InputArea';
import OnboardingModal from '@/components/OnboardingModal';
import { DEFAULTS, STORAGE_KEYS } from '@/lib/storage';
import type { SavingsPayload } from '@/lib/types';

export default function ChatPage() {
  const [savings, setSavings] = useState<number>(DEFAULTS.SAVINGS);
  const [target, setTarget] = useState<number>(DEFAULTS.TARGET);
  const [delta, setDelta] = useState<number | undefined>(undefined);

  // null = not yet determined (SSR), false = needs onboarding, true = ready
  const [onboarded, setOnboarded] = useState<boolean | null>(null);

  // Restore persisted values and check onboarding status after hydration
  useEffect(() => {
    const storedSavings = localStorage.getItem(STORAGE_KEYS.SAVINGS);
    const storedTarget = localStorage.getItem(STORAGE_KEYS.TARGET);
    const hasOnboarded = localStorage.getItem(STORAGE_KEYS.HAS_ONBOARDED);

    if (storedSavings !== null) setSavings(parseFloat(storedSavings));
    if (storedTarget !== null) setTarget(parseFloat(storedTarget));
    setOnboarded(hasOnboarded === 'true');
  }, []);

  const handleOnboardingComplete = (s: number, t: number) => {
    setSavings(s);
    setTarget(t);
    localStorage.setItem(STORAGE_KEYS.SAVINGS, String(s));
    localStorage.setItem(STORAGE_KEYS.TARGET, String(t));
    localStorage.setItem(STORAGE_KEYS.HAS_ONBOARDED, 'true');
    setOnboarded(true);
  };

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
    body: { savings, target },
  });

  // Read delta from 2: channel for the flash animation only.
  // Do NOT update savings state — user manages their savings manually.
  useEffect(() => {
    if (chatData && chatData.length > 0) {
      const raw = chatData[chatData.length - 1] as unknown;
      if (
        raw &&
        typeof (raw as SavingsPayload).delta === 'number'
      ) {
        setDelta((raw as SavingsPayload).delta);
      }
    }
  }, [chatData]);

  const handleSubmit = () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    append({ role: 'user', content: trimmed });
    setInput('');
  };

  const handleExampleClick = (text: string) => {
    setInput(text);
  };

  // Don't render until hydration check is done (avoids flicker)
  if (onboarded === null) return null;

  return (
    <>
      {!onboarded && (
        <OnboardingModal onComplete={handleOnboardingComplete} />
      )}

      <div className="flex flex-col h-screen bg-gray-50 text-gray-900">
        <Header />
        <SavingsPanel
          savings={savings}
          target={target}
          onSavingsChange={setSavings}
          onTargetChange={setTarget}
        />
        <ProgressBar savings={savings} target={target} delta={delta} />
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
    </>
  );
}
