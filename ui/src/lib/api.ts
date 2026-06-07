/**
 * PEACOCK ENGINE V3 — Syndicate Weaver Generated API Client
 */
import React from 'react';

const isProd = typeof window !== 'undefined' && window.location.hostname !== 'localhost';
export const API_BASE = isProd ? '' : 'http://localhost:3099';

async function peacockFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text().catch(() => 'Unknown error');
    throw new Error(`PEACOCK_API_ERROR [${res.status}]: ${err}`);
  }
  return res.json() as Promise<T>;
}

function createSSE(path: string): EventSource {
  return new EventSource(`${API_BASE}${path}`);
}

// ─── DASHBOARD ───
export interface HealthResponse {
  status: string;
  system: string;
  version: string;
  integrity: { groq: number; google: number; deepseek: number; mistral: number };
  features: Record<string, boolean>;
  metrics: Record<string, unknown>;
}

export interface TelemetryPayload {
  time: string;
  rpm: number;
  tps: number;
  tokens: number;
  cost: number;
  success_rate: number;
  proxy_tokens: number;
  direct_tokens: number;
  proxy_cost: number;
  direct_cost: number;
  proxy_strikes: number;
  direct_strikes: number;
  queue_depth: number;
  queue_state: string;
  msg: string;
  type: string;
}

export interface DashboardSettings {
  tunnel_mode: boolean;
  quiet_mode: boolean;
  success_logging: boolean;
  failed_logging: boolean;
  verbose: boolean;
}

export interface HistoryEntry {
  timestamp: string;
  tag: string;
  gateway: string;
  model: string;
  tokens: string;
  cost: string;
  status: 'SUCCESS' | 'FAILED';
}

export const DashboardAPI = {
  getHealth(): Promise<HealthResponse> { return peacockFetch('/health'); },
  streamTelemetry(onData: (p: TelemetryPayload) => void, onError?: (e: Event) => void): EventSource {
    const es = createSSE('/v1/telemetry/stream');
    es.onmessage = (ev) => { try { onData(JSON.parse(ev.data)); } catch {} };
    if (onError) es.onerror = onError;
    return es;
  },
  getSettings(): Promise<DashboardSettings> { return peacockFetch('/v1/dashboard/settings'); },
  toggleSetting(key: 'tunnel' | 'stealth' | 'success_logs' | 'fail_logs') {
    return peacockFetch<{ status: string; key: string; new_state: boolean }>(`/v1/dashboard/settings/toggle/${key}`, { method: 'POST' });
  },
  setPerformanceMode(mode: 'stealth' | 'balanced' | 'apex') {
    return peacockFetch<{ status: string; active_key: string }>(`/v1/dashboard/settings/performance/${mode}`, { method: 'POST' });
  },
  getHistory(limit = 50, gateway?: string): Promise<HistoryEntry[]> {
    const qs = new URLSearchParams({ limit: String(limit) });
    if (gateway) qs.append('gateway', gateway);
    return peacockFetch(`/v1/dashboard/history?${qs}`);
  },
};

// ─── NEURAL LINK ───
export interface ConversationItem {
  id: string;
  title: string;
  model: string;
  message_count: number;
  updated_at: number;
  preview: string;
}

export interface UploadedFile {
  file_id: string;
  filename: string;
  path: string;
  size: number;
}

export interface SessionContextResponse {
  tokens: number;
  cost: number;
  active_streams: number;
  model: string;
  gateway: string;
}

