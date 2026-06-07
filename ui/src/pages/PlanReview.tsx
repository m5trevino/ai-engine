import React from 'react';
import { PlansAPI, PayloadsAPI, PlanListItem, PlanDetail, PayloadFileItem } from '../lib/api';
import RecentExecutions from '../components/common/RecentExecutions';

const ROUTE_BADGES: Record<string, string> = {
  direct: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  proxy: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
};

const STATUS_BADGES: Record<string, string> = {
  pending: 'bg-surface-container text-outline',
  queued: 'bg-primary/15 text-primary',
  running: 'bg-primary/15 text-primary',
  completed: 'bg-emerald-500/15 text-emerald-400',
  failed: 'bg-error/15 text-error',
  archived: 'bg-surface-container-high text-outline',
};

const PlanReview: React.FC = () => {
  const [plans, setPlans] = React.useState<PlanListItem[]>([]);
  const [planOffset, setPlanOffset] = React.useState(0);
  const [planTotal, setPlanTotal] = React.useState(0);
  const [hasMorePlans, setHasMorePlans] = React.useState(true);
  const [loadingMorePlans, setLoadingMorePlans] = React.useState(false);
  const PLAN_PAGE_SIZE = 50;
  const [selectedPlanId, setSelectedPlanId] = React.useState<string | null>(null);
  const [plan, setPlan] = React.useState<PlanDetail | null>(null);
  const [filePath, setFilePath] = React.useState('');
  const [modelId, setModelId] = React.useState('llama-3.3-70b-versatile');
  const [toast, setToast] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [executing, setExecuting] = React.useState(false);
  const [queuing, setQueuing] = React.useState(false);
  const [queueActionLoading, setQueueActionLoading] = React.useState(false);
  const [executionResult, setExecutionResult] = React.useState<{
    status: string;
    total_tokens: number;
    total_cost: number;
    duration_ms: number;
    chunks: Array<{
      chunk_id: number;
      status: string;
      route: string;
      key_used: string;
      error: string | null;
    }>;
  } | null>(null);
  const [queue, setQueue] = React.useState<{ state: string; length: number; items: Array<{ plan_id: string; position: number }> }>({ state: 'idle', length: 0, items: [] });
  const [queuePolling, setQueuePolling] = React.useState(false);
  const [execRefreshTrigger, setExecRefreshTrigger] = React.useState(0);
  const [payloads, setPayloads] = React.useState<PayloadFileItem[]>([]);
  const [executionProgress, setExecutionProgress] = React.useState<{ completed: number; total: number; failed: number; currentChunk: number | null } | null>(null);
  const [selectedPayload, setSelectedPayload] = React.useState<string>('');
  const [uploading, setUploading] = React.useState(false);
  const [dragOver, setDragOver] = React.useState(false);

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(null), 3000); };

  const refreshPlans = React.useCallback(async (targetOffset?: number) => {
    const offset = targetOffset ?? planOffset;
    try {
      const [data, count] = await Promise.all([
        PlansAPI.listPlans(undefined, undefined, PLAN_PAGE_SIZE, offset),
        PlansAPI.countPlans(),
      ]);
      setPlans(data);
      setPlanTotal(count.total);
      setHasMorePlans(offset + data.length < count.total);
      setPlanOffset(offset);
    } catch (e: any) {
      showToast(e.message);
    }
  }, [planOffset]);

  const refreshQueue = React.useCallback(() => {
    PlansAPI.getQueueSnapshot()
      .then((s) => setQueue({ state: s.state, length: s.length, items: s.items }))
      .catch((e) => showToast(e.message));
  }, []);

  React.useEffect(() => {
    refreshPlans(0);
    refreshQueue();
    PayloadsAPI.list().then(setPayloads).catch(() => {});
  }, []);

  React.useEffect(() => {
    if (!queuePolling) return;
    const iv = setInterval(() => { refreshQueue(); refreshPlans(planOffset); }, 2000);
    return () => clearInterval(iv);
  }, [queuePolling, refreshQueue, refreshPlans, planOffset]);

  // Live execution polling — when a plan is running, poll every 2s
  React.useEffect(() => {
    if (!plan || plan.status !== 'running') {
      setExecutionProgress(null);
      return;
    }
    const iv = setInterval(async () => {
      try {
        const updated = await PlansAPI.getPlan(plan.plan_id);
        setPlan(updated);
        const completed = updated.chunks.filter((c: any) => c.status === 'completed').length;
        const failed = updated.chunks.filter((c: any) => c.status === 'failed').length;
        const current = updated.chunks.find((c: any) => c.status === 'running');
        setExecutionProgress({ completed, total: updated.total_chunks, failed, currentChunk: current?.chunk_id ?? null });
        if (updated.status !== 'running') {
          setExecuting(false);
          setExecutionProgress((prev) => prev ? { ...prev, completed, total: updated.total_chunks, failed, currentChunk: null } : null);
        }
      } catch {}
    }, 2000);
    return () => clearInterval(iv);
  }, [plan?.plan_id, plan?.status]);

  React.useEffect(() => {
    if (!selectedPlanId) { setPlan(null); return; }
    setLoading(true);
    PlansAPI.getPlan(selectedPlanId)
      .then((p) => { setPlan(p); })
      .catch((e) => showToast(e.message))
      .finally(() => setLoading(false));
  }, [selectedPlanId]);

  const createPlan = async () => {
    if (!filePath.trim()) { showToast('Enter a file path'); return; }
    try {
      setLoading(true);
      const p = await PlansAPI.createPlan(filePath.trim(), modelId || undefined);
      setSelectedPlanId(p.plan_id);
      refreshPlans(0);
      showToast('Plan generated');
    } catch (e: any) {
      showToast(e.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleOverride = async (chunkId: number, currentOverride: 'direct' | 'proxy' | null, currentRoute: 'direct' | 'proxy') => {
    if (!plan) return;
    const target = currentOverride ? (currentOverride === 'direct' ? 'proxy' : 'direct') : (currentRoute === 'direct' ? 'proxy' : 'direct');
    try {
      const updated = await PlansAPI.setChunkOverride(plan.plan_id, chunkId, target);
      setPlan(updated);
      refreshPlans();
      showToast(`Chunk ${chunkId} overridden to ${target}`);
    } catch (e: any) {
      showToast(e.message);
    }
  };

  const clearOverride = async (chunkId: number) => {
    if (!plan) return;
    try {
      const updated = await PlansAPI.clearChunkOverride(plan.plan_id, chunkId);
      setPlan(updated);
      refreshPlans();
      showToast(`Chunk ${chunkId} override cleared`);
    } catch (e: any) {
      showToast(e.message);
    }
  };

  const deleteSelectedPlan = async () => {
    if (!selectedPlanId) return;
    if (!confirm('Delete this plan?')) return;
    try {
      await PlansAPI.deletePlan(selectedPlanId);
      setSelectedPlanId(null);
      refreshPlans(0);
      showToast('Plan deleted');
    } catch (e: any) {
      showToast(e.message);
    }
  };

  const executePlan = async () => {
    if (!plan) return;
    try {
      setExecuting(true);
      const res = await PlansAPI.executePlan(plan.plan_id, { temperature: 0.3, max_tokens: 1024 });
      setExecutionResult(res);
      const updated = await PlansAPI.getPlan(plan.plan_id);
      setPlan(updated);
      refreshPlans();
      setExecRefreshTrigger((n) => n + 1);
      showToast(`Execution ${res.status} — ${res.total_tokens} tokens`);
    } catch (e: any) {
      showToast(e.message);
    } finally {
      setExecuting(false);
    }
  };

  const queueSelectedPlan = async () => {
    if (!selectedPlanId) return;
    try {
      setQueuing(true);
      const res = await PlansAPI.queuePlan(selectedPlanId);
      refreshQueue();
      refreshPlans();
      showToast(`Queued at position ${res.position}`);
    } catch (e: any) {
      showToast(e.message);
    } finally {
      setQueuing(false);
    }
  };

  const unqueuePlan = async (planId: string) => {
    try {
      await PlansAPI.unqueuePlan(planId);
      refreshQueue();
      refreshPlans();
      showToast('Removed from queue');
    } catch (e: any) {
      showToast(e.message);
    }
  };

  const startQueue = async () => {
    try {
      setQueueActionLoading(true);
      await PlansAPI.startQueue({ temperature: 0.3, max_tokens: 1024 });
      setQueuePolling(true);
      refreshQueue();
      showToast('Queue runner started');
    } catch (e: any) {
      showToast(e.message);
    } finally {
      setQueueActionLoading(false);
    }
  };

  const stopQueue = async () => {
    try {
      setQueueActionLoading(true);
      await PlansAPI.stopQueue();
      setQueuePolling(false);
      refreshQueue();
      showToast('Queue runner stopped');
    } catch (e: any) {
      showToast(e.message);
    } finally {
      setQueueActionLoading(false);
    }
  };

  const reRunPlan = async (planId: string) => {
    try {
      await PlansAPI.queuePlan(planId);
      refreshQueue();
      refreshPlans();
      showToast(`Re-queued ${planId}`);
    } catch (e: any) {
      showToast(e.message);
      throw e;
    }
  };

  return (
    <main className="pt-4 pb-8 h-[calc(100vh-32px)] flex flex-col p-4 gap-4 overflow-hidden">
      {/* Header / Create */}
      <section className="bg-surface-container-low p-4 flex flex-col md:flex-row gap-3 items-stretch md:items-center">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-primary">route</span>
          <span className="font-headline font-bold text-sm tracking-tight uppercase">PLAN REVIEW & OVERRIDE</span>
        </div>
        <div className="flex-1 flex gap-2 items-center">
          <select
            value={selectedPayload}
            onChange={(e) => {
              const name = e.target.value;
              setSelectedPayload(name);
              setFilePath(name ? `/root/hetzner/ai-engine/payloads/${name}` : '');
            }}
            className="bg-surface-container px-3 py-2 text-xs font-mono text-on-surface outline-none border border-outline-variant/20 focus:border-primary"
          >
            <option value="">— select payload —</option>
            {payloads.map((p) => (
              <option key={p.name} value={p.name}>{p.name} ({(p.size / 1024).toFixed(1)} KB)</option>
            ))}
          </select>
          <input
            value={filePath}
            onChange={(e) => { setFilePath(e.target.value); setSelectedPayload(''); }}
            placeholder="/path/to/file.py"
            className="flex-1 bg-surface-container px-3 py-2 text-xs font-mono text-on-surface outline-none border border-outline-variant/20 focus:border-primary"
          />
          <input
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
            placeholder="model-id"
            className="w-48 bg-surface-container px-3 py-2 text-xs font-mono text-on-surface outline-none border border-outline-variant/20 focus:border-primary"
          />
          <button
            onClick={createPlan}
            disabled={loading}
            className="bg-primary-container text-on-primary-container px-4 py-2 font-headline font-bold text-xs tracking-widest uppercase hover:bg-primary transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-sm">auto_fix_high</span>
            GENERATE
          </button>
          <label
            className={`cursor-pointer px-3 py-2 border text-xs font-mono transition-colors flex items-center gap-2 ${dragOver ? 'border-primary bg-primary/10 text-primary' : 'border-outline-variant/30 text-outline hover:text-on-surface hover:bg-surface-container'}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={async (e) => {
              e.preventDefault();
              setDragOver(false);
              const files = e.dataTransfer.files;
              if (files.length > 0) {
                setUploading(true);
                try {
                  for (const file of Array.from(files)) {
                    await PayloadsAPI.upload(file);
                  }
                  const list = await PayloadsAPI.list();
                  setPayloads(list);
                  showToast(`${files.length} file(s) uploaded`);
                } catch (e: any) {
                  showToast(e.message);
                } finally {
                  setUploading(false);
                }
              }
            }}
          >
            <span className="material-symbols-outlined text-sm">upload_file</span>
            <span className="hidden md:inline">{uploading ? '…' : 'Drop or click'}</span>
            <input
              type="file"
              className="hidden"
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                setUploading(true);
                try {
                  await PayloadsAPI.upload(file);
                  const list = await PayloadsAPI.list();
                  setPayloads(list);
                  showToast(`Uploaded: ${file.name}`);
                } catch (err: any) {
                  showToast(err.message);
                } finally {
                  setUploading(false);
                }
              }}
            />
          </label>
        </div>
      </section>

      {/* Body */}
      <section className="flex-1 flex gap-4 overflow-hidden min-h-0">
        {/* Sidebar */}
        <aside className="w-80 bg-surface-container-low flex flex-col gap-2 p-3 overflow-hidden">
          {/* Plan List */}
          <div className="flex-1 min-h-0 flex flex-col gap-2">
            <div className="text-[10px] font-headline font-bold text-outline uppercase tracking-widest">Stored Plans</div>
            <div className="flex-1 overflow-y-auto pr-1 space-y-2">
              {plans.map((p) => (
                <button
                  key={p.plan_id}
                  onClick={() => setSelectedPlanId(p.plan_id)}
                  className={`w-full text-left p-3 border-l-4 transition-colors ${selectedPlanId === p.plan_id ? 'border-tertiary bg-surface-container' : 'border-outline-variant bg-surface-container-low hover:bg-surface-container'}`}
                >
                  <div className="flex justify-between items-start gap-2">
                    <div className="font-mono text-xs text-on-surface truncate">{p.plan_id}</div>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded uppercase font-bold border ${STATUS_BADGES[p.status] || STATUS_BADGES.pending}`}>{p.status}</span>
                  </div>
                  <div className="text-[10px] font-mono text-outline truncate mt-1">{p.file_path}</div>
                  <div className="flex justify-between text-[10px] font-mono text-outline mt-2">
                    <span>{p.total_chunks} chunks</span>
                    <span>{p.overridden_chunks > 0 ? `${p.overridden_chunks} overridden` : 'auto'}</span>
                  </div>
                </button>
              ))}
              {plans.length === 0 && !loadingMorePlans && (
                <div className="text-center text-xs text-outline py-8">No plans yet.<br />Generate one to start.</div>
              )}
              {planTotal > 0 && (
                <div className="flex items-center justify-between px-2 py-2 border-t border-outline-variant/20">
                  <span className="text-[9px] font-mono text-outline">
                    {planOffset + 1}-{Math.min(planOffset + plans.length, planTotal)} of {planTotal}
                  </span>
                  <div className="flex gap-1">
                    <button
                      onClick={() => { setLoadingMorePlans(true); refreshPlans(Math.max(0, planOffset - PLAN_PAGE_SIZE)).finally(() => setLoadingMorePlans(false)); }}
                      disabled={loadingMorePlans || planOffset === 0}
                      className="px-2 py-1 text-[9px] font-headline font-bold uppercase tracking-widest text-outline hover:text-on-surface hover:bg-surface-container transition-colors disabled:opacity-30"
                    >
                      Prev
                    </button>
                    <button
                      onClick={() => { setLoadingMorePlans(true); refreshPlans(planOffset + PLAN_PAGE_SIZE).finally(() => setLoadingMorePlans(false)); }}
                      disabled={loadingMorePlans || !hasMorePlans}
                      className="px-2 py-1 text-[9px] font-headline font-bold uppercase tracking-widest text-outline hover:text-on-surface hover:bg-surface-container transition-colors disabled:opacity-30"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Queue Panel */}
          <div className="border-t border-outline-variant/20 pt-3 flex flex-col gap-2 min-h-0 flex-1">
            <div className="flex justify-between items-center px-1">
              <div className="text-[10px] font-headline font-bold text-outline uppercase tracking-widest">Queue</div>
              <div className="flex items-center gap-1">
                <span className={`w-2 h-2 rounded-full ${queue.state === 'running' ? 'bg-tertiary animate-pulse' : 'bg-outline'}`} />
                <span className="text-[10px] font-mono text-outline uppercase">{queue.state}</span>
              </div>
            </div>
            <div className="flex gap-1">
              <button
                onClick={startQueue}
                disabled={queue.state === 'running' || queue.items.length === 0 || queueActionLoading}
                className="flex-1 bg-primary-container text-on-primary-container py-2 font-headline font-bold text-[10px] tracking-widest uppercase hover:bg-primary transition-colors disabled:opacity-50 flex items-center justify-center gap-1"
              >
                <span className="material-symbols-outlined text-sm">play_arrow</span>
                START
              </button>
              <button
                onClick={stopQueue}
                disabled={queue.state !== 'running' || queueActionLoading}
                className="flex-1 bg-surface-container-high text-on-surface py-2 font-headline font-bold text-[10px] tracking-widest uppercase hover:bg-surface-bright transition-colors disabled:opacity-50 flex items-center justify-center gap-1"
              >
                <span className="material-symbols-outlined text-sm">stop</span>
                STOP
              </button>
            </div>
            <div className="flex-1 overflow-y-auto pr-1 space-y-1">
              {queue.items.map((item) => (
                <div key={item.plan_id} className="flex justify-between items-center p-2 bg-surface-container text-xs">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-outline">#{item.position}</span>
                    <span className="font-mono text-on-surface truncate max-w-[120px]">{item.plan_id}</span>
                  </div>
                  <button onClick={() => unqueuePlan(item.plan_id)} className="text-error hover:bg-error/10 p-1 rounded">
                    <span className="material-symbols-outlined text-sm">close</span>
                  </button>
                </div>
              ))}
              {queue.items.length === 0 && (
                <div className="text-center text-[10px] text-outline py-4">Queue empty</div>
              )}
            </div>
          </div>

          {/* Recent Executions */}
          <div className="border-t border-outline-variant/20 pt-3 flex flex-col gap-2 min-h-0 flex-1">
            <RecentExecutions onReRun={reRunPlan} refreshTrigger={execRefreshTrigger} />
          </div>
        </aside>

        {/* Detail */}
        <div className="flex-1 bg-surface-container-low flex flex-col overflow-hidden">
          {!plan && !loading && (
            <div className="flex-1 flex items-center justify-center text-outline text-sm">
              Select a plan or generate a new one.
            </div>
          )}
          {loading && (
            <div className="flex-1 flex items-center justify-center text-outline text-sm">
              <span className="material-symbols-outlined animate-spin mr-2">progress_activity</span>
              Loading...
            </div>
          )}
          {plan && !loading && (
            <>
              {/* Plan header */}
              <div className="p-4 border-b border-outline-variant/20 flex justify-between items-start gap-4">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <span className={`text-[10px] px-2 py-0.5 rounded uppercase font-bold border ${STATUS_BADGES[plan.status] || STATUS_BADGES.pending}`}>{plan.status}</span>
                    <span className="font-mono text-xs text-primary">{plan.plan_id}</span>
                  </div>
                  <div className="text-sm text-on-surface font-mono truncate">{plan.file_path}</div>
                  <div className="text-[10px] font-mono text-outline mt-1">
                    {plan.total_chunks} chunks · {plan.total_tokens} tokens · {plan.model_id} · raw {plan.estimated_total_seconds.toFixed(1)}s · makespan {plan.makespan_seconds.toFixed(1)}s
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={queueSelectedPlan}
                    disabled={!selectedPlanId || queue.state === 'running' || queuing}
                    className="bg-secondary-container text-on-secondary-container px-4 py-2 font-headline font-bold text-xs tracking-widest uppercase hover:bg-secondary transition-colors disabled:opacity-50 flex items-center gap-2"
                  >
                    <span className="material-symbols-outlined text-sm">{queuing ? 'progress_activity' : 'queue'}</span>
                    {queuing ? 'QUEUING' : 'QUEUE'}
                  </button>
                  <button
                    onClick={executePlan}
                    disabled={executing || plan.status === 'running'}
                    className="bg-primary-container text-on-primary-container px-4 py-2 font-headline font-bold text-xs tracking-widest uppercase hover:bg-primary transition-colors disabled:opacity-50 flex items-center gap-2"
                  >
                    <span className="material-symbols-outlined text-sm">{executing ? 'progress_activity' : 'play_arrow'}</span>
                    {executing ? 'EXECUTING' : 'EXECUTE'}
                  </button>
                  <button
                    onClick={deleteSelectedPlan}
                    disabled={executing || queuing}
                    className="text-error hover:bg-error/10 px-3 py-2 flex items-center gap-1 text-xs font-headline uppercase tracking-widest disabled:opacity-50"
                  >
                    <span className="material-symbols-outlined text-sm">delete</span>
                    Delete
                  </button>
                </div>
              </div>

              {executionResult && (
                <div className="px-4 py-2 bg-surface-container border-b border-outline-variant/20 flex items-center gap-4 text-[10px] font-mono">
                  <span className="text-outline uppercase">Last Run:</span>
                  <span className={executionResult.status === 'completed' ? 'text-emerald-400' : executionResult.status === 'failed' ? 'text-error' : 'text-amber-400'}>
                    {executionResult.status.toUpperCase()}
                  </span>
                  <span className="text-outline">{executionResult.total_tokens} tokens</span>
                  <span className="text-outline">${executionResult.total_cost.toFixed(4)}</span>
                  <span className="text-outline">{executionResult.duration_ms}ms</span>
                </div>
              )}

              {/* Chunk grid */}
              <div className="flex-1 overflow-y-auto p-4">
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                  {plan.chunks.map((c) => {
                    const effectiveRoute = c.manual_override || c.route;
                    const isOverridden = Boolean(c.manual_override);
                    return (
                      <div
                        key={c.chunk_id}
                        className={`bg-surface-container p-4 border-l-4 ${isOverridden ? 'border-tertiary' : effectiveRoute === 'proxy' ? 'border-amber-500/60' : 'border-emerald-500/60'} flex flex-col gap-3`}
                      >
                        <div className="flex justify-between items-start">
                          <div className="flex items-center gap-3">
                            <span className="font-headline font-bold text-sm text-on-surface">Chunk {c.chunk_id}</span>
                            <span className={`text-[10px] px-2 py-0.5 rounded uppercase font-bold border ${ROUTE_BADGES[effectiveRoute]}`}>
                              {isOverridden ? `${effectiveRoute} (manual)` : effectiveRoute}
                            </span>
                          </div>
                          <span className="text-[10px] font-mono text-outline">{c.token_count} tok · {c.estimated_seconds.toFixed(1)}s {c.wait_seconds > 0 ? `(+${c.wait_seconds.toFixed(1)}s wait)` : ''}</span>
                        </div>

                        {/* Improved Rationale */}
                        <div className="bg-surface-container-low p-2.5 rounded-sm">
                          <div className="flex items-start gap-2">
                            <span className="material-symbols-outlined text-[14px] text-outline mt-0.5 shrink-0">lightbulb</span>
                            <p className="text-[11px] text-on-surface-variant leading-relaxed line-clamp-2" title={c.rationale || 'No rationale provided'}>
                              {c.rationale || 'No rationale provided'}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-3 pt-2 border-t border-outline-variant/10">
                          <span className="text-[10px] font-mono text-outline uppercase">Auto:</span>
                          <span className={`text-[10px] px-2 py-0.5 rounded uppercase font-bold border ${ROUTE_BADGES[c.route]}`}>{c.route}</span>

                          <div className="flex-1" />

                          <button
                            onClick={() => toggleOverride(c.chunk_id, c.manual_override, c.route)}
                            disabled={executing}
                            className="text-[10px] font-headline font-bold uppercase tracking-wider px-3 py-1.5 bg-surface-container-high hover:bg-primary/20 text-primary border border-primary/30 transition-colors disabled:opacity-50"
                          >
                            Flip to {c.manual_override ? (c.manual_override === 'direct' ? 'proxy' : 'direct') : (c.route === 'direct' ? 'proxy' : 'direct')}
                          </button>

                          {isOverridden && (
                            <button
                              onClick={() => clearOverride(c.chunk_id)}
                              disabled={executing}
                              className="text-[10px] font-headline font-bold uppercase tracking-wider px-3 py-1.5 bg-surface-container-high hover:bg-error/20 text-error border border-error/30 transition-colors disabled:opacity-50"
                            >
                              Clear
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          )}
        </div>
      </section>

      {/* Toast — top-right for better visibility */}
      {toast && (
        <div className="fixed top-20 right-6 bg-surface-container-high text-on-surface px-4 py-3 border border-outline-variant shadow-lg text-xs font-mono z-50 max-w-xs">
          {toast}
        </div>
      )}
    </main>
  );
};

export default PlanReview;
