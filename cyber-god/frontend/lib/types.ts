/**
 * Shared TypeScript interfaces for Cyber God of Wealth frontend.
 * SavingsPayload MUST match the backend 2: channel payload shape exactly.
 */

/** Single transaction record stored in localStorage and sent to backend */
export interface TransactionRecord {
  id: string;
  type: 'deposit' | 'withdraw';
  amount: number;
  timestamp: string; // ISO 8601
}

/** Payload arriving on useChat.data[] from the 2: channel */
export interface SavingsPayload {
  new_savings: number;
  progress_pct: number;
  delta: number;
  // Price research fields (present when backend resolved a price)
  product_name?: string;
  price_found?: number;
  price_min?: number;
  price_max?: number;
  source?: string;
  confidence?: 'user_stated' | 'scraped' | 'reference' | 'unknown' | 'no_intent';
  sources?: PriceSource[];
  items?: Array<{ name: string; price: number; confidence: string }>;
  verdict?: '批准' | '驳回' | null;
}

/** Single chat message */
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

/** Backend ChatRequest body shape — must match Pydantic model in routes.py */
export interface ChatRequestBody {
  messages: ChatMessage[];
  savings: number;
  target: number;
  transactions: TransactionRecord[];
  persona: Persona;
}

/** Persona identifier */
export type Persona = 'snarky' | 'gentle';

/** A single price source returned by the backend for scraped results */
export interface PriceSource {
  platform: string;
  price: number;
  url: string;
}
