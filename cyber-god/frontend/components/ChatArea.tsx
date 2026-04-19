'use client';

import { useEffect, useRef } from 'react';
import type { Message } from 'ai/react';
import type { SavingsPayload } from '@/lib/types';
import PriceResearchCard from './PriceResearchCard';

interface ChatAreaProps {
  messages: Message[];
  isLoading: boolean;
  chatData: SavingsPayload[];
  target: number;
  onExampleClick: (text: string) => void;
}

function getVerdictBorder(content: string): string {
  const firstLine = content.split('\n')[0];
  if (firstLine.includes('【批准】')) return 'border-l-4 border-green-500';
  if (firstLine.includes('【拒绝】') || firstLine.includes('【驳回】')) return 'border-l-4 border-red-500';
  return '';
}

function ToolStatus({
  isLoading,
  contentLength,
  dataLength,
}: {
  isLoading: boolean;
  contentLength: number;
  dataLength: number;
}) {
  if (!isLoading || contentLength >= 10) return null;
  if (dataLength === 0) {
    return <div className="text-yellow-400 text-sm animate-pulse">⚡ 财神正在掐指一算…</div>;
  }
  return <div className="text-yellow-400 text-sm animate-pulse">📊 正在计算影响…</div>;
}

export default function ChatArea({
  messages,
  isLoading,
  chatData,
  target,
  onExampleClick,
}: ChatAreaProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4 px-6">
        <div className="text-5xl select-none">🧧</div>
        <p className="text-lg text-gray-700 text-center">财神在此，请问何处要花冤枉钱？</p>
        <button
          onClick={() => onExampleClick('我想花 800 买个盲盒')}
          className="text-gray-500 hover:text-gray-700 cursor-pointer text-sm border border-gray-300 hover:border-gray-400 rounded-full px-4 py-2 transition-colors"
        >
          试试：我想花 800 买个盲盒
        </button>
      </div>
    );
  }

  // Associate each assistant message with its chatData payload by index
  let assistantIdx = 0;

  return (
    <div className="flex-1 overflow-y-auto px-6 py-4 flex flex-col gap-4">
      {messages.map((msg) => {
        if (msg.role === 'user') {
          return (
            <div key={msg.id} className="flex flex-col items-end gap-1">
              <span className="text-xs text-gray-400">用户</span>
              <div className="bg-yellow-50 text-gray-900 px-4 py-3 rounded-lg max-w-2xl border border-yellow-200">
                {msg.content}
              </div>
            </div>
          );
        }

        if (msg.role === 'assistant') {
          const payload = chatData[assistantIdx] as SavingsPayload | undefined;
          const currentIdx = assistantIdx;
          assistantIdx++;

          const isThisLoading = isLoading && currentIdx === assistantIdx - 1;
          const verdictBorder = getVerdictBorder(msg.content);

          // Reconstruct savings-before from payload (delta = -price, so before = new + price)
          const savingsBefore = payload ? payload.new_savings - payload.delta : 0;

          return (
            <div key={msg.id} className="flex flex-col items-start gap-1">
              <span className="text-xs text-gray-400">财神</span>
              <div
                className={`bg-gray-50 text-gray-900 px-4 py-3 rounded-lg max-w-2xl border border-gray-200 w-full ${verdictBorder}`}
              >
                {/* Price research card — shown as soon as payload arrives */}
                {payload && (
                  <PriceResearchCard
                    payload={payload}
                    currentSavings={savingsBefore}
                    target={target}
                  />
                )}

                <ToolStatus
                  isLoading={isThisLoading}
                  contentLength={msg.content.length}
                  dataLength={chatData.length}
                />

                {msg.content && (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                )}
              </div>
            </div>
          );
        }

        return null;
      })}
      <div ref={bottomRef} />
    </div>
  );
}
