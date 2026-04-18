'use client';

/**
 * Scrollable chat message area.
 *
 * Renders:
 *   - Empty state when messages === [] (D-22, CHAT-06)
 *   - User messages right-aligned, assistant messages left-aligned (D-13)
 *   - Approve/reject left border on assistant messages (D-14, CHAT-05)
 *   - Tool-call status indicator with 3 phases (D-16, D-17, D-18, CHAT-04)
 *   - Streaming typewriter effect (native useChat behavior, CHAT-02)
 *
 * Verdict detection: scan first line of content for 【批准】, 【拒绝】, or 【驳回】.
 * Note: backend (loop.py) uses 【驳回】 for reject — confirmed in 01-03-SUMMARY.md curl output.
 */

import { useEffect, useRef } from 'react';
import type { Message } from 'ai/react';

interface ChatAreaProps {
  messages: Message[];
  isLoading: boolean;
  dataLength: number;           // useChat.data.length — used for tool-status phase detection
  onExampleClick: (text: string) => void;  // fills input when example chip is clicked (D-22)
}

/** Detect verdict type from first line of assistant message content */
function getVerdictBorder(content: string): string {
  const firstLine = content.split('\n')[0];
  if (firstLine.includes('【批准】')) {
    return 'border-l-4 border-green-500';
  }
  if (firstLine.includes('【拒绝】') || firstLine.includes('【驳回】')) {
    return 'border-l-4 border-red-500';
  }
  return '';
}

/** Tool-call status indicator rendered inside an assistant message bubble */
function ToolStatus({
  isLoading,
  contentLength,
  dataLength,
}: {
  isLoading: boolean;
  contentLength: number;
  dataLength: number;
}) {
  // Hidden once content has started rendering (>= 10 chars) or not loading
  if (!isLoading || contentLength >= 10) return null;

  if (dataLength === 0) {
    // Phase 1: tool resolution in progress (no 2: data yet)
    return (
      <div className="text-yellow-400 text-sm animate-pulse">
        ⚡ 财神正在掐指一算…
      </div>
    );
  }

  // Phase 2: 2: data arrived, GLM generating text (content < 10 chars)
  return (
    <div className="text-yellow-400 text-sm animate-pulse">
      📊 正在计算影响…
    </div>
  );
}

export default function ChatArea({
  messages,
  isLoading,
  dataLength,
  onExampleClick,
}: ChatAreaProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new message or content update
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // --- Empty state (D-22, CHAT-06) ---
  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4 px-6">
        <div className="text-5xl select-none">🧧</div>
        <p className="text-lg text-gray-700 text-center">
          财神在此，请问何处要花冤枉钱？
        </p>
        <button
          onClick={() => onExampleClick('我想花 800 买个盲盒')}
          className="text-gray-500 hover:text-gray-700 cursor-pointer text-sm border border-gray-300 hover:border-gray-400 rounded-full px-4 py-2 transition-colors"
        >
          试试：我想花 800 买个盲盒
        </button>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-6 py-4 flex flex-col gap-4">
      {messages.map((msg) => {
        const isUser = msg.role === 'user';
        const isAssistant = msg.role === 'assistant';

        if (isUser) {
          return (
            <div key={msg.id} className="flex flex-col items-end gap-1">
              <span className="text-xs text-gray-400">用户</span>
              <div className="bg-yellow-50 text-gray-900 px-4 py-3 rounded-lg max-w-2xl border border-yellow-200">
                {msg.content}
              </div>
            </div>
          );
        }

        if (isAssistant) {
          const verdictBorder = getVerdictBorder(msg.content);

          return (
            <div key={msg.id} className="flex flex-col items-start gap-1">
              <span className="text-xs text-gray-400">财神</span>
              <div
                className={`bg-gray-50 text-gray-900 px-4 py-3 rounded-lg max-w-2xl border border-gray-200 ${verdictBorder}`}
              >
                {/* Tool-status indicator: shown when content is empty/minimal and loading */}
                <ToolStatus
                  isLoading={isLoading}
                  contentLength={msg.content.length}
                  dataLength={dataLength}
                />
                {/* Streamed verdict text (typewriter effect is native useChat behavior) */}
                {msg.content && (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                )}
              </div>
            </div>
          );
        }

        return null;
      })}
      {/* Scroll anchor */}
      <div ref={bottomRef} />
    </div>
  );
}
