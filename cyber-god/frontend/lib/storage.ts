/**
 * localStorage keys and default values for savings context.
 * Keys are stable — changing them would lose user data.
 */
export const STORAGE_KEYS = {
  SAVINGS: 'gsd_savings',
  TARGET: 'gsd_target',
  HAS_ONBOARDED: 'gsd_onboarded',
} as const;

export const DEFAULTS = {
  SAVINGS: 0,
  TARGET: 10000,
} as const;
