'use client';

import { useChat } from 'ai/react';
import { useEffect, useState } from 'react';
import Header from '@/components/Header';
import SavingsPanel from '@/components/SavingsPanel';
import ProgressBar from '@/components/ProgressBar';
import ChatArea from '@/components/ChatArea';
import InputArea from '@/components/InputArea';
import OnboardingModal from '@/components/OnboardingModal';
import TransactionSidebar from '@/components/TransactionSidebar';
import { DEFAULTS, STORAGE_KEYS, loadTransactions, saveTransaction, getPersona, setPersona } from '@/lib/storage';
import type { SavingsPayload, TransactionRecord, Persona } from '@/lib/types';

export default function ChatPage() {
  const [savings, setSavings] = useState<number>(DEFAULTS.SAVINGS);
  const [target, setTarget] = useState<number>(DEFAULTS.TARGET);
  const [delta, setDelta] = useState<number | undefined>(undefined);
  const [transactions, setTransactions] = useState<TransactionRecord[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [persona, setPersonaState] = useState<Persona>('snarky');

  // null = hydrating, false = needs onboarding, true = ready
  const [onboarded, setOnboarded] = useState<boolean | null>(null);

  useEffect(() => {
    const storedSavings = localStorage.getItem(STORAGE_KEYS.SAVINGS);
    const storedTarget = localStorage.getItem(STORAGE_KEYS.TARGET);
    const hasOnboarded = localStorage.getItem(STORAGE_KEYS.HAS_ONBOARDED);

    if (storedSavings !== null) setSavings(parseFloat(storedSavings));
    if (storedTarget !== null) setTarget(parseFloat(storedTarget));
    setTransactions(loadTransactions());
    setPersonaState(getPersona());
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

  const handleAddTransaction = (type: 'deposit' | 'withdraw', amount: number) => {
    const record = saveTransaction({ type, amount, timestamp: new Date().toISOString() });
    setTransactions((prev) => [record, ...prev].slice(0, 90));
  };

  const handlePersonaChange = (p: Persona) => {
    setPersonaState(p);
    setPersona(p);
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
    body: { savings, target, transactions: transactions.slice(0, 30), persona },
  });

  const typedChatData = (chatData ?? []) as unknown as SavingsPayload[];

  // Keep delta in sync for ProgressBar flash animation
  useEffect(() => {
    if (typedChatData.length > 0) {
      const last = typedChatData[typedChatData.length - 1];
      if (typeof last?.delta === 'number') setDelta(last.delta);
    }
  }, [chatData]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmit = () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    append({ role: 'user', content: trimmed });
    setInput('');
  };

  if (onboarded === null) return null;

  return (
    <>
      {!onboarded && <OnboardingModal onComplete={handleOnboardingComplete} />}

      <TransactionSidebar
        open={sidebarOpen}
        transactions={transactions}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="flex flex-col h-screen bg-gray-50 text-gray-900">
        <Header
          onToggleSidebar={() => setSidebarOpen((o) => !o)}
          persona={persona}
          onPersonaChange={handlePersonaChange}
        />
        <SavingsPanel
          savings={savings}
          target={target}
          onSavingsChange={setSavings}
          onTargetChange={setTarget}
          onAddTransaction={handleAddTransaction}
        />
        <ProgressBar savings={savings} target={target} delta={delta} />
        <main className="flex flex-col flex-1 min-h-0">
          <ChatArea
            messages={messages}
            isLoading={isLoading}
            chatData={typedChatData}
            target={target}
            onExampleClick={setInput}
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
