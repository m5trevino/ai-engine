import React from 'react';
import { PlansAPI, RecentExecution } from '../../lib/api';

const STATUS_BADGES: Record<string, string> = {
  completed: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  failed: 'bg-error/15 text-error border-error/30',
  partial: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
};

interface RecentExecutionsProps {
  onReRun?: (planId: string) => void;
  refreshTrigger?: number;
}

const RecentExecutions: React.FC<RecentExecutionsProps> = ({ onReRun, refreshTrigger }) => {
  const [executions, setExecutions] = React.useState<RecentExecution[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [reRunningId, setReRunningId] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await PlansAPI.getRecentExecutions(20);
      setExecutions(data);
    } catch {
      // silent fail — this is a convenience view
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh, refreshTrigger]);

  const handleReRun = async (planId: string) => {
    if (!onReRun) return;
    setReRunningId(planId);
    try {
      await onReRun(planId);
    } finally {
      setReRunningId(null);
    }
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts * 1000);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const proxyPct = (e: RecentExecution) => {
    const total = e.proxy_chunks + e.direct_chunks;
    if (total === 0) return 0;
    return Math.round((e.proxy_chunks / total) * 100);
  };

  return (
    <div className="flex flex-col gap-3 h-full">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-sm">history</span>
          <span className="font-headline font-bold text-xs tracking-tight uppercase text-primary">Recent Executions</span>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="text-[10px] font-mono text-outline hover:text-primary transition-colors disabled:opacity-50 flex items-center gap-1"
        >
          <span className={`material-symbols-outlined text-sm ${loading ? 'animate-spin' : ''}`}>refresh</span>
          Refresh
        </button>
      </div>

      <div className="flex-1 overflow-y-auto pr-1">
        {executions.length === 0 && !loading && (
          <div className="text-center text-xs text-outline py-8">No executions yet.</div>
        )}

        <div className="space-y-2">
          {executions.map((e) => {
            const pct = proxyPct(e);
            const isReRunning = reRunningId === e.plan_id;
            return (
              <div
                key={`${e.plan_id}-${e.executed_at}`}
                className="bg-surface-container p-3 border-l-4 border-secondary/40 flex flex-col gap-2"
              >
                <div className="flex justify-between items-start">
                  <div className="flex flex-col gap-0.5 min-w-0">
                    <div className="font-mono text-xs text-on-surface truncate">{e.plan_id}</div>
                    <div className="text-[10px] font-mono text-outline truncate">{e.file_path}</div>
                  </div>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded uppercase font-bold border shrink-0 ${STATUS_BADGES[e.status] || STATUS_BADGES.partial}`}>
                    {e.status}
                  </span>
                </div>

                <div className="grid grid-cols-4 gap-2 text-[10px] font-mono">
                  <div className="flex flex-col">
                    <span className="text-outline">TOKENS</span>
                    <span className="text-on-surface font-bold">{e.total_tokens.toLocaleString()}</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-outline">PROXY</span>
                    <span className={`font-bold ${pct > 50 ? 'text-amber-400' : 'text-emerald-400'}`}>{pct}%</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-outline">DURATION</span>
                    <span className="text-on-surface font-bold">{formatDuration(e.duration_ms)}</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-outline">COST</span>
                    <span className="text-on-surface font-bold">${e.total_cost.toFixed(4)}</span>
                  </div>
                </div>

                <div className="flex justify-between items-center pt-1 border-t border-outline-variant/10">
                  <span className="text-[9px] font-mono text-outline">{formatTime(e.executed_at)}</span>
                  <button
                    onClick={() => handleReRun(e.plan_id)}
                    disabled={isReRunning || !onReRun}
                    className="text-[10px] font-headline font-bold uppercase tracking-wider px-2 py-1 bg-surface-container-high hover:bg-primary/20 text-primary border border-primary/30 transition-colors disabled:opacity-50 flex items-center gap-1"
                  >
                    <span className={`material-symbols-outlined text-sm ${isReRunning ? 'animate-spin' : ''}`}>
                      {isReRunning ? 'progress_activity' : 'replay'}
                    </span>
                    {isReRunning ? 'Queuing' : 'Re-run'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default RecentExecutions;