export const NeuralLinkAPI = {
  getSessionContext(model: string, messages: { role: string; content: string }[], active_streams = 0): Promise<SessionContextResponse> {
    return peacockFetch('/v1/neural-link/session', { method: 'POST', body: JSON.stringify({ model, messages, active_streams }) });
  },
  listConversations(limit = 20, offset = 0): Promise<ConversationItem[]> {
    return peacockFetch(`/v1/webui/chat/conversations?limit=${limit}&offset=${offset}`);
  },
  createConversation(model: string, title?: string) {
    const qs = new URLSearchParams({ model });
    if (title) qs.append('title', title);
    return peacockFetch<{ conversation_id: string; model: string }>(`/v1/webui/chat/conversations?${qs}`, { method: 'POST' });
  },
  streamChat(request: { message: string; conversation_id?: string; model?: string; files?: string[]; temperature: number; max_tokens?: number }, onEvent: (event: unknown) => void, onError?: (e: any) => void) {
    fetch(`${API_BASE}/v1/webui/chat/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...request, stream: true }),
    }).then(async (res) => {
      if (!res.ok || !res.body) throw new Error('Stream request failed');
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          const m = line.match(/^data: (.+)$/m);
          if (m) { try { onEvent(JSON.parse(m[1])); } catch {} }
        }
      }
    }).catch((err) => { if (onError) onError(err); else console.error(err); });
  },
  uploadFile(file: File): Promise<UploadedFile> {
    const form = new FormData();
    form.append('file', file);
    return fetch(`${API_BASE}/v1/webui/chat/upload`, { method: 'POST', body: form }).then(r => { if (!r.ok) throw new Error('Upload failed'); return r.json(); });
  },
  getChatModels(): Promise<Record<string, any[]>> { return peacockFetch('/v1/chat/models'); },
};

// ─── MODEL REGISTRY ───
export interface ModelDetail {
  id: string;
  gateway: string;
  tier: string;
  status: string;
  note: string;
  rpm?: number;
  tpm?: number;
  rpd?: number;
  context_window?: number;
  input_price_1m: number;
  output_price_1m: number;
}

export interface ModelRegistryResponse {
  models: ModelDetail[];
  by_gateway: Record<string, ModelDetail[]>;
  frozen_count: number;
  active_count: number;
}

export interface RegisterModelRequest {
  id: string;
  gateway: 'groq' | 'google' | 'deepseek' | 'mistral';
  tier: 'free' | 'cheap' | 'expensive';
  note?: string;
  rpm?: number;
  rpd?: number;
  tpm?: number;
  context_window?: number;
  input_price_1m?: number;
  output_price_1m?: number;
}

export const ModelRegistryAPI = {
  getRegistry(): Promise<ModelRegistryResponse> { return peacockFetch('/v1/webui/models/registry'); },
  testModel(model_id: string) { return peacockFetch<{ model_id: string; working: boolean; latency_ms: number; error?: string; tokens_used: number }>(`/v1/webui/models/${encodeURIComponent(model_id)}/test`, { method: 'POST' }); },
  freezeModel(model_id: string, reason = 'manual') { return peacockFetch(`/v1/webui/models/${encodeURIComponent(model_id)}/freeze`, { method: 'POST', body: JSON.stringify({ reason }) }); },
  unfreezeModel(model_id: string) { return peacockFetch(`/v1/webui/models/${encodeURIComponent(model_id)}/unfreeze`, { method: 'POST' }); },
  registerModel(req: RegisterModelRequest) { return peacockFetch<{ status: string; model: string }>('/v1/models/register', { method: 'POST', body: JSON.stringify(req) }); },
};

// ─── KEY VAULT ───
export interface GatewayKeys {
  gateway: string;
  status: string;
  keys: any[];
  key_count: number;
  healthy_count: number;
}

export interface KeyTelemetry {
  total_keys: number;
  healthy_keys: number;
  exhausted_keys: number;
  dead_keys: number;
  global_token_quota: Record<string, number>;
  gateway_redundancy: Record<string, number>;
  estimated_daily_cost: number;
  error_rate: number;
}

export const KeyVaultAPI = {
  getKeys(): Promise<GatewayKeys[]> { return peacockFetch('/v1/webui/keys/'); },
  getTelemetry(): Promise<KeyTelemetry> { return peacockFetch('/v1/webui/keys/telemetry'); },
  testKey(gateway: string, label: string) { return peacockFetch(`/v1/webui/keys/${gateway}/${label}/test`, { method: 'POST' }); },
  toggleKey(gateway: string, label: string) { return peacockFetch<{ message: string }>(`/v1/webui/keys/${gateway}/${label}/toggle`, { method: 'POST' }); },
  deleteKey(gateway: string, label: string) { return peacockFetch<{ message: string }>(`/v1/webui/keys/${gateway}/${label}`, { method: 'DELETE' }); },
  addKey(gateway: string, label: string, key: string) { return peacockFetch('/v1/webui/keys/add', { method: 'POST', body: JSON.stringify({ gateway, label, key }) }); },
};

// ─── STRIKER ───
export interface StrikerFile {
  name: string;
  path: string;
  size: number;
  status: string;
  signalIntensity: number;
}

export interface StrikerTelemetry {
  currentFile?: string;
  processedCount: number;
  totalCount: number;
  isPaused: boolean;
  isRunning: boolean;
  proxyIP: string;
  logs: string[];
  totalPromptTokens: number;
  totalCompletionTokens: number;
  totalTokens: number;
  rpm: number;
  tpm: number;
  rpd: number;
}

export const StrikerAPI = {
  getFiles(base_dir = '/home/flintx/chat_logs'): Promise<StrikerFile[]> { return peacockFetch(`/v1/striker/files?base_dir=${encodeURIComponent(base_dir)}`); },
  getStatus(): Promise<StrikerTelemetry> { return peacockFetch('/v1/striker/status'); },
  execute(req: { files: string[]; prompt: string; modelId: string; delay: number; throttle: number }) { return peacockFetch('/v1/striker/execute', { method: 'POST', body: JSON.stringify(req) }); },
  pause() { return peacockFetch('/v1/striker/pause', { method: 'POST' }); },
  resume() { return peacockFetch('/v1/striker/resume', { method: 'POST' }); },
  abort() { return peacockFetch('/v1/striker/abort', { method: 'POST' }); },
};

// ─── LIVE WIRE ───
export const LiveWireAPI = {
  initiateMission(req: { name: string; prompt_path: string; file_paths: string[]; model_id: string; settings: { temperature: number; max_tokens: number; output_format: string } }) {
    return peacockFetch<{ status: string; batch_id: string; items: number }>('/v1/payloads/strike', { method: 'POST', body: JSON.stringify(req) });
  },
  streamMission(batch_id: string, onEvent: (event: unknown) => void, onError?: (e: Event) => void): EventSource {
    const es = createSSE(`/v1/payloads/stream/${batch_id}`);
    es.onmessage = (ev) => { try { onEvent(JSON.parse(ev.data)); } catch {} };
    if (onError) es.onerror = onError;
    return es;
  },
};

// ─── WEBSOCKET ───
export const PeacockWS = {
  connect(model = 'llama-3.3-70b-versatile', temp = 0.7): WebSocket {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host === 'localhost:3099' ? 'localhost:3099' : window.location.host;
    const ws = new WebSocket(`${protocol}//${host}/v1/chat/ws/ws`);
    ws.onopen = () => { ws.send(JSON.stringify({ type: 'config', model, temp, files: [] })); };
    return ws;
  },
};

// ─── LEGACY COMPAT ───
export const PeacockAPI = {
  ...DashboardAPI,
  ...NeuralLinkAPI,
  ...ModelRegistryAPI,
  ...KeyVaultAPI,
  ...StrikerAPI,
  ...LiveWireAPI,
  getModels: NeuralLinkAPI.getChatModels,
  getAmmo: () => peacockFetch<string[]>('/v1/fs/ammo'),
  getAmmoContent: (fileName: string) => peacockFetch<{ content: string }>(`/v1/fs/ammo/${fileName}`).then(r => r.content || ''),
  saveAmmo: (fileName: string, content: string) => peacockFetch('/v1/fs/prompts/ammo', { method: 'POST', body: JSON.stringify({ name: fileName.replace(/\.[^/.]+$/, ''), content }) }).then(() => true).catch(() => false),
  getMolds: () => peacockFetch<any[]>('/v1/refinery/molds'),
  browseLegos: (path?: string) => peacockFetch(path ? `/v1/refinery/browse?path=${encodeURIComponent(path)}` : '/v1/refinery/browse'),
  getRefineryFile: (path: string) => peacockFetch<{ content: string }>(`/v1/refinery/file?path=${encodeURIComponent(path)}`).then(r => r.content || ''),
  processStrike: (moldPath: string, legoPaths: string[], modelId: string) => peacockFetch('/v1/refinery/process', { method: 'POST', body: JSON.stringify({ mold_path: moldPath, lego_paths: legoPaths, model_id: modelId }) }),
  startMission: (name: string, promptPath: string, filePaths: string[], modelId: string, settings: any) => peacockFetch('/v1/payloads/strike', { method: 'POST', body: JSON.stringify({ name, prompt_path: promptPath, file_paths: filePaths, model_id: modelId, settings }) }),
  onboardApp: (data: { name: string; description: string; model_pack: string }) => peacockFetch('/v1/onboarding/onboard', { method: 'POST', body: JSON.stringify(data) }),
};

export function useLiveWire(activeMission: string | null) {
  const [stats, setStats] = React.useState({ rpm: 0, tps: 0, tokens: 0, cost: 0, success_rate: '0%' });
  const [batchItems, setBatchItems] = React.useState<any[]>([]);
  const [connected, setConnected] = React.useState(false);

  React.useEffect(() => {
    const eventSource = new EventSource(`${API_BASE}/v1/telemetry/stream`);
    eventSource.onopen = () => setConnected(true);
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'telemetry') {
          setStats({ rpm: data.rpm, tps: data.tps, tokens: data.tokens || 0, cost: data.cost || 0, success_rate: data.success_rate || '0%' });
        }
      } catch {}
    };
    eventSource.onerror = () => setConnected(false);
    return () => eventSource.close();
  }, []);

  return { stats, batchItems, connected };
}

