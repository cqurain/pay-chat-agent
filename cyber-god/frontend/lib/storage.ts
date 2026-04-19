/**
 * localStorage keys, defaults, and transaction helpers.
 * Keys are stable — changing them loses user data.
 */
import type { TransactionRecord, Persona } from './types';

export const STORAGE_KEYS = {
  SAVINGS: 'gsd_savings',
  TARGET: 'gsd_target',
  HAS_ONBOARDED: 'gsd_onboarded',
  TRANSACTIONS: 'gsd_transactions',
  PERSONA: 'gsd_persona',
} as const;

export const DEFAULTS = {
  SAVINGS: 0,
  TARGET: 10000,
} as const;

const MAX_TRANSACTIONS = 90;

export function loadTransactions(): TransactionRecord[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.TRANSACTIONS);
    return raw ? (JSON.parse(raw) as TransactionRecord[]) : [];
  } catch {
    return [];
  }
}

export function saveTransaction(tx: Omit<TransactionRecord, 'id'>): TransactionRecord {
  const record: TransactionRecord = {
    ...tx,
    id: typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`,
  };
  const existing = loadTransactions();
  const updated = [record, ...existing].slice(0, MAX_TRANSACTIONS);
  localStorage.setItem(STORAGE_KEYS.TRANSACTIONS, JSON.stringify(updated));
  return record;
}

export function getPersona(): Persona {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.PERSONA);
    if (raw === 'gentle' || raw === 'snarky') return raw;
  } catch { /* ignore */ }
  return 'snarky';
}

export function setPersona(p: Persona): void {
  try {
    localStorage.setItem(STORAGE_KEYS.PERSONA, p);
  } catch { /* ignore */ }
}
