import React from 'react';
import type { Tab, NavItem, NavGroup } from '../types';
import { NAV_GROUPS } from '../types';

const RECENT_KEY = 'peacock_recent_tabs';
const MAX_RECENT = 4;
const GROUP_COLLAPSE_KEY = 'peacock_sidebar_collapsed_groups';

function readRecent(): Tab[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed.slice(0, MAX_RECENT);
  } catch {}
  return [];
}

function writeRecent(tabs: Tab[]) {
  try {
    localStorage.setItem(RECENT_KEY, JSON.stringify(tabs.slice(0, MAX_RECENT)));
  } catch {}
}

function readCollapsedGroups(): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(GROUP_COLLAPSE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  // Default: collapse Assets and System (less-used groups)
  return { Assets: true, System: true };
}

function writeCollapsedGroups(groups: Record<string, boolean>) {
  try {
    localStorage.setItem(GROUP_COLLAPSE_KEY, JSON.stringify(groups));
  } catch {}
}

export const Sidebar: React.FC<{ active: Tab; onChange: (t: Tab) => void }> = ({ active, onChange }) => {
  const [expanded, setExpanded] = React.useState(() => {
    try { return localStorage.getItem('peacock_sidebar_expanded') !== 'false'; } catch { return true; }
  });
  const [recent, setRecent] = React.useState<Tab[]>(readRecent);
  const [collapsedGroups, setCollapsedGroups] = React.useState<Record<string, boolean>>(readCollapsedGroups);

  const allItems = React.useMemo(() => NAV_GROUPS.flatMap((g) => g.items), []);

  const handleChange = (tab: Tab) => {
    onChange(tab);
    setRecent((prev) => {
      const next = [tab, ...prev.filter((t) => t !== tab)];
      writeRecent(next);
      return next;
    });
  };

  const toggleExpanded = () => {
    setExpanded((v) => {
      try { localStorage.setItem('peacock_sidebar_expanded', String(!v)); } catch {}
      return !v;
    });
  };

  const toggleGroup = (label: string) => {
    setCollapsedGroups((prev) => {
      const next = { ...prev, [label]: !prev[label] };
      writeCollapsedGroups(next);
      return next;
    });
  };

  const recentItems = recent
    .map((key) => allItems.find((i) => i.key === key))
    .filter(Boolean) as NavItem[];

  const isActive = (key: Tab) => key === active;

  return (
    <aside
      className={`bg-surface-container-low border-r border-outline-variant/20 flex flex-col transition-all duration-300 ease-out ${
        expanded ? 'w-56' : 'w-16'
      }`}
    >
      {/* Header */}
      <div className="h-16 flex items-center justify-between px-3 border-b border-outline-variant/20 shrink-0">
        {expanded && (
          <span className="font-['Space_Grotesk'] font-bold text-[#aac7ff] text-sm tracking-widest truncate">
            PEACOCK
          </span>
        )}
        <button
          onClick={toggleExpanded}
          className="p-1.5 text-outline hover:text-on-surface hover:bg-surface-container-high rounded transition-colors"
          title={expanded ? 'Collapse' : 'Expand'}
        >
          <span className="material-symbols-outlined text-lg">{expanded ? 'menu_open' : 'menu'}</span>
        </button>
      </div>

      {/* Recent */}
      {recentItems.length > 0 && (
        <div className="py-2 border-b border-outline-variant/10">
          {expanded && (
            <div className="px-3 pb-1 text-[9px] font-headline font-bold text-outline uppercase tracking-widest">
              Recent
            </div>
          )}
          {recentItems.map((item) => (
            <button
              key={`recent-${item.key}`}
              onClick={() => handleChange(item.key)}
              className={`w-full flex items-center gap-3 px-3 py-2 text-xs transition-colors ${
                isActive(item.key)
                  ? 'bg-primary-container text-on-primary-container'
                  : 'text-on-surface hover:bg-surface-container-high'
              }`}
              title={item.label}
            >
              <span className="material-symbols-outlined text-lg shrink-0">{item.icon}</span>
              {expanded && <span className="truncate font-medium">{item.label}</span>}
            </button>
          ))}
        </div>
      )}

      {/* Groups */}
      <div className="flex-1 overflow-y-auto py-2 space-y-1">
        {NAV_GROUPS.map((group) => {
          const collapsed = collapsedGroups[group.label] ?? false;
          const hasActiveInGroup = group.items.some((i) => isActive(i.key));
          return (
            <div key={group.label}>
              <button
                onClick={() => toggleGroup(group.label)}
                className={`w-full flex items-center justify-between px-3 py-1.5 text-[9px] font-headline font-bold uppercase tracking-widest transition-colors ${
                  hasActiveInGroup ? 'text-primary' : 'text-outline'
                } hover:bg-surface-container-high`}
                title={group.label}
              >
                {expanded && <span>{group.label}</span>}
                {expanded && (
                  <span className="material-symbols-outlined text-sm transition-transform duration-200">
                    {collapsed ? 'chevron_right' : 'expand_more'}
                  </span>
                )}
                {!expanded && hasActiveInGroup && (
                  <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                )}
              </button>
              {(!collapsed || !expanded) && (
                <div className={collapsed ? 'hidden' : ''}>
                  {group.items.map((item) => (
                    <button
                      key={item.key}
                      onClick={() => handleChange(item.key)}
                      className={`w-full flex items-center gap-3 px-3 py-2 text-xs transition-colors ${
                        isActive(item.key)
                          ? 'bg-primary-container text-on-primary-container'
                          : 'text-on-surface hover:bg-surface-container-high'
                      }`}
                      title={item.label}
                    >
                      <span className="material-symbols-outlined text-lg shrink-0">{item.icon}</span>
                      {expanded && <span className="truncate font-medium">{item.label}</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="px-3 py-2 border-t border-outline-variant/20 shrink-0">
        <div className={`flex items-center gap-2 text-[10px] font-['JetBrains_Mono'] text-outline ${expanded ? '' : 'justify-center'}`}>
          <span className="material-symbols-outlined text-sm text-tertiary">sensors</span>
          {expanded && <span>v3.0.0</span>}
        </div>
      </div>
    </aside>
  );
};