// ─── PLANS ───
export interface PlanListItem {
  plan_id: string;
  file_path: string;
  model_id: string;
  total_chunks: number;
  completed_chunks: number;
  overridden_chunks: number;
  status: string;
  estimated_total_seconds: number;
  makespan_seconds: number;
  created_at: number;
  completed_at: number | null;
}

export interface PlanDetail extends PlanListItem {
  total_tokens: number;
  config: Record<string, unknown>;
  rules: Array<Record<string, unknown>>;
  chunks: Array<{
    chunk_id: number;
    token_count: number;
    model_id: string;
    key_label: string;
    route: 'direct' | 'proxy';
    estimated_seconds: number;
    wait_seconds: number;
    status: string;
    manual_override: 'direct' | 'proxy' | null;
    rationale: string;
  }>;
}

export interface ChunkSummary {
  plan_id: string;
  plan_status: string;
  total_chunks: number;
  chunks: Array<{
    chunk_id: number;
    route: 'direct' | 'proxy';
    original_route: 'direct' | 'proxy';
    manual_override: 'direct' | 'proxy' | null;
    status: string;
    token_count: number;
    key_label: string;
    estimated_seconds: number;
    wait_seconds: number;
    completed_at: number | null;
    error: string | null;
  }>;
}

// ─── PAYLOADS ───
export interface PayloadFileItem {
  name: string;
  size: number;
  modified: number;
}

