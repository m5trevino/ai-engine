/**
 * Peacock Engine - Sequence Orchestrator
 * Manages high-stakes tactical strikes in both Batch and Ultra modes.
 */

import { PeacockAPI, PeacockWS } from './api';

export interface StrikeSlot {
  id: number;
  modelId: string;
  delay: number;
  status: 'IDLE' | 'ACTIVE' | 'DONE' | 'ERROR';
  result?: string;
}

export interface PayloadAsset {
  fileName: string;
  content: string;
  customPrompt?: string | null;
}

export type StrikeMode = 'BATCH' | 'ULTRA';

export class SequenceOrchestrator {
  private slots: StrikeSlot[];
  private onUpdate: (slots: StrikeSlot[]) => void;
  private onTotalUsage: (usage: any) => void;
  private isRunning: boolean = false;
  private threads: number;
  private mode: StrikeMode;
  private systemPrompt: string;
  private globalPayloadPrompt: string;
  private payloadAssets: PayloadAsset[];
  private onTelemetry: (telemetry: { tps: number, rpm: number }) => void;
  
  private startTime: number = 0;
  private totalTokens: number = 0;
  private strikeCount: number = 0;

  constructor(
    slots: StrikeSlot[], 
    threads: number, 
    mode: StrikeMode,
    systemPrompt: string,
    globalPayloadPrompt: string,
    payloadAssets: PayloadAsset[],
    onUpdate: (slots: StrikeSlot[]) => void,
    onTotalUsage: (usage: any) => void,
    onTelemetry: (telemetry: { tps: number, rpm: number }) => void
  ) {
    this.slots = slots;
    this.threads = threads;
    this.mode = mode;
    this.systemPrompt = systemPrompt;
    this.globalPayloadPrompt = globalPayloadPrompt;
    this.payloadAssets = payloadAssets;
    this.onUpdate = onUpdate;
    this.onTotalUsage = onTotalUsage;
    this.onTelemetry = onTelemetry;
  }

  public stop() {
    this.isRunning = false;
  }

  public async execute() {
    if (this.isRunning) return;
    this.isRunning = true;
    
    // Prepare slots
    this.slots = this.slots.map(s => ({ ...s, status: 'IDLE', result: undefined }));
    this.onUpdate(this.slots);
    
    this.startTime = Date.now();
    this.totalTokens = 0;
    this.strikeCount = 0;

    if (this.mode === 'BATCH') {
      await this.runBatchMode();
    } else {
      await this.runUltraMode();
    }

    this.isRunning = false;
  }

  private async runBatchMode() {
    const manifest = [...this.slots];
    for (let i = 0; i < manifest.length; i += this.threads) {
      if (!this.isRunning) break;
      
      const batch = manifest.slice(i, i + this.threads);
      await Promise.all(batch.map(slot => this.fireStrike(slot)));
    }
  }

  private async runUltraMode() {
    const manifest = [...this.slots];
    let nextIndex = 0;
    const workers = [];

    const worker = async () => {
      while (nextIndex < manifest.length && this.isRunning) {
        const slotIndex = nextIndex++;
        const slot = manifest[slotIndex];
        await this.fireStrike(slot);
      }
    };

    for (let i = 0; i < Math.min(this.threads, manifest.length); i++) {
        workers.push(worker());
    }

    await Promise.all(workers);
  }

  private async fireStrike(slot: StrikeSlot) {
    if (!this.isRunning) return;

    // Update state to ACTIVE
    slot.status = 'ACTIVE';
    this.onUpdate([...this.slots]);

    if (slot.delay > 0) {
      await new Promise(r => setTimeout(r, slot.delay));
    }

    try {
      // Build final payload
      let finalPayloadContent = '';
      for (const asset of this.payloadAssets) {
         const instruction = asset.customPrompt && asset.customPrompt.trim() !== '' 
              ? asset.customPrompt 
              : this.globalPayloadPrompt;
         
         finalPayloadContent += `\n\n--- [ASSET: ${asset.fileName}] ---\n[INSTRUCTION]:\n${instruction}\n\n[CONTENT]:\n${asset.content}`;
      }

      const payload = `${this.systemPrompt}\n\n[PAYLOAD_BAY]${finalPayloadContent}`;
      
      // For sequential strikes, we'll use the REST API for easier tracking, 
      // but we could use WS if we wanted streaming per slot.
      // Given the dashboard "Gauge" aesthetic, REST is cleaner for batch results.
      const response = await fetch('/v1/strike', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          modelId: slot.modelId,
          prompt: payload,
          temp: 0.7
        })
      });

      if (!response.ok) throw new Error(`Strike ${slot.id} failed`);
      const data = await response.json();

      slot.status = 'DONE';
      slot.result = data.content;
      
      this.totalTokens += (data.usage?.total_tokens || 0);
      this.strikeCount++;
      
      // Calculate Telemetry
      const elapsed = (Date.now() - this.startTime) / 1000;
      this.onTelemetry({
        tps: Math.round(this.totalTokens / elapsed),
        rpm: Number((this.strikeCount * 60 / elapsed).toFixed(1))
      });

      this.onTotalUsage(data.usage);
    } catch (e) {
      console.error(`[Orchestrator] Slot ${slot.id} Error:`, e);
      slot.status = 'ERROR';
    } finally {
      this.onUpdate([...this.slots]);
    }
  }
}
