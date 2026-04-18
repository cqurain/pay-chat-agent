'use client';

/**
 * Input row: text input + send/stop buttons.
 *
 * Behavior:
 *   - isLoading=true: input disabled, send hidden, stop (■ 停止) visible (D-20, CHAT-03)
 *   - isLoading=false: input enabled, stop hidden, send visible
 *   - Submit on Enter key (not Shift+Enter) (D-21)
 *   - Error banner above input if error is set (D-23, CHAT-07)
 *
 * Security (T-02-10): Error banner shows hardcoded Chinese message — NOT error.message.
 * This prevents internal stack traces or sensitive details leaking to the UI.
 */

import type { FormEvent, KeyboardEvent } from 'react';

interface InputAreaProps {
  input: string;
  isLoading: boolean;
  error?: Error;
  onInputChange: (value: string) => void;
  onSubmit: () => void;
  onStop: () => void;
  onRetry: () => void;
}

export default function InputArea({
  input,
  isLoading,
  error,
  onInputChange,
  onSubmit,
  onStop,
  onRetry,
}: InputAreaProps) {
  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !isLoading) {
      e.preventDefault();
      if (input.trim()) {
        onSubmit();
      }
    }
  };

  const handleFormSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSubmit();
    }
  };

  return (
    <div className="shrink-0 border-t border-gray-800 bg-gray-900">
      {/* Error banner (D-23, CHAT-07) — hardcoded message only, never error.message (T-02-10) */}
      {error && (
        <div className="flex items-center gap-3 px-6 py-3 bg-red-900 border-b border-red-800">
          <span className="text-red-200 text-sm flex-1">
            ⚠ 财神系统故障，请稍后再试。
          </span>
          <button
            onClick={onRetry}
            className="text-red-200 hover:text-white text-sm underline shrink-0"
          >
            重试
          </button>
        </div>
      )}

      {/* Input row */}
      <form onSubmit={handleFormSubmit} className="flex gap-3 px-6 py-4">
        <input
          type="text"
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          placeholder="试试：我想花 800 买个盲盒"
          className="
            flex-1 px-4 py-3 bg-gray-800 border border-gray-600 text-gray-100 rounded-lg
            placeholder-gray-500 focus:outline-none focus:border-yellow-500
            disabled:opacity-50 disabled:cursor-not-allowed
            text-sm
          "
        />

        {/* Stop button — shown during streaming */}
        {isLoading && (
          <button
            type="button"
            onClick={onStop}
            className="px-4 py-3 bg-red-500 hover:bg-red-600 text-white font-semibold rounded-lg transition-colors shrink-0 text-sm"
          >
            ■ 停止
          </button>
        )}

        {/* Send button — shown when not streaming */}
        {!isLoading && (
          <button
            type="submit"
            disabled={!input.trim()}
            className="
              px-4 py-3 bg-yellow-500 hover:bg-yellow-400 text-gray-900 font-semibold rounded-lg
              transition-colors shrink-0 text-sm
              disabled:opacity-40 disabled:cursor-not-allowed
            "
          >
            发送
          </button>
        )}
      </form>
    </div>
  );
}
