/**
 * Peacock Engine TUI Core — API helpers
 */

export const API_BASE = "http://localhost:3099";

export interface ProviderState {
  enabled: boolean;
  visible: boolean;
  label: string;
}

export interface ModelInfo {
  id: string;
  gateway: string;
  tier: string;
  status: "active" | "frozen" | "deprecated";
  note: string;
  rpm: number | null;
  tpm: number | null;
  rpd: number | null;
  context_window: number | null;
  input_price_1m: number;
  output_price_1m: number;
  tools_supported: boolean;
  index: number;
  base_url: string | null;
  display_name: string;
}

export interface ModelsData {
  models: ModelInfo[];
  by_gateway: Record<string, ModelInfo[]>;
  count: number;
  providers: Record<string, ProviderState>;
}

export async function fetchModels(): Promise<ModelsData> {
  const res = await fetch(`${API_BASE}/v1/models`);
  if (!res.ok) throw new Error(`models fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchProviders(): Promise<Record<string, ProviderState>> {
  const res = await fetch(`${API_BASE}/v1/config/providers`);
  if (!res.ok) throw new Error(`providers fetch failed: ${res.status}`);
  return res.json();
}

export async function toggleProvider(gateway: string): Promise<ProviderState> {
  const res = await fetch(`${API_BASE}/v1/config/providers/${encodeURIComponent(gateway)}/toggle`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`provider toggle failed: ${res.status}`);
  return res.json();
}

export async function fetchEndpoints(): Promise<any> {
  const res = await fetch(`${API_BASE}/v1/docs/endpoints`);
  if (!res.ok) throw new Error(`docs endpoints fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchIntegrationGuide(): Promise<any> {
  const res = await fetch(`${API_BASE}/v1/docs/integration-guide`);
  if (!res.ok) throw new Error(`docs guide fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchHistory(limit = 20): Promise<any> {
  const res = await fetch(`${API_BASE}/v1/history?limit=${limit}`);
  if (!res.ok) throw new Error(`history fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchStrikerStatus(): Promise<any> {
  const res = await fetch(`${API_BASE}/v1/striker/status`);
  if (!res.ok) throw new Error(`striker status fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchEngineLogs(lines = 50): Promise<{ lines: string[]; total_lines: number }> {
  const res = await fetch(`${API_BASE}/v1/admin/logs?lines=${lines}`);
  if (!res.ok) throw new Error(`engine logs fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchDirectory(path: string): Promise<{ name: string; type: "file" | "directory" }[]> {
  const res = await fetch(`${API_BASE}/v1/fs/browse?path=${encodeURIComponent(path)}`);
  if (!res.ok) throw new Error(`fs browse failed: ${res.status}`);
  const data = await res.json();
  return (data.items ?? []).map((e: any) => ({ name: e.name, type: e.type }));
}

export async function fetchFile(path: string): Promise<string> {
  const res = await fetch(`${API_BASE}/v1/striker/target/${encodeURIComponent(path)}`);
  if (!res.ok) {
    // Fallback: read plain text via dashboard vault if not a target file
    const fallback = await fetch(`${API_BASE}/v1/dashboard/vault/${encodeURIComponent(path)}`);
    if (!fallback.ok) throw new Error(`file read failed: ${res.status}`);
    const data = await fallback.json();
    return data.content ?? "";
  }
  return res.json().then(d => typeof d === "string" ? d : JSON.stringify(d, null, 2));
}