export const PayloadsAPI = {
  list(): Promise<PayloadFileItem[]> {
    return peacockFetch('/v1/payloads');
  },
  upload(file: File): Promise<{ status: string; name: string; path: string; size: number }> {
    const form = new FormData();
    form.append('file', file);
    return fetch(`${API_BASE}/v1/payloads/upload`, { method: 'POST', body: form }).then(r => {
      if (!r.ok) throw new Error('Upload failed');
      return r.json();
    });
  },
  delete(filename: string): Promise<{ status: string; name: string }> {
    return peacockFetch(`/v1/payloads/${encodeURIComponent(filename)}`, { method: 'DELETE' });
  },
};

export const PlansAPI = {
  listPlans(status?: string, model_id?: string, limit = 100, offset = 0): Promise<PlanListItem[]> {
    const qs = new URLSearchParams();
    if (status) qs.set('status', status);
    if (model_id) qs.set('model_id', model_id);
    qs.set('limit', String(limit));
    qs.set('offset', String(offset));
    return peacockFetch<PlanListItem[]>(`/v1/plans?${qs.toString()}`);
  },
  countPlans(status?: string, model_id?: string): Promise<{ total: number }> {
    const qs = new URLSearchParams();
    if (status) qs.set('status', status);
    if (model_id) qs.set('model_id', model_id);
    return peacockFetch<{ total: number }>(`/v1/plans/count?${qs.toString()}`);
  },
  createPlan(file_path: string, model_id?: string, system_prompt?: string): Promise<PlanDetail> {
    return peacockFetch<PlanDetail>('/v1/plans', {
      method: 'POST',
      body: JSON.stringify({ file_path, model_id, system_prompt }),
    });
  },
  getPlan(plan_id: string): Promise<PlanDetail> {
    return peacockFetch<PlanDetail>(`/v1/plans/${plan_id}`);
  },
  getChunkSummary(plan_id: string): Promise<ChunkSummary> {
    return peacockFetch<ChunkSummary>(`/v1/plans/${plan_id}/chunks`);
  },
  updatePlanStatus(plan_id: string, status: string): Promise<PlanDetail> {
    return peacockFetch<PlanDetail>(`/v1/plans/${plan_id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  },
  updateChunkStatus(plan_id: string, chunk_id: number, status: string, error?: string | null): Promise<PlanDetail> {
    return peacockFetch<PlanDetail>(`/v1/plans/${plan_id}/chunks/${chunk_id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status, error }),
    });
  },
  setChunkOverride(plan_id: string, chunk_id: number, route: 'direct' | 'proxy'): Promise<PlanDetail> {
    return peacockFetch<PlanDetail>(`/v1/plans/${plan_id}/chunks/${chunk_id}/route`, {
      method: 'PATCH',
      body: JSON.stringify({ route }),
    });
  },
  clearChunkOverride(plan_id: string, chunk_id: number): Promise<PlanDetail> {
    return peacockFetch<PlanDetail>(`/v1/plans/${plan_id}/chunks/${chunk_id}/route`, { method: 'DELETE' });
  },
  deletePlan(plan_id: string): Promise<{ status: string; plan_id: string }> {
    return peacockFetch<{ status: string; plan_id: string }>(`/v1/plans/${plan_id}`, { method: 'DELETE' });
  },
  executePlan(plan_id: string, opts: { system_prompt?: string; temperature?: number; max_tokens?: number; top_p?: number; abort_on_fail?: boolean } = {}): Promise<{
    plan_id: string;
    status: string;
    total_tokens: number;
    total_cost: number;
    duration_ms: number;
    chunks: Array<{
      chunk_id: number;
      status: string;
      route: string;
      key_used: string;
      usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
      cost: number;
      duration_ms: number;
      error: string | null;
    }>;
  }> {
    return peacockFetch(`/v1/plans/${plan_id}/execute`, {
      method: 'POST',
      body: JSON.stringify(opts),
    });
  },
  queuePlan(plan_id: string): Promise<{ status: string; plan_id: string; position: number }> {
    return peacockFetch(`/v1/plans/${plan_id}/queue`, { method: 'POST' });
  },
  unqueuePlan(plan_id: string): Promise<{ status: string; plan_id: string }> {
    return peacockFetch(`/v1/plans/${plan_id}/queue`, { method: 'DELETE' });
  },
  getQueueSnapshot(): Promise<{
    state: string;
    length: number;
    current_plan_id: string | null;
    completed_count: number;
    failed_count: number;
    items: Array<{ plan_id: string; position: number }>;
  }> {
    return peacockFetch('/v1/plans/queue/snapshot');
  },
  startQueue(opts: { system_prompt?: string; temperature?: number; max_tokens?: number; top_p?: number } = {}): Promise<{ status: string }> {
    return peacockFetch('/v1/plans/queue/start', { method: 'POST', body: JSON.stringify(opts) });
  },
  stopQueue(): Promise<{ status: string }> {
    return peacockFetch('/v1/plans/queue/stop', { method: 'POST' });
  },
  clearQueue(): Promise<{ status: string; removed: number }> {
    return peacockFetch('/v1/plans/queue/all', { method: 'DELETE' });
  },
  getRecentExecutions(limit = 20): Promise<RecentExecution[]> {
    return peacockFetch(`/v1/plans/recent?limit=${limit}`);
  },
};

