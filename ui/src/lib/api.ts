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
