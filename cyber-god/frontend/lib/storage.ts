/**
 * localStorage keys and default values for savings context (D-08, SAVINGS-01, SAVINGS-02).
 * Keys are stable — changing them would lose user data.
 */
export const STORAGE_KEYS = {
  SAVINGS: 'gsd_savings',
  TARGET: 'gsd_target',
} as const;

export const DEFAULTS = {
  SAVINGS: 0,
  TARGET: 10000,
} as const;