export interface RecentExecution {
  plan_id: string;
  file_path: string;
  model_id: string;
  total_chunks: number;
  executed_at: number;
  status: string;
  total_tokens: number;
  total_cost: number;
  duration_ms: number;
  proxy_chunks: number;
  direct_chunks: number;
}

// ─── CONFIG ───
export interface ProxyRulesConfig {
  tpm_threshold_pct: number;
  rpm_threshold_pct: number;
  chunk_size_threshold: number;
  recent_429_min_consecutive: number;
  status_rule_enabled: boolean;
}

export interface GuardConfig {
  warn_threshold: number;
  block_threshold: number;
}

export interface PacerConfig {
  burn_mode: 'CONSERVATIVE' | 'BALANCED' | 'ULTRA';
  tpm_backpressure_pct: number;
  default_concurrency: number;
}

export interface CleanupConfig {
  plan_retention_days: number;
  stress_retention_days: number;
  history_retention_days: number;
  interval_hours: number;
}

export interface RuntimeConfig {
  proxy_rules: ProxyRulesConfig;
  guard: GuardConfig;
  pacer: PacerConfig;
  cleanup: CleanupConfig;
}

export const ConfigAPI = {
  getConfig(): Promise<RuntimeConfig> { return peacockFetch('/v1/config'); },
  patchConfig(patch: Partial<RuntimeConfig>): Promise<{ status: string; applied: Partial<RuntimeConfig> }> {
    return peacockFetch('/v1/config', { method: 'PATCH', body: JSON.stringify(patch) });
  },
  resetConfig(): Promise<RuntimeConfig> { return peacockFetch('/v1/config/reset', { method: 'POST' }); },
};

