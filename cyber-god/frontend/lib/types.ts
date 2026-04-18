/**
 * Shared TypeScript interfaces for Cyber God of Wealth frontend.
 * SavingsPayload MUST match the backend 2: channel payload shape exactly.
 *
 * Backend source: cyber-god/backend/agent/loop.py
 *   savings_payload = { "new_savings": float, "progress_pct": float, "delta": float }
 */

/** Payload arriving on useChat.data[] from the 2: channel (SAVINGS-03, PROGRESS-02) */
export interface SavingsPayload {
  new_savings: number;
  progress_pct: number;
  delta: number;
}

/** Single chat message (mirrors backend ChatRequest.messages list item) */
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

/** Backend ChatRequest body shape — must match Pydantic model in routes.py */
export interface ChatRequestBody {
  messages: ChatMessage[];
  savings: number;
  target: number;
}
