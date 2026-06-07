import React from 'react';
import { StressAPI, StressLiveStatus, StressReport, StressListItem, StressCompareItem } from '../lib/api';

const STATUS_BADGES: Record<string, string> = {
  completed: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  failed: 'bg-error/15 text-error border-error/30',
  partial: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  running: 'bg-primary/15 text-primary border-primary/30',
  aborted: 'bg-surface-container-high text-outline border-outline-variant/30',
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

const Stress: React.FC = () => {
  const [filePaths, setFilePaths] = React.useState('');
  const [modelId, setModelId] = React.useState('llama-3.3-70b-versatile');
  const [concurrency, setConcurrency] = React.useState(3);
  const [temperature, setTemperature] = React.useState(0.3);
  const [maxTokens, setMaxTokens] = React.useState(1024);
  const [running, setRunning] = React.useState(false);
  const [runId, setRunId] = React.useState<string | null>(null);
  const [live, setLive] = React.useState<StressLiveStatus | null>(null);
  const [report, setReport] = React.useState<StressReport | null>(null);
  const [pastRuns, setPastRuns] = React.useState<StressListItem[]>([]);
  const [runOffset, setRunOffset] = React.useState(0);
  const [runTotal, setRunTotal] = React.useState(0);
  const [hasMoreRuns, setHasMoreRuns] = React.useState(true);
  const [loadingMoreRuns, setLoadingMoreRuns] = React.useState(false);
  const RUN_PAGE_SIZE = 20;
  const [loading, setLoading] = React.useState(false);
  const [toast, setToast] = React.useState<string | null>(null);

  // Compare state
  const [selectedRuns, setSelectedRuns] = React.useState<Set<string>>(new Set());
  const [compareData, setCompareData] = React.useState<StressCompareItem[] | null>(null);
  const [compareLoading, setCompareLoading] = React.useState(false);

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(null), 3000); };

  const refreshPast = React.useCallback(async (targetOffset?: number) => {
    const offset = targetOffset ?? runOffset;
    try {
      const [data, count] = await Promise.all([
        StressAPI.listRuns(RUN_PAGE_SIZE, offset),
        StressAPI.countRuns(),
      ]);
      setPastRuns(data);
      setRunTotal(count.total);
      setHasMoreRuns(offset + data.length < count.total);
      setRunOffset(offset);
    } catch {}
  }, [runOffset]);

  React.useEffect(() => {
    refreshPast(0);
  }, []);

  // Live polling during run
  React.useEffect(() => {
    if (!runId || !running) return;
    const iv = setInterval(async () => {
      try {
        const status = await StressAPI.getStatus(runId);
        setLive(status);
        if (status.state !== 'running') {
          setRunning(false);
          const rep = await StressAPI.getReport(runId);
          setReport(rep);
          refreshPast();
        }
      } catch (e: any) {
        showToast(e.message);
        setRunning(false);
      }
    }, 1000);
    return () => clearInterval(iv);
  }, [runId, running, refreshPast]);

  const start = async () => {
    const paths = filePaths.split('\n').map((p) => p.trim()).filter(Boolean);
    if (paths.length === 0) { showToast('Enter at least one file path'); return; }
    try {
      setLoading(true);
      setReport(null);
      setLive(null);
      const res = await StressAPI.start({
        file_paths: paths,
        model_id: modelId,
        concurrency,
        temperature,
        max_tokens: maxTokens,
      });
      setRunId(res.run_id);
      setRunning(true);
      showToast(`Stress run started: ${res.run_id}`);
    } catch (e: any) {
      showToast(e.message);
    } finally {
      setLoading(false);
    }
  };

  const abort = async () => {
    if (!runId) return;
    try {
      await StressAPI.abort(runId);
      showToast('Abort signaled');
    } catch (e: any) {
      showToast(e.message);
    }
  };

  const loadReport = async (id: string) => {
    try {
      setLoading(true);
      const rep = await StressAPI.getReport(id);
      setReport(rep);
      const status = await StressAPI.getStatus(id);
      setLive(status);
    } catch (e: any) {
      showToast(e.message);
    } finally {
      setLoading(false);
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
      const res = await StressAPI.compare(ids);
      setCompareData(res.runs);
    } catch (e: any) {
      showToast(e.message);
    } finally {
      setCompareLoading(false);
    }
  };

  const exportSingleJson = () => {
    if (!report) return;
    downloadJson(report, `${report.run_id}.json`);
  };

  const exportSingleCsv = () => {
    if (!report) return;
    const rows = [{
      run_id: report.run_id,
      status: report.status,
      total_plans: report.total_plans,
      completed_plans: report.completed_plans,
      failed_plans: report.failed_plans,
      total_tokens: report.total_tokens,
      total_cost: report.total_cost,
      duration_ms: report.duration_ms,
      proxy_pct: report.proxy_effectiveness?.proxy_pct ?? 0,
    }];
    downloadCsv(rows, `${report.run_id}.csv`);
  };

  const exportCompareJson = () => {
    if (!compareData) return;
    downloadJson(compareData, 'stress_comparison.json');
  };

  const exportCompareCsv = () => {
    if (!compareData) return;
    const rows = compareData.map((r) => ({
      run_id: r.run_id,
      status: r.status,
      total_plans: r.total_plans,
      completed_plans: r.completed_plans,
      failed_plans: r.failed_plans,
      total_tokens: r.total_tokens,
      total_cost: r.total_cost,
      duration_ms: r.duration_ms,
      proxy_pct: r.proxy_pct,
    }));
    downloadCsv(rows, 'stress_comparison.csv');
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts * 1000);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <main className="pt-4 pb-8 h-[calc(100vh-32px)] flex flex-col p-4 gap-4 overflow-hidden">
      {/* Header */}
      <section className="bg-surface-container-low p-4 flex flex-col md:flex-row gap-3 items-stretch md:items-center">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-primary">fitness_center</span>
          <span className="font-headline font-bold text-sm tracking-tight uppercase">STRESS TEST</span>
        </div>
        <div className="flex-1 flex gap-2">
          <button
            onClick={start}
            disabled={running || loading}
            className="bg-primary-container text-on-primary-container px-4 py-2 font-headline font-bold text-xs tracking-widest uppercase hover:bg-primary transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-sm">{running ? 'progress_activity' : 'play_arrow'}</span>
            {running ? 'RUNNING' : 'START'}
          </button>
          {running && (
            <button
              onClick={abort}
              className="bg-error/15 text-error px-4 py-2 font-headline font-bold text-xs tracking-widest uppercase hover:bg-error/30 transition-colors flex items-center gap-2"
            >
              <span className="material-symbols-outlined text-sm">stop</span>
              ABORT
            </button>
          )}
          {report && (
            <>
              <button onClick={exportSingleJson} className="bg-surface-container-high text-on-surface px-3 py-2 font-headline font-bold text-[10px] tracking-widest uppercase hover:bg-surface-bright transition-colors flex items-center gap-1">
                <span className="material-symbols-outlined text-sm">download</span> JSON
              </button>
              <button onClick={exportSingleCsv} className="bg-surface-container-high text-on-surface px-3 py-2 font-headline font-bold text-[10px] tracking-widest uppercase hover:bg-surface-bright transition-colors flex items-center gap-1">
                <span className="material-symbols-outlined text-sm">download</span> CSV
              </button>
            </>
          )}
        </div>
      </section>

      <section className="flex-1 flex gap-4 overflow-hidden min-h-0">
        {/* Sidebar: config + past runs */}
        <aside className="w-80 bg-surface-container-low flex flex-col gap-3 p-3 overflow-hidden">
          {/* Config */}
          <div className="flex flex-col gap-2">
            <div className="text-[10px] font-headline font-bold text-outline uppercase tracking-widest">Target Files</div>
            <textarea
              value={filePaths}
              onChange={(e) => setFilePaths(e.target.value)}
              placeholder="/path/to/file1.py&#10;/path/to/file2.py"
              rows={4}
              disabled={running}
              className="bg-surface-container px-3 py-2 text-xs font-mono text-on-surface outline-none border border-outline-variant/20 focus:border-primary resize-none"
            />
            <div className="text-[10px] font-mono text-outline">{filePaths.split('\n').filter(Boolean).length} files</div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-mono text-outline">MODEL</span>
              <input value={modelId} onChange={(e) => setModelId(e.target.value)} disabled={running} className="bg-surface-container px-2 py-1 text-xs font-mono text-on-surface outline-none border border-outline-variant/20 focus:border-primary" />
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-mono text-outline">CONCURRENCY</span>
              <input type="number" min={1} max={20} value={concurrency} onChange={(e) => setConcurrency(parseInt(e.target.value) || 1)} disabled={running} className="bg-surface-container px-2 py-1 text-xs font-mono text-on-surface outline-none border border-outline-variant/20 focus:border-primary" />
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-mono text-outline">TEMP</span>
              <input type="number" min={0} max={2} step={0.1} value={temperature} onChange={(e) => setTemperature(parseFloat(e.target.value))} disabled={running} className="bg-surface-container px-2 py-1 text-xs font-mono text-on-surface outline-none border border-outline-variant/20 focus:border-primary" />
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-mono text-outline">MAX TOKENS</span>
              <input type="number" min={1} max={8192} value={maxTokens} onChange={(e) => setMaxTokens(parseInt(e.target.value) || 1)} disabled={running} className="bg-surface-container px-2 py-1 text-xs font-mono text-on-surface outline-none border border-outline-variant/20 focus:border-primary" />
            </div>
          </div>

          {/* Past Runs */}
          <div className="border-t border-outline-variant/20 pt-3 flex-1 min-h-0 flex flex-col gap-2">
            <div className="flex justify-between items-center">
              <div className="text-[10px] font-headline font-bold text-outline uppercase tracking-widest">Past Runs</div>
              {selectedRuns.size >= 2 && (
                <button
                  onClick={doCompare}
                  disabled={compareLoading}
                  className="bg-secondary-container text-on-secondary-container px-2 py-1 font-headline font-bold text-[9px] tracking-widest uppercase hover:bg-secondary transition-colors disabled:opacity-50 flex items-center gap-1"
                >
                  <span className="material-symbols-outlined text-sm">{compareLoading ? 'progress_activity' : 'compare_arrows'}</span>
                  Compare ({selectedRuns.size})
                </button>
              )}
            </div>
            <div className="flex-1 overflow-y-auto pr-1 space-y-2">
              {pastRuns.map((r) => (
                <div
                  key={r.run_id}
                  className={`w-full text-left p-2 bg-surface-container border-l-4 transition-colors ${selectedRuns.has(r.run_id) ? 'border-tertiary bg-surface-container-high' : 'border-secondary/40 hover:bg-surface-container-high'}`}
                >
                  <div className="flex items-start gap-2">
                    <input
                      type="checkbox"
                      checked={selectedRuns.has(r.run_id)}
                      onChange={() => toggleSelectRun(r.run_id)}
                      className="mt-0.5 accent-primary shrink-0"
                    />
                    <button onClick={() => loadReport(r.run_id)} className="flex-1 text-left min-w-0">
                      <div className="flex justify-between items-start gap-2">
                        <span className="font-mono text-[10px] text-on-surface truncate">{r.run_id}</span>
                        <span className={`text-[9px] px-1.5 py-0.5 rounded uppercase font-bold border ${STATUS_BADGES[r.status] || STATUS_BADGES.partial}`}>{r.status}</span>
                      </div>
                      <div className="flex justify-between text-[10px] font-mono text-outline mt-1">
                        <span>{r.completed_plans}/{r.total_plans} plans</span>
                        <span>{formatDuration(r.duration_ms)}</span>
                      </div>
                    </button>
                  </div>
                </div>
              ))}
              {pastRuns.length === 0 && !loadingMoreRuns && (
                <div className="text-center text-xs text-outline py-4">No stress runs yet.</div>
              )}
              {runTotal > 0 && (
                <div className="flex items-center justify-between px-2 py-2 border-t border-outline-variant/20">
                  <span className="text-[9px] font-mono text-outline">
                    {runOffset + 1}-{Math.min(runOffset + pastRuns.length, runTotal)} of {runTotal}
                  </span>
                  <div className="flex gap-1">
                    <button
                      onClick={() => { setLoadingMoreRuns(true); refreshPast(Math.max(0, runOffset - RUN_PAGE_SIZE)).finally(() => setLoadingMoreRuns(false)); }}
                      disabled={loadingMoreRuns || runOffset === 0}
                      className="px-2 py-1 text-[9px] font-headline font-bold uppercase tracking-widest text-outline hover:text-on-surface hover:bg-surface-container transition-colors disabled:opacity-30"
                    >
                      Prev
                    </button>
                    <button
                      onClick={() => { setLoadingMoreRuns(true); refreshPast(runOffset + RUN_PAGE_SIZE).finally(() => setLoadingMoreRuns(false)); }}
                      disabled={loadingMoreRuns || !hasMoreRuns}
                      className="px-2 py-1 text-[9px] font-headline font-bold uppercase tracking-widest text-outline hover:text-on-surface hover:bg-surface-container transition-colors disabled:opacity-30"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </aside>

        {/* Main content: live + report + compare */}
        <div className="flex-1 bg-surface-container-low flex flex-col overflow-hidden">
          {/* Live Status */}
          {live && live.state === 'running' && (
            <div className="p-4 border-b border-outline-variant/20">
              <div className="flex items-center gap-3 mb-3">
                <span className="w-2 h-2 bg-tertiary animate-pulse rounded-full" />
                <span className="font-headline font-bold text-xs uppercase text-primary">Live Run</span>
                <span className="font-mono text-[10px] text-outline">{live.run_id}</span>
              </div>
              <div className="grid grid-cols-4 gap-2 text-[10px] font-mono">
                <div className="bg-surface-container p-2">
                  <div className="text-outline">PLANS</div>
                  <div className="text-on-surface font-bold">{live.completed_plans}/{live.total_plans}</div>
                </div>
                <div className="bg-surface-container p-2">
                  <div className="text-outline">CHUNKS</div>
                  <div className="text-on-surface font-bold">{live.completed_chunks}/{live.total_chunks}</div>
                </div>
                <div className="bg-surface-container p-2">
                  <div className="text-outline">TOKENS</div>
                  <div className="text-on-surface font-bold">{live.total_tokens.toLocaleString()}</div>
                </div>
                <div className="bg-surface-container p-2">
                  <div className="text-outline">ELAPSED</div>
                  <div className="text-on-surface font-bold">{formatDuration(live.elapsed_ms)}</div>
                </div>
              </div>
              {live.current_file && (
                <div className="mt-2 text-[10px] font-mono text-outline truncate">Processing: {live.current_file}</div>
              )}
            </div>
          )}

          {/* Comparison Panel */}
          {compareData && (
            <div className="p-4 border-b border-outline-variant/20 bg-surface-container">
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
                      { label: 'Status', get: (r: StressCompareItem) => r.status },
                      { label: 'Plans', get: (r: StressCompareItem) => `${r.completed_plans}/${r.total_plans}` },
                      { label: 'Chunks', get: (r: StressCompareItem) => `${r.completed_chunks}/${r.total_chunks}` },
                      { label: 'Tokens', get: (r: StressCompareItem) => r.total_tokens.toLocaleString() },
                      { label: 'Cost', get: (r: StressCompareItem) => `$${r.total_cost.toFixed(4)}` },
                      { label: 'Duration', get: (r: StressCompareItem) => formatDuration(r.duration_ms) },
                      { label: 'Proxy %', get: (r: StressCompareItem) => `${r.proxy_pct}%` },
                      { label: 'Failed', get: (r: StressCompareItem) => r.failed_plans.toString() },
                      { label: 'Skipped', get: (r: StressCompareItem) => r.skipped_chunks.toString() },
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
            </div>
          )}

          {/* Report */}
          {report && (
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Summary */}
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-1">
                {[
                  { label: 'PLANS', value: `${report.completed_plans}/${report.total_plans}` },
                  { label: 'CHUNKS', value: `${report.completed_chunks}/${report.total_chunks}` },
                  { label: 'TOKENS', value: report.total_tokens.toLocaleString() },
                  { label: 'COST', value: `$${report.total_cost.toFixed(4)}` },
                  { label: 'DURATION', value: formatDuration(report.duration_ms) },
                  { label: 'STATUS', value: report.status.toUpperCase(), color: report.status === 'completed' ? 'text-emerald-400' : report.status === 'failed' ? 'text-error' : 'text-amber-400' },
                ].map((s, i) => (
                  <div key={i} className="bg-surface-container-high p-3 flex flex-col justify-between aspect-square">
                    <span className="font-headline text-[10px] text-outline uppercase">{s.label}</span>
                    <div className={`font-mono text-xl font-bold ${s.color || 'text-on-surface'}`}>{s.value}</div>
                  </div>
                ))}
              </div>

              {/* Proxy Effectiveness */}
              {report.proxy_effectiveness && (
                <div className="bg-surface-container p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="material-symbols-outlined text-sm text-tertiary">route</span>
                    <span className="font-headline font-bold text-xs uppercase text-primary">Proxy Effectiveness</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-[10px] font-mono">
                    <div><span className="text-outline">PROXY CHUNKS:</span> <span className="text-amber-400 font-bold">{report.proxy_effectiveness.proxy_chunks}</span></div>
                    <div><span className="text-outline">DIRECT CHUNKS:</span> <span className="text-emerald-400 font-bold">{report.proxy_effectiveness.direct_chunks}</span></div>
                    <div><span className="text-outline">PROXY %:</span> <span className="text-secondary font-bold">{report.proxy_effectiveness.proxy_pct}%</span></div>
                  </div>
                </div>
              )}

              {/* Wait Distribution */}
              {report.wait_distribution && (
                <div className="bg-surface-container p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="material-symbols-outlined text-sm text-tertiary">timer</span>
                    <span className="font-headline font-bold text-xs uppercase text-primary">Wait Time Distribution</span>
                  </div>
                  <div className="grid grid-cols-5 gap-2 text-[10px] font-mono">
                    <div><span className="text-outline">MIN:</span> <span className="text-on-surface font-bold">{formatDuration(report.wait_distribution.min_ms)}</span></div>
                    <div><span className="text-outline">MEDIAN:</span> <span className="text-on-surface font-bold">{formatDuration(report.wait_distribution.median_ms)}</span></div>
                    <div><span className="text-outline">P95:</span> <span className="text-on-surface font-bold">{formatDuration(report.wait_distribution.p95_ms)}</span></div>
                    <div><span className="text-outline">P99:</span> <span className="text-on-surface font-bold">{formatDuration(report.wait_distribution.p99_ms)}</span></div>
                    <div><span className="text-outline">MAX:</span> <span className="text-on-surface font-bold">{formatDuration(report.wait_distribution.max_ms)}</span></div>
                  </div>
                </div>
              )}

              {/* Per-Key Stats */}
              {Object.keys(report.per_key_stats).length > 0 && (
                <div className="bg-surface-container p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="material-symbols-outlined text-sm text-tertiary">vpn_key</span>
                    <span className="font-headline font-bold text-xs uppercase text-primary">Per-Key Burn</span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left font-mono text-[10px]">
                      <thead className="border-b border-outline-variant/20">
                        <tr>
                          <th className="p-2 font-normal text-outline">KEY</th>
                          <th className="p-2 font-normal text-outline">CHUNKS</th>
                          <th className="p-2 font-normal text-outline">TOKENS</th>
                          <th className="p-2 font-normal text-outline">COST</th>
                          <th className="p-2 font-normal text-outline">AVG LATENCY</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-outline-variant/5">
                        {Object.entries(report.per_key_stats).map(([key, stats]: [string, any]) => (
                          <tr key={key} className="hover:bg-surface-container-low">
                            <td className="p-2 text-on-surface">{key}</td>
                            <td className="p-2 text-on-surface">{stats.chunks}</td>
                            <td className="p-2 text-on-surface">{stats.tokens.toLocaleString()}</td>
                            <td className="p-2 text-on-surface">${stats.cost.toFixed(4)}</td>
                            <td className="p-2 text-on-surface">{formatDuration(stats.avg_duration_ms)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Bottlenecks */}
              {report.bottlenecks.length > 0 && (
                <div className="bg-surface-container p-4 border-l-4 border-error/60">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="material-symbols-outlined text-sm text-error">warning</span>
                    <span className="font-headline font-bold text-xs uppercase text-error">Bottlenecks</span>
                  </div>
                  <ul className="space-y-1">
                    {report.bottlenecks.map((b, i) => (
                      <li key={i} className="text-[11px] font-mono text-on-surface-variant">• {b}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Suggestions */}
              {report.suggestions.length > 0 && (
                <div className="bg-surface-container p-4 border-l-4 border-tertiary/60">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="material-symbols-outlined text-sm text-tertiary">lightbulb</span>
                    <span className="font-headline font-bold text-xs uppercase text-tertiary">Tuning Suggestions</span>
                  </div>
                  <ul className="space-y-1">
                    {report.suggestions.map((s, i) => (
                      <li key={i} className="text-[11px] font-mono text-on-surface-variant">• {s}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {!report && !live && !compareData && !loading && (
            <div className="flex-1 flex items-center justify-center text-outline text-sm">
              Configure files and click START to run a stress test.
            </div>
          )}

          {loading && !report && !live && !compareData && (
            <div className="flex-1 flex items-center justify-center text-outline text-sm">
              <span className="material-symbols-outlined animate-spin mr-2">progress_activity</span>
              Loading...
            </div>
          )}
        </div>
      </section>

      {toast && (
        <div className="fixed top-20 right-6 bg-surface-container-high text-on-surface px-4 py-3 border border-outline-variant shadow-lg text-xs font-mono z-50 max-w-xs">
          {toast}
        </div>
      )}
    </main>
  );
};

export default Stress;