export interface StorageStats {
  plans: { count: number; bytes: number; oldest_mtime: number | null };
  stress: { count: number; bytes: number; oldest_mtime: number | null };
  history: { count: number; bytes: number; oldest_mtime: number | null };
  total_bytes: number;
}

export interface CleanupSummary {
  status: string;
  plans_deleted: number;
  stress_deleted: number;
  history_deleted: number;
  bytes_freed: number;
}

export interface SystemStatus {
  status: string;
  queue: {
    state: string;
    depth: number;
    current_plan_id: string | null;
    completed_today: number;
    failed_today: number;
  };
  failure_rate_24h: number;
  storage: {
    plans: number;
    history: number;
    stress: number;
    total_mb: number;
  };
  storage_status: 'ok' | 'warning' | 'critical';
  keys: {
    groq: number;
    google: number;
    deepseek: number;
    mistral: number;
  };
}

export const AdminAPI = {
  getStorage(): Promise<StorageStats> { return peacockFetch('/v1/admin/storage'); },
  runCleanup(): Promise<CleanupSummary> { return peacockFetch('/v1/admin/cleanup', { method: 'POST' }); },
  getSystemStatus(): Promise<SystemStatus> { return peacockFetch('/v1/admin/system'); },
};

// ─── HISTORY ───
export interface HistoryChunkItem {
  chunk_id: number;
  status: string;
  route: string | null;
  key_used: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost: number;
  duration_ms: number;
  error: string | null;
}

