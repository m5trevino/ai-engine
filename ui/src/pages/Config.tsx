import React from 'react';
import { ConfigAPI, AdminAPI, RuntimeConfig } from '../lib/api';

const BURN_MODES: Array<{ key: 'CONSERVATIVE' | 'BALANCED' | 'ULTRA'; label: string; desc: string; color: string }> = [
  { key: 'CONSERVATIVE', label: 'CONSERVATIVE', desc: 'Low concurrency, early backpressure. Safest for shared keys.', color: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/15' },
  { key: 'BALANCED', label: 'BALANCED', desc: 'Default pacing. Good for most production workloads.', color: 'text-secondary border-secondary/30 bg-secondary/15' },
  { key: 'ULTRA', label: 'ULTRA', desc: 'Aggressive concurrency, late backpressure. Max throughput, higher risk.', color: 'text-error border-error/30 bg-error/15' },
];

const Config: React.FC = () => {
  const [config, setConfig] = React.useState<RuntimeConfig | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [toast, setToast] = React.useState<string | null>(null);
  const [dirty, setDirty] = React.useState(false);
  const [cleaning, setCleaning] = React.useState(false);

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(null), 3000); };

  const refresh = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await ConfigAPI.getConfig();
      setConfig(data);
      setDirty(false);
    } catch (e: any) {
      showToast(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  const updateField = (section: keyof RuntimeConfig, field: string, value: any) => {
    if (!config) return;
    setConfig((c) => {
      if (!c) return c;
      return { ...c, [section]: { ...c[section], [field]: value } };
    });
    setDirty(true);
  };

  const save = async () => {
    if (!config) return;
    setSaving(true);
    try {
      await ConfigAPI.patchConfig(config);
      setDirty(false);
      showToast('Config saved — takes effect on next request');
    } catch (e: any) {
      showToast(e.message);
    } finally {
      setSaving(false);
    }
  };

  const reset = async () => {
    if (!confirm('Reset all config to factory defaults?')) return;
    setSaving(true);
    try {
      const data = await ConfigAPI.resetConfig();
      setConfig(data);
      setDirty(false);
      showToast('Config reset to defaults');
    } catch (e: any) {
      showToast(e.message);
    } finally {
      setSaving(false);
    }
  };

  const runCleanup = async () => {
    if (!confirm('Run cleanup now? This will delete files older than their retention thresholds.')) return;
    setCleaning(true);
    try {
      const res = await AdminAPI.runCleanup();
      const total = res.plans_deleted + res.stress_deleted + res.history_deleted;
      showToast(`Cleanup done: ${total} items removed, ${(res.bytes_freed / 1024).toFixed(1)} KB freed`);
    } catch (e: any) {
      showToast(e.message);
    } finally {
      setCleaning(false);
    }
  };

  const SliderField = ({
    label,
    section,
    field,
    min,
    max,
    step,
    suffix,
  }: {
    label: string;
    section: keyof RuntimeConfig;
    field: string;
    min: number;
    max: number;
    step: number;
    suffix?: string;
  }) => {
    const val = (config as any)?.[section]?.[field] ?? 0;
    const pct = ((val - min) / (max - min)) * 100;
    return (
      <div className="flex flex-col gap-2">
        <div className="flex justify-between items-center">
          <span className="font-mono text-xs text-on-surface">{label}</span>
          <span className="font-mono text-xs text-secondary font-bold">
            {typeof val === 'number' && val < 1 && val > 0 ? `${(val * 100).toFixed(0)}%` : val}
            {suffix && val >= 1 ? suffix : ''}
          </span>
        </div>
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={val}
          onChange={(e) => updateField(section, field, parseFloat(e.target.value))}
          disabled={loading || saving}
          className="w-full h-1 bg-surface-container-high rounded-lg appearance-none cursor-pointer accent-primary"
          style={{ background: `linear-gradient(to right, #aac7ff ${pct}%, #363a3e ${pct}%)` }}
        />
      </div>
    );
  };

  const NumberField = ({
    label,
    section,
    field,
    min,
    max,
  }: {
    label: string;
    section: keyof RuntimeConfig;
    field: string;
    min: number;
    max: number;
  }) => {
    const val = (config as any)?.[section]?.[field] ?? 0;
    return (
      <div className="flex justify-between items-center">
        <span className="font-mono text-xs text-on-surface">{label}</span>
        <input
          type="number"
          min={min}
          max={max}
          value={val}
          onChange={(e) => updateField(section, field, parseInt(e.target.value) || 0)}
          disabled={loading || saving}
          className="w-24 bg-surface-container px-2 py-1 text-xs font-mono text-on-surface outline-none border border-outline-variant/20 focus:border-primary text-right"
        />
      </div>
    );
  };

  const ToggleField = ({
    label,
    section,
    field,
  }: {
    label: string;
    section: keyof RuntimeConfig;
    field: string;
  }) => {
    const val = (config as any)?.[section]?.[field] ?? false;
    return (
      <div className="flex justify-between items-center cursor-pointer" onClick={() => updateField(section, field, !val)}>
        <span className="font-mono text-xs text-on-surface">{label}</span>
        <div className={`w-10 h-5 flex items-center px-1 transition-colors ${val ? 'bg-secondary' : 'bg-outline-variant'}`}>
          <div className={`w-3 h-3 bg-background transition-all ${val ? '' : 'ml-auto'}`} />
        </div>
      </div>
    );
  };

  return (
    <main className="pt-4 pb-8 h-[calc(100vh-32px)] flex flex-col p-4 gap-4 overflow-hidden">
      {/* Header */}
      <section className="bg-surface-container-low p-4 flex flex-col md:flex-row gap-3 items-stretch md:items-center">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-primary">tune</span>
          <span className="font-headline font-bold text-sm tracking-tight uppercase">RUNTIME CONFIG</span>
        </div>
        <div className="flex-1" />
        <div className="flex flex-col items-end gap-1">
          <div className="flex gap-2">
            <button
              onClick={runCleanup}
              disabled={cleaning || loading}
              className="bg-surface-container-high text-error px-4 py-2 font-headline font-bold text-xs tracking-widest uppercase hover:bg-error/10 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              <span className="material-symbols-outlined text-sm">{cleaning ? 'progress_activity' : 'cleaning_services'}</span>
              {cleaning ? 'CLEANING' : 'CLEANUP NOW'}
            </button>
            <button
              onClick={reset}
              disabled={saving || loading || cleaning}
              className="bg-surface-container-high text-on-surface px-4 py-2 font-headline font-bold text-xs tracking-widest uppercase hover:bg-surface-bright transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              <span className="material-symbols-outlined text-sm">restart_alt</span>
              Reset
            </button>
            <button
              onClick={save}
              disabled={!dirty || saving || loading || cleaning}
              className="bg-primary-container text-on-primary-container px-4 py-2 font-headline font-bold text-xs tracking-widest uppercase hover:bg-primary transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              <span className="material-symbols-outlined text-sm">{saving ? 'progress_activity' : 'save'}</span>
              {saving ? 'SAVING' : 'SAVE & APPLY'}
            </button>
          </div>
          <span className="text-[9px] font-mono text-outline max-w-[260px] text-right leading-tight">
            Note: Changes only affect new plans. Already generated or queued plans keep their original routing decisions.
          </span>
        </div>
      </section>

      {loading && !config && (
        <div className="flex-1 flex items-center justify-center text-outline text-sm">
          <span className="material-symbols-outlined animate-spin mr-2">progress_activity</span>
          Loading config...
        </div>
      )}

      {config && (
        <section className="flex-1 overflow-y-auto">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Proxy Rules */}
            <div className="bg-surface-container-low p-5 flex flex-col gap-5">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-sm text-tertiary">route</span>
                <h2 className="font-headline font-bold text-xs tracking-tight uppercase text-primary">Proxy Rules</h2>
              </div>
              <div className="text-[10px] font-mono text-outline leading-relaxed">
                Controls when chunks are routed through the proxy instead of direct.
              </div>
              <SliderField label="TPM Threshold %" section="proxy_rules" field="tpm_threshold_pct" min={50} max={100} step={1} />
              <SliderField label="RPM Threshold %" section="proxy_rules" field="rpm_threshold_pct" min={50} max={100} step={1} />
              <NumberField label="Chunk Size Threshold" section="proxy_rules" field="chunk_size_threshold" min={500} max={20000} />
              <NumberField label="Recent 429s Min" section="proxy_rules" field="recent_429_min_consecutive" min={1} max={10} />
              <ToggleField label="Status Rule Enabled" section="proxy_rules" field="status_rule_enabled" />
            </div>

            {/* Guard Thresholds */}
            <div className="bg-surface-container-low p-5 flex flex-col gap-5">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-sm text-tertiary">shield</span>
                <h2 className="font-headline font-bold text-xs tracking-tight uppercase text-primary">Pre-Flight Guard</h2>
              </div>
              <div className="text-[10px] font-mono text-outline leading-relaxed">
                Soft-gate thresholds applied before requests hit the wire.
              </div>
              <SliderField label="Warn Threshold" section="guard" field="warn_threshold" min={0.5} max={1.0} step={0.01} />
              <SliderField label="Block Threshold" section="guard" field="block_threshold" min={0.7} max={1.0} step={0.01} />
              <div className="bg-surface-container p-3 text-[10px] font-mono text-outline">
                <div className="flex items-start gap-2">
                  <span className="material-symbols-outlined text-sm mt-0.5">info</span>
                  <p>
                    <span className="text-secondary font-bold">Warn</span> = yellow alert, request proceeds with caution.<br />
                    <span className="text-error font-bold">Block</span> = hard no-go before actual limit breach.
                  </p>
                </div>
              </div>
            </div>

            {/* Burn Mode */}
            <div className="bg-surface-container-low p-5 flex flex-col gap-5">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-sm text-tertiary">local_fire_department</span>
                <h2 className="font-headline font-bold text-xs tracking-tight uppercase text-primary">Burn Mode</h2>
              </div>
              <div className="text-[10px] font-mono text-outline leading-relaxed">
                Controls concurrency and backpressure aggression.
              </div>
              <div className="flex flex-col gap-2">
                {BURN_MODES.map((m) => {
                  const active = config.pacer.burn_mode === m.key;
                  return (
                    <button
                      key={m.key}
                      onClick={() => updateField('pacer', 'burn_mode', m.key)}
                      disabled={loading || saving}
                      className={`p-3 text-left border transition-all disabled:opacity-50 ${
                        active
                          ? `${m.color} border-current`
                          : 'bg-surface-container border-outline-variant/20 hover:border-outline-variant'
                      }`}
                    >
                      <div className={`font-headline text-xs font-bold uppercase ${active ? m.color.split(' ')[0] : 'text-on-surface'}`}>
                        {m.label}
                      </div>
                      <div className="text-[10px] font-mono text-outline mt-1">{m.desc}</div>
                    </button>
                  );
                })}
              </div>
              <SliderField label="TPM Backpressure %" section="pacer" field="tpm_backpressure_pct" min={50} max={100} step={1} />
              <NumberField label="Default Concurrency" section="pacer" field="default_concurrency" min={1} max={16} />
            </div>
          </div>

          {/* Storage Hygiene */}
          <div className="mt-4 bg-surface-container-low p-5 flex flex-col gap-5">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-sm text-tertiary">cleaning_services</span>
              <h2 className="font-headline font-bold text-xs tracking-tight uppercase text-primary">Storage Hygiene</h2>
            </div>
            <div className="text-[10px] font-mono text-outline leading-relaxed">
              Automatic TTL cleanup runs on startup and every interval. Files older than the retention threshold are deleted.
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <NumberField label="Plan Retention (days)" section="cleanup" field="plan_retention_days" min={1} max={365} />
              <NumberField label="Stress Retention (days)" section="cleanup" field="stress_retention_days" min={1} max={90} />
              <NumberField label="History Retention (days)" section="cleanup" field="history_retention_days" min={1} max={365} />
              <NumberField label="Cleanup Interval (hours)" section="cleanup" field="interval_hours" min={1} max={168} />
              <NumberField label="Warning Threshold (MB)" section="cleanup" field="storage_warning_mb" min={1} max={10000} />
              <NumberField label="Critical Threshold (MB)" section="cleanup" field="storage_critical_mb" min={1} max={10000} />
            </div>
          </div>
        </section>
      )}

      {toast && (
        <div className="fixed top-20 right-6 bg-surface-container-high text-on-surface px-4 py-3 border border-outline-variant shadow-lg text-xs font-mono z-50 max-w-xs">
          {toast}
        </div>
      )}
    </main>
  );
};

export default Config;
