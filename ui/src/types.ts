/**
 * PEACOCK ENGINE V3 — Shared Type Definitions
 * Single source of truth for tab keys, nav shapes, and global enums.
 */

export type Tab =
  | 'DASHBOARD'
  | 'NEURAL LINK'
  | 'MODEL REGISTRY'
  | 'KEY VAULT'
  | 'STRIKER'
  | 'LIVE WIRE'
  | 'PLAN REVIEW'
  | 'HISTORY'
  | 'CONFIG'
  | 'STRESS';

export interface NavItem {
  key: Tab;
  label: string;
  icon: string;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: 'Operations',
    items: [
      { key: 'DASHBOARD', label: 'Dashboard', icon: 'dashboard' },
      { key: 'NEURAL LINK', label: 'Neural Link', icon: 'chat' },
      { key: 'LIVE WIRE', label: 'Live Wire', icon: 'bolt' },
    ],
  },
  {
    label: 'Planning',
    items: [
      { key: 'PLAN REVIEW', label: 'Plan Review', icon: 'route' },
      { key: 'HISTORY', label: 'History', icon: 'history' },
      { key: 'STRESS', label: 'Stress Test', icon: 'fitness_center' },
    ],
  },
  {
    label: 'Assets',
    items: [
      { key: 'MODEL REGISTRY', label: 'Models', icon: 'model_training' },
      { key: 'KEY VAULT', label: 'Keys', icon: 'vpn_key' },
      { key: 'STRIKER', label: 'Striker', icon: 'target' },
    ],
  },
  {
    label: 'System',
    items: [{ key: 'CONFIG', label: 'Config', icon: 'tune' }],
  },
];