export interface HistoryRunItem {
  run_id: string;
  plan_id: string;
  file_path: string;
  model_id: string;
  status: string;
  total_tokens: number;
  total_cost: number;
  duration_ms: number;
  proxy_chunks: number;
  direct_chunks: number;
  failed_chunks: number;
  skipped_chunks: number;
  executed_at: number;
  error_summary: string | null;
}

export interface HistoryStats {
  period_days: number;
  total_runs: number;
  completed_runs: number;
  failed_runs: number;
  failure_rate: number;
  total_tokens: number;
  total_cost: number;
  proxy_chunks: number;
  direct_chunks: number;
  proxy_pct: number;
  failed_chunks: number;
}

// ─── STRESS ───
export interface StressStartRequest {
  file_paths: string[];
  model_id?: string;
  concurrency?: number;
  system_prompt?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface StressLiveStatus {
  run_id: string;
  state: string;
  total_plans: number;
  completed_plans: number;
  failed_plans: number;
  total_chunks: number;
  completed_chunks: number;
  failed_chunks: number;
  total_tokens: number;
  total_cost: number;
  elapsed_ms: number;
  current_file: string;
}

export interface StressReport {
  run_id: string;
  config: Record<string, any>;
  status: string;
  total_plans: number;
  completed_plans: number;
  failed_plans: number;
  total_chunks: number;
  completed_chunks: number;
  failed_chunks: number;
  skipped_chunks: number;
  total_tokens: number;
  total_cost: number;
  duration_ms: number;
  per_key_stats: Record<string, any>;
  wait_distribution: Record<string, any>;
  proxy_effectiveness: Record<string, any>;
  bottlenecks: string[];
  suggestions: string[];
  created_at: number;
}

export interface StressListItem {
  run_id: string;
  status: string;
  total_plans: number;
  completed_plans: number;
  failed_plans: number;
  total_tokens: number;
  duration_ms: number;
  created_at: number;
}

export interface StressCompareItem {
  run_id: string;
  status: string;
  total_plans: number;
  completed_plans: number;
  failed_plans: number;
  total_chunks: number;
  completed_chunks: number;
  failed_chunks: number;
  skipped_chunks: number;
  total_tokens: number;
  total_cost: number;
  duration_ms: number;
  proxy_pct: number;
  created_at: number;
}

export interface StressCompareResponse {
  runs: StressCompareItem[];
}

export interface HistoryCompareItem {
  run_id: string;
  plan_id: string;
  file_path: string;
  model_id: string;
  status: string;
  total_tokens: number;
  total_cost: number;
  duration_ms: number;
  proxy_chunks: number;
  direct_chunks: number;
  failed_chunks: number;
  skipped_chunks: number;
  proxy_pct: number;
  executed_at: number;
  error_summary: string | null;
}

export interface HistoryCompareResponse {
  runs: HistoryCompareItem[];
}

export const StressAPI = {
  start(req: StressStartRequest): Promise<{ run_id: string; status: string; total_plans: number }> {
    return peacockFetch('/v1/stress/start', { method: 'POST', body: JSON.stringify(req) });
  },
  getStatus(run_id: string): Promise<StressLiveStatus> {
    return peacockFetch(`/v1/stress/status/${run_id}`);
  },
  abort(run_id: string): Promise<{ status: string; run_id: string }> {
    return peacockFetch(`/v1/stress/abort/${run_id}`, { method: 'POST' });
  },
  getReport(run_id: string): Promise<StressReport> {
    return peacockFetch(`/v1/stress/report/${run_id}`);
  },
  listRuns(limit = 50, offset = 0, status?: string): Promise<StressListItem[]> {
    const qs = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (status) qs.set('status', status);
    return peacockFetch(`/v1/stress/list?${qs.toString()}`);
  },
  countRuns(status?: string): Promise<{ total: number }> {
    const qs = new URLSearchParams();
    if (status) qs.set('status', status);
    return peacockFetch<{ total: number }>(`/v1/stress/count?${qs.toString()}`);
  },
  compare(run_ids: string[]): Promise<StressCompareResponse> {
    return peacockFetch('/v1/stress/compare', { method: 'POST', body: JSON.stringify({ run_ids }) });
  },
};

export const HistoryAPI = {
  listRuns(limit = 50, offset = 0, plan_id?: string, status?: string, model_id?: string): Promise<HistoryRunItem[]> {
    const qs = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (plan_id) qs.set('plan_id', plan_id);
    if (status) qs.set('status', status);
    if (model_id) qs.set('model_id', model_id);
    return peacockFetch(`/v1/history?${qs.toString()}`);
  },
  countRuns(plan_id?: string, status?: string, model_id?: string): Promise<{ total: number }> {
    const qs = new URLSearchParams();
    if (plan_id) qs.set('plan_id', plan_id);
    if (status) qs.set('status', status);
    if (model_id) qs.set('model_id', model_id);
    return peacockFetch<{ total: number }>(`/v1/history/count?${qs.toString()}`);
  },
  getRun(run_id: string): Promise<HistoryRunItem & { chunks: HistoryChunkItem[] }> {
    return peacockFetch(`/v1/history/${run_id}`);
  },
  getStats(days = 7): Promise<HistoryStats> {
    return peacockFetch(`/v1/history/stats?days=${days}`);
  },
  compare(run_ids: string[]): Promise<HistoryCompareResponse> {
    return peacockFetch('/v1/history/compare', { method: 'POST', body: JSON.stringify({ run_ids }) });
  },
};

export class PeacockWSClass {
  private ws: WebSocket | null = null;
  private onChunk: (content: string) => void;
  private onError: (error: string) => void;
  private onComplete: (fullResponse: string, usage: any) => void;
  private buffer: string = '';

