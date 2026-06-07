import React from 'react';
import { HistoryAPI, HistoryRunItem, HistoryChunkItem, HistoryStats, HistoryCompareItem } from '../lib/api';

const STATUS_BADGES: Record<string, string> = {
  completed: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  failed: 'bg-error/15 text-error border-error/30',
  partial: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
};

const CHUNK_STATUS_DOT: Record<string, string> = {
  completed: 'bg-emerald-400',
  failed: 'bg-error',
  skipped: 'bg-outline',
  running: 'bg-primary animate-pulse',
};

function downloadJson(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function downloadCsv(rows: Record<string, string | number>[], filename: string) {
  if (rows.length === 0) return;
  const headers = Object.keys(rows[0]);
  const csv = [
    headers.join(','),
    ...rows.map((r) => headers.map((h) => `"${String(r[h]).replace(/"/g, '""')}"`).join(',')),
  ].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

const History: React.FC = () => {
  const [runs, setRuns] = React.useState<HistoryRunItem[]>([]);
  const [stats, setStats] = React.useState<HistoryStats | null>(null);
  const [selectedRun, setSelectedRun] = React.useState<(HistoryRunItem & { chunks: HistoryChunkItem[] }) | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [detailLoading, setDetailLoading] = React.useState(false);
  const [filterStatus, setFilterStatus] = React.useState<string>('');
  const [filterPlanId, setFilterPlanId] = React.useState<string>('');
  const [runOffset, setRunOffset] = React.useState(0);
  const [runTotal, setRunTotal] = React.useState(0);
  const [hasMoreRuns, setHasMoreRuns] = React.useState(true);
  const [loadingMoreRuns, setLoadingMoreRuns] = React.useState(false);
  const RUN_PAGE_SIZE = 50;
  const [toast, setToast] = React.useState<string | null>(null);

  // Compare state
  const [selectedRuns, setSelectedRuns] = React.useState<Set<string>>(new Set());
  const [compareData, setCompareData] = React.useState<HistoryCompareItem[] | null>(null);
  const [compareLoading, setCompareLoading] = React.useState(false);

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(null), 3000); };

  const refresh = React.useCallback(async (targetOffset?: number) => {
    const offset = targetOffset ?? runOffset;
    setLoading(true);
    try {
      const [runsData, statsData, count] = await Promise.all([
        HistoryAPI.listRuns(RUN_PAGE_SIZE, offset, filterPlanId || undefined, filterStatus || undefined),
        HistoryAPI.getStats(7),
        HistoryAPI.countRuns(filterPlanId || undefined, filterStatus || undefined),
      ]);
      setRuns(runsData);
      setRunTotal(count.total);
      setHasMoreRuns(offset + runsData.length < count.total);
      setRunOffset(offset);
      setStats(statsData);
    } catch (e: any) {
      showToast(e.message);
    } finally {
      setLoading(false);
    }
  }, [filterStatus, filterPlanId, runOffset]);

  React.useEffect(() => {
    refresh(0);
  }, []);

  const openDetail = async (run_id: string) => {
    setDetailLoading(true);
    try {
      const run = await HistoryAPI.getRun(run_id);
      setSelectedRun(run);
    } catch (e: any) {
      showToast(e.message);
    } finally {
      setDetailLoading(false);
    }
  };

  const toggleSelectRun = (runId: string) => {
    setSelectedRuns((prev) => {
      const next = new Set(prev);
      if (next.has(runId)) next.delete(runId);
      else next.add(runId);
      return next;
    });
  };

  const doCompare = async () => {
    const ids = Array.from(selectedRuns);
    if (ids.length < 2) { showToast('Select at least 2 runs'); return; }
    setCompareLoading(true);
    try {
      const res = await HistoryAPI.compare(ids);
      setCompareData(res.runs);
    } catch (e: any) {
      showToast(e.message);
    } finally {
      setCompareLoading(false);
    }
  };

  const exportSingleJson = () => {
    if (!selectedRun) return;
    downloadJson(selectedRun, `${selectedRun.run_id}.json`);
  };

  const exportSingleCsv = () => {
    if (!selectedRun) return;
    const rows = [{
      run_id: selectedRun.run_id,
      plan_id: selectedRun.plan_id,
      status: selectedRun.status,
      total_tokens: selectedRun.total_tokens,
      total_cost: selectedRun.total_cost,
      duration_ms: selectedRun.duration_ms,
      proxy_chunks: selectedRun.proxy_chunks,
      direct_chunks: selectedRun.direct_chunks,
      failed_chunks: selectedRun.failed_chunks,
      model_id: selectedRun.model_id,
    }];
    downloadCsv(rows, `${selectedRun.run_id}.csv`);
  };

  const exportCompareJson = () => {
    if (!compareData) return;
    downloadJson(compareData, 'history_comparison.json');
  };

  const exportCompareCsv = () => {
    if (!compareData) return;
    const rows = compareData.map((r) => ({
      run_id: r.run_id,
      plan_id: r.plan_id,
      status: r.status,
      total_tokens: r.total_tokens,
      total_cost: r.total_cost,
      duration_ms: r.duration_ms,
      proxy_pct: r.proxy_pct,
      failed_chunks: r.failed_chunks,
      model_id: r.model_id,
    }));
    downloadCsv(rows, 'history_comparison.csv');
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts * 1000);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const proxyPct = (run: HistoryRunItem) => {
    const total = run.proxy_chunks + run.direct_chunks;
    if (total === 0) return 0;
    return Math.round((run.proxy_chunks / total) * 100);
  };

  return (
    <main className="pt-4 pb-8 h-[calc(100vh-32px)] flex flex-col p-4 gap-4 overflow-hidden">
      {/* Header */}
      <section className="bg-surface-container-low p-4 flex flex-col md:flex-row gap-3 items-stretch md:items-center">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-primary">history</span>
          <span className="font-headline font-bold text-sm tracking-tight uppercase">EXECUTION HISTORY</span>
        </div>
        <div className="flex-1 flex gap-2">
          <input
            value={filterPlanId}
            onChange={(e) => setFilterPlanId(e.target.value)}
            placeholder="Filter by plan ID"
            className="flex-1 bg-surface-container px-3 py-2 text-xs font-mono text-on-surface outline-none border border-outline-variant/20 focus:border-primary"
          />
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="w-40 bg-surface-container px-3 py-2 text-xs font-mono text-on-surface outline-none border border-outline-variant/20 focus:border-primary"
          >
            <option value="">All statuses</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="partial">Partial</option>
          </select>
          <button
            onClick={() => refresh(0)}
            disabled={loading}
            className="bg-primary-container text-on-primary-container px-4 py-2 font-headline font-bold text-xs tracking-widest uppercase hover:bg-primary transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            <span className={`material-symbols-outlined text-sm ${loading ? 'animate-spin' : ''}`}>refresh</span>
            Refresh
          </button>
          {selectedRuns.size >= 2 && (
            <button
              onClick={doCompare}
              disabled={compareLoading}
              className="bg-secondary-container text-on-secondary-container px-4 py-2 font-headline font-bold text-xs tracking-widest uppercase hover:bg-secondary transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              <span className="material-symbols-outlined text-sm">{compareLoading ? 'progress_activity' : 'compare_arrows'}</span>
              Compare ({selectedRuns.size})
            </button>
          )}
        </div>
      </section>

      {/* Stats row */}
      {stats && (
        <section className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-1">
          {[
            { label: 'TOTAL RUNS', value: stats.total_runs },
            { label: 'COMPLETED', value: stats.completed_runs, color: 'text-emerald-400' },
            { label: 'FAILED', value: stats.failed_runs, color: 'text-error' },
            { label: 'FAILURE RATE', value: `${stats.failure_rate}%`, color: stats.failure_rate > 10 ? 'text-error' : 'text-secondary' },
            { label: 'TOKENS', value: stats.total_tokens.toLocaleString() },
            { label: 'PROXY %', value: `${stats.proxy_pct}%`, color: stats.proxy_pct > 50 ? 'text-amber-400' : 'text-emerald-400' },
          ].map((s, i) => (
            <div key={i} className="bg-surface-container-high p-3 flex flex-col justify-between aspect-square">
              <span className="font-headline text-[10px] text-outline uppercase">{s.label}</span>
              <div className={`font-mono text-xl font-bold ${s.color || 'text-on-surface'}`}>{s.value}</div>
            </div>
          ))}
        </section>
      )}

      {/* Comparison Panel */}
      {compareData && (
        <section className="bg-surface-container p-4 border border-outline-variant/20">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-sm text-tertiary">compare_arrows</span>
              <span className="font-headline font-bold text-xs uppercase text-primary">Run Comparison</span>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={exportCompareJson} className="bg-surface-container-high text-on-surface px-2 py-1 font-headline font-bold text-[9px] tracking-widest uppercase hover:bg-surface-bright transition-colors flex items-center gap-1">
                <span className="material-symbols-outlined text-sm">download</span> JSON
              </button>
              <button onClick={exportCompareCsv} className="bg-surface-container-high text-on-surface px-2 py-1 font-headline font-bold text-[9px] tracking-widest uppercase hover:bg-surface-bright transition-colors flex items-center gap-1">
                <span className="material-symbols-outlined text-sm">download</span> CSV
              </button>
              <button onClick={() => { setCompareData(null); setSelectedRuns(new Set()); }} className="text-outline hover:text-error p-1">
                <span className="material-symbols-outlined text-sm">close</span>
              </button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-[10px]">
              <thead className="border-b border-outline-variant/20">
                <tr>
                  <th className="p-2 font-normal text-outline">METRIC</th>
                  {compareData.map((r) => (
                    <th key={r.run_id} className="p-2 font-normal text-outline">{r.run_id}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/5">
                {[
                  { label: 'Status', get: (r: HistoryCompareItem) => r.status },
                  { label: 'Plan', get: (r: HistoryCompareItem) => r.plan_id },
                  { label: 'Model', get: (r: HistoryCompareItem) => r.model_id },
                  { label: 'Tokens', get: (r: HistoryCompareItem) => r.total_tokens.toLocaleString() },
                  { label: 'Cost', get: (r: HistoryCompareItem) => `$${r.total_cost.toFixed(4)}` },
                  { label: 'Duration', get: (r: HistoryCompareItem) => formatDuration(r.duration_ms) },
                  { label: 'Proxy %', get: (r: HistoryCompareItem) => `${r.proxy_pct}%` },
                  { label: 'Failed', get: (r: HistoryCompareItem) => r.failed_chunks.toString() },
                  { label: 'Skipped', get: (r: HistoryCompareItem) => r.skipped_chunks.toString() },
                ].map((row) => (
                  <tr key={row.label}>
                    <td className="p-2 text-outline">{row.label}</td>
                    {compareData.map((r) => (
                      <td key={r.run_id} className="p-2 text-on-surface font-bold">{row.get(r)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Runs list */}
      <section className="flex-1 bg-surface-container-low flex flex-col overflow-hidden">
        <div className="p-3 border-b border-outline-variant/20 flex justify-between items-center">
          <span className="font-headline text-[10px] text-outline uppercase tracking-widest">Runs</span>
          <span className="text-[10px] font-mono text-outline">{runs.length} results</span>
        </div>
        <div className="flex-1 overflow-y-auto p-3">
          {runs.length === 0 && !loading && !loadingMoreRuns && (
            <div className="text-center text-outline text-sm py-12">No execution history yet.</div>
          )}
          <div className="space-y-2">
            {runs.map((run) => {
              const pct = proxyPct(run);
              return (
                <div
                  key={run.run_id}
                  className={`w-full text-left bg-surface-container p-3 border-l-4 transition-colors ${selectedRuns.has(run.run_id) ? 'border-tertiary bg-surface-container-high' : 'border-secondary/40 hover:bg-surface-container-high'}`}
                >
                  <div className="flex items-start gap-2">
                    <input
                      type="checkbox"
                      checked={selectedRuns.has(run.run_id)}
                      onChange={() => toggleSelectRun(run.run_id)}
                      className="mt-0.5 accent-primary shrink-0"
                    />
                    <button onClick={() => openDetail(run.run_id)} className="flex-1 text-left min-w-0">
                      <div className="flex justify-between items-start gap-3">
                        <div className="flex flex-col gap-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs text-on-surface truncate">{run.run_id}</span>
                            <span className={`text-[9px] px-1.5 py-0.5 rounded uppercase font-bold border ${STATUS_BADGES[run.status] || STATUS_BADGES.partial}`}>
                              {run.status}
                            </span>
                          </div>
                          <div className="text-[10px] font-mono text-outline truncate">{run.file_path} · {run.model_id}</div>
                        </div>
                        <span className="text-[10px] font-mono text-outline shrink-0">{formatTime(run.executed_at)}</span>
                      </div>
                      <div className="grid grid-cols-5 gap-2 mt-2 text-[10px] font-mono">
                        <div><span className="text-outline">TOKENS</span> <span className="text-on-surface font-bold">{run.total_tokens.toLocaleString()}</span></div>
                        <div><span className="text-outline">PROXY</span> <span className={`font-bold ${pct > 50 ? 'text-amber-400' : 'text-emerald-400'}`}>{pct}%</span></div>
                        <div><span className="text-outline">COST</span> <span className="text-on-surface font-bold">${run.total_cost.toFixed(4)}</span></div>
                        <div><span className="text-outline">TIME</span> <span className="text-on-surface font-bold">{formatDuration(run.duration_ms)}</span></div>
                        <div><span className="text-outline">CHUNKS</span> <span className="text-on-surface font-bold">{run.proxy_chunks + run.direct_chunks + run.failed_chunks + run.skipped_chunks}</span></div>
                      </div>
                      {run.error_summary && (
                        <div className="text-[10px] text-error mt-1 truncate">{run.error_summary}</div>
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
          {runTotal > 0 && (
            <div className="p-3 border-t border-outline-variant/20 flex items-center justify-between">
              <span className="text-[9px] font-mono text-outline">
                {runOffset + 1}-{Math.min(runOffset + runs.length, runTotal)} of {runTotal}
              </span>
              <div className="flex gap-1">
                <button
                  onClick={() => { setLoadingMoreRuns(true); refresh(Math.max(0, runOffset - RUN_PAGE_SIZE)).finally(() => setLoadingMoreRuns(false)); }}
                  disabled={loadingMoreRuns || runOffset === 0}
                  className="px-2 py-1 text-[9px] font-headline font-bold uppercase tracking-widest text-outline hover:text-on-surface hover:bg-surface-container transition-colors disabled:opacity-30"
                >
                  Prev
                </button>
                <button
                  onClick={() => { setLoadingMoreRuns(true); refresh(runOffset + RUN_PAGE_SIZE).finally(() => setLoadingMoreRuns(false)); }}
                  disabled={loadingMoreRuns || !hasMoreRuns}
                  className="px-2 py-1 text-[9px] font-headline font-bold uppercase tracking-widest text-outline hover:text-on-surface hover:bg-surface-container transition-colors disabled:opacity-30"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Detail Modal */}
      {selectedRun && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-surface-container-low w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden shadow-2xl">
            {/* Modal header */}
            <div className="p-4 border-b border-outline-variant/20 flex justify-between items-start">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-[10px] px-2 py-0.5 rounded uppercase font-bold border ${STATUS_BADGES[selectedRun.status] || STATUS_BADGES.partial}`}>
                    {selectedRun.status}
                  </span>
                  <span className="font-mono text-xs text-primary">{selectedRun.run_id}</span>
                </div>
                <div className="text-sm text-on-surface font-mono truncate">{selectedRun.file_path}</div>
                <div className="text-[10px] font-mono text-outline mt-1">
                  {selectedRun.model_id} · {formatTime(selectedRun.executed_at)}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={exportSingleJson} className="bg-surface-container-high text-on-surface px-2 py-1 font-headline font-bold text-[9px] tracking-widest uppercase hover:bg-surface-bright transition-colors flex items-center gap-1">
                  <span className="material-symbols-outlined text-sm">download</span> JSON
                </button>
                <button onClick={exportSingleCsv} className="bg-surface-container-high text-on-surface px-2 py-1 font-headline font-bold text-[9px] tracking-widest uppercase hover:bg-surface-bright transition-colors flex items-center gap-1">
                  <span className="material-symbols-outlined text-sm">download</span> CSV
                </button>
                <button
                  onClick={() => setSelectedRun(null)}
                  className="text-outline hover:text-error p-1"
                >
                  <span className="material-symbols-outlined text-lg">close</span>
                </button>
              </div>
            </div>

            {/* Modal stats */}
            <div className="px-4 py-2 bg-surface-container border-b border-outline-variant/20 flex items-center gap-4 text-[10px] font-mono">
              <span className="text-outline">TOKENS: <span className="text-on-surface font-bold">{selectedRun.total_tokens.toLocaleString()}</span></span>
              <span className="text-outline">COST: <span className="text-on-surface font-bold">${selectedRun.total_cost.toFixed(4)}</span></span>
              <span className="text-outline">DURATION: <span className="text-on-surface font-bold">{formatDuration(selectedRun.duration_ms)}</span></span>
              <span className="text-outline">PROXY: <span className="text-on-surface font-bold">{selectedRun.proxy_chunks}</span></span>
              <span className="text-outline">DIRECT: <span className="text-on-surface font-bold">{selectedRun.direct_chunks}</span></span>
              <span className="text-outline">FAILED: <span className="text-error font-bold">{selectedRun.failed_chunks}</span></span>
            </div>

            {/* Chunk breakdown */}
            <div className="flex-1 overflow-y-auto p-4">
              {detailLoading ? (
                <div className="flex items-center justify-center text-outline text-sm py-12">
                  <span className="material-symbols-outlined animate-spin mr-2">progress_activity</span>
                  Loading...
                </div>
              ) : (
                <div className="space-y-2">
                  {selectedRun.chunks.map((chunk) => (
                    <div
                      key={chunk.chunk_id}
                      className="bg-surface-container p-3 border-l-4 flex items-center gap-3"
                      style={{
                        borderLeftColor:
                          chunk.status === 'completed' && chunk.route === 'proxy'
                            ? '#f59e0b'
                            : chunk.status === 'completed' && chunk.route === 'direct'
                            ? '#10b981'
                            : chunk.status === 'failed'
                            ? '#ef4444'
                            : '#6b7280',
                      }}
                    >
                      <div className={`w-2 h-2 rounded-full ${CHUNK_STATUS_DOT[chunk.status] || 'bg-outline'}`} />
                      <div className="flex-1 grid grid-cols-6 gap-2 text-[10px] font-mono">
                        <div className="text-on-surface font-bold">Chunk {chunk.chunk_id}</div>
                        <div className="text-outline">{chunk.total_tokens} tok</div>
                        <div className="text-outline">${chunk.cost.toFixed(4)}</div>
                        <div className="text-outline">{formatDuration(chunk.duration_ms)}</div>
                        <div>
                          {chunk.route ? (
                            <span className={`text-[9px] px-1.5 py-0.5 rounded uppercase font-bold border ${chunk.route === 'proxy' ? 'bg-amber-500/15 text-amber-400 border-amber-500/30' : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'}`}>
                              {chunk.route}
                            </span>
                          ) : (
                            <span className="text-outline">—</span>
                          )}
                        </div>
                        <div className="text-outline truncate">{chunk.key_used || '—'}</div>
                      </div>
                      {chunk.error && (
                        <div className="text-[10px] text-error max-w-[200px] truncate" title={chunk.error}>
                          {chunk.error}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {toast && (
        <div className="fixed top-20 right-6 bg-surface-container-high text-on-surface px-4 py-3 border border-outline-variant shadow-lg text-xs font-mono z-50 max-w-xs">
          {toast}
        </div>
      )}
    </main>
  );
};

export default History;
