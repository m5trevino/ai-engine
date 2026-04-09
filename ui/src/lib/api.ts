/**
 * Peacock Engine V3 - Frontend API Client
 * Manages REST configuration and WebSocket bidirectional streaming
 */

const isProd = typeof window !== 'undefined' && window.location.hostname !== 'localhost';
const API_BASE = isProd ? "" : "http://localhost:3099";

export interface ModelConfig {
  id: string;
  tier: string;
  note: string;
  rpm: number;
  tpm: number;
  rpd: number;
}

export interface KeyTelemetry {
  account: string;
  gateway: string;
  total_requests: number;
  total_tokens: number;
  success_rate: number;
  last_used: string;
}

/**
 * REST Client for system configuration and telemetry
 */
export const PeacockAPI = {
  /** Fetch all available models grouped by gateway */
  async getModels(): Promise<Record<string, ModelConfig[]>> {
    try {
      const res = await fetch(`${API_BASE}/v1/chat/models`);
      if (!res.ok) throw new Error("Failed to fetch models");
      return await res.json();
    } catch (e) {
      console.error("[PeacockAPI] Model Fetch Error:", e);
      return {};
    }
  },

  /** Fetch key usage telemetry */
  async getKeyUsage(): Promise<KeyTelemetry[]> {
    try {
      const res = await fetch(`${API_BASE}/v1/keys/usage`);
      if (!res.ok) throw new Error("Failed to fetch key telemetry");
      
      const data = await res.json();
      // Transform backend dict format to array for UI
      return Object.entries(data).map(([account, stats]: [string, any]) => ({
        account,
        gateway: account.includes("GROQ") ? "groq" : account.includes("PEACOCK") ? "google" : "unknown",
        total_requests: stats.requests || 0,
        total_tokens: stats.total_tokens || 0,
        success_rate: stats.requests ? Math.round((stats.successes / stats.requests) * 100) : 100,
        last_used: stats.last_used || new Date().toISOString()
      }));
    } catch (e) {
      console.error("[PeacockAPI] Key Telemetry Fetch Error:", e);
      return [];
    }
  }
};

/**
 * WebSocket handler for bidirectional OpenClaw-compatible streaming
 */
export class PeacockWS {
  private ws: WebSocket | null = null;
  private onChunk: (content: string) => void;
  private onError: (error: string) => void;
  private onComplete: (fullResponse: string, usage: any) => void;
  private buffer: string = "";

  constructor(
    onChunk: (c: string) => void,
    onError: (e: string) => void,
    onComplete: (c: string, u: any) => void
  ) {
    this.onChunk = onChunk;
    this.onError = onError;
    this.onComplete = onComplete;
  }

  connect(model: string, temp: number = 0.7, files: string[] = []) {
    return new Promise<void>((resolve, reject) => {
      // Corrected WebSocket path: v1/chat/ws is the prefix, /ws is the endpoint
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsHost = isProd ? window.location.host : 'localhost:3099';
      this.ws = new WebSocket(`${wsProtocol}//${wsHost}/v1/chat/ws/ws`);

      this.ws.onopen = () => {
        // Send initial config upon connection
        this.ws?.send(JSON.stringify({
          type: "config",
          model,
          temp,
          files
        }));
        resolve();
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === "info") {
            console.log("[PeacockWS]", data.content);
          } else if (data.type === "content") {
            this.buffer += data.content || "";
            this.onChunk(this.buffer);
          } else if (data.type === "metadata") {
            // Stream complete, usage data arrived
            this.onComplete(this.buffer, data.usage);
          } else if (data.type === "error") {
            this.onError(data.content);
          }
        } catch (e) {
          console.error("Failed to parse websocket message", event.data);
        }
      };

      this.ws.onerror = (e) => {
        console.error("[PeacockWS] Connection Error");
        this.onError("NEURAL_LINK_FAILURE: Connection lost");
        reject(e);
      };

      this.ws.onclose = () => {
        console.log("[PeacockWS] Disconnected");
      };
    });
  }

  sendPrompt(prompt: string) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.onError("SOCKET_CLOSED: Cannot send prompt");
      return;
    }
    
    // Clear buffer for new prompt
    this.buffer = "";
    this.ws.send(JSON.stringify({
      type: "prompt",
      content: prompt
    }));
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