  constructor(onChunk: (c: string) => void, onError: (e: string) => void, onComplete: (c: string, u: any) => void) {
    this.onChunk = onChunk;
    this.onError = onError;
    this.onComplete = onComplete;
  }

  connect(modelId: string, options: any = {}) {
    return new Promise<void>((resolve, reject) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'config', model: modelId, temp: options.temp || 0.7, top_p: options.top_p || 1.0, max_tokens: options.max_tokens || 2048, system: options.system || '' }));
        resolve();
      } else {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsHost = window.location.host === 'localhost:3099' ? 'localhost:3099' : window.location.host;
        this.ws = new WebSocket(`${wsProtocol}//${wsHost}/v1/chat/ws/ws`);
        this.ws.onopen = () => {
          this.ws?.send(JSON.stringify({ type: 'config', model: modelId, temp: options.temp || 0.7, top_p: options.top_p || 1.0, max_tokens: options.max_tokens || 2048, system: options.system || '' }));
          resolve();
        };
        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'content') { this.buffer += data.content || ''; this.onChunk(this.buffer); }
            else if (data.type === 'metadata') { this.onComplete(this.buffer, data.usage); }
            else if (data.type === 'error') { this.onError(data.content); }
          } catch {}
        };
        this.ws.onerror = () => { this.onError('NEURAL_LINK_FAILURE: Connection lost'); reject(); };
      }
    });
  }

  sendPrompt(prompt: string) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) { this.onError('SOCKET_CLOSED: Cannot send prompt'); return; }
    this.buffer = '';
    this.ws.send(JSON.stringify({ type: 'prompt', content: prompt }));
  }

  disconnect() { if (this.ws) { this.ws.close(); this.ws = null; } }
}

export default PeacockAPI;
