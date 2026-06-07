import React from 'react';
import { DashboardAPI, AdminAPI, HealthResponse, TelemetryPayload, DashboardSettings, HistoryEntry, StorageStats, SystemStatus } from '../lib/api';

const Dashboard: React.FC = () => {
  const [health, setHealth] = React.useState<HealthResponse | null>(null);
  const [telemetry, setTelemetry] = React.useState<TelemetryPayload | null>(null);
  const [settings, setSettings] = React.useState<DashboardSettings | null>(null);
  const [history, setHistory] = React.useState<HistoryEntry[]>([]);
  const [storage, setStorage] = React.useState<StorageStats | null>(null);
  const [systemStatus, setSystemStatus] = React.useState<SystemStatus | null>(null);
  const [perfMode, setPerfMode] = React.useState<'stealth' | 'balanced' | 'apex'>('balanced');
  const [settingsLoading, setSettingsLoading] = React.useState<string | null>(null);
  const [perfLoading, setPerfLoading] = React.useState(false);

  React.useEffect(() => {
    DashboardAPI.getHealth().then(setHealth);
    DashboardAPI.getSettings().then(setSettings);
    DashboardAPI.getHistory(20).then(setHistory);
    AdminAPI.getStorage().then(setStorage);
    AdminAPI.getSystemStatus().then(setSystemStatus);
    const es = DashboardAPI.streamTelemetry((d) => setTelemetry(d));
    const iv = setInterval(() => {
      DashboardAPI.getHealth().then(setHealth);
      DashboardAPI.getHistory(20).then(setHistory);
      AdminAPI.getStorage().then(setStorage);
      AdminAPI.getSystemStatus().then(setSystemStatus);
    }, 5000);
    return () => { es.close(); clearInterval(iv); };
  }, []);

  const toggle = async (key: 'tunnel' | 'stealth' | 'success_logs' | 'fail_logs') => {
    setSettingsLoading(key);
    try {
      const res = await DashboardAPI.toggleSetting(key);
      setSettings((s) => s ? { ...s, [key === 'tunnel' ? 'tunnel_mode' : key === 'stealth' ? 'quiet_mode' : key === 'success_logs' ? 'success_logging' : 'failed_logging']: res.new_state } : s);
    } finally {
      setSettingsLoading(null);
    }
  };

  const setPerf = async (mode: 'stealth' | 'balanced' | 'apex') => {
    setPerfLoading(true);
    try {
      await DashboardAPI.setPerformanceMode(mode);
      setPerfMode(mode);
    } finally {
      setPerfLoading(false);
    }
  };

  const integrity = health?.integrity || { groq: 0, google: 0, deepseek: 0, mistral: 0 };

  const fmtBytes = (b: number) => {
    if (b > 1024 * 1024) return `${(b / (1024 * 1024)).toFixed(1)} MB`;
    if (b > 1024) return `${(b / 1024).toFixed(1)} KB`;
    return `${b} B`;
  };

  const fmtAge = (mtime: number | null) => {
    if (!mtime) return '—';
    const days = (Date.now() / 1000 - mtime) / 86400;
    return `${days.toFixed(0)}d`;
  };

  const healthColor = (rate: number) => {
    if (rate > 20) return 'text-error';
    if (rate > 10) return 'text-amber-400';
    return 'text-emerald-400';
  };

  return (
    <main className="pt-4 pb-8 min-h-[calc(100vh-32px)] overflow-y-auto">
      <div className="p-6 pb-12 max-w-[1600px] mx-auto space-y-1">
        {/* System Health Card */}
        {systemStatus && (
          <section className="bg-surface-container-low p-4 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
            <div className="flex flex-col justify-between aspect-square bg-surface-container p-3">
              <span className="font-headline text-[10px] text-outline uppercase">QUEUE</span>
              <div className="font-mono text-xl font-bold text-on-surface">{systemStatus.queue.depth}</div>
              <span className="font-mono text-[8px] text-outline uppercase">{systemStatus.queue.state}</span>
            </div>
            <div className="flex flex-col justify-between aspect-square bg-surface-container p-3">
              <span className="font-headline text-[10px] text-outline uppercase">FAIL RATE 24H</span>
              <div className={`font-mono text-xl font-bold ${healthColor(systemStatus.failure_rate_24h)}`}>{systemStatus.failure_rate_24h}%</div>
              <span className="font-mono text-[8px] text-outline">{systemStatus.queue.failed_today} FAILED</span>
            </div>
            <div className="flex flex-col justify-between aspect-square bg-surface-container p-3">
              <span className="font-headline text-[10px] text-outline uppercase">COMPLETED 24H</span>
              <div className="font-mono text-xl font-bold text-emerald-400">{systemStatus.queue.completed_today}</div>
              <span className="font-mono text-[8px] text-outline">RUNS</span>
            </div>
            <div className={`flex flex-col justify-between aspect-square p-3 ${systemStatus.storage_status==='critical'?'bg-error/10 border border-error/30':systemStatus.storage_status==='warning'?'bg-amber-400/10 border border-amber-400/30':'bg-surface-container'}`}>
              <span className={`font-headline text-[10px] uppercase ${systemStatus.storage_status==='critical'?'text-error':systemStatus.storage_status==='warning'?'text-amber-400':'text-outline'}`}>STORAGE</span>
              <div className={`font-mono text-xl font-bold ${systemStatus.storage_status==='critical'?'text-error':systemStatus.storage_status==='warning'?'text-amber-400':'text-on-surface'}`}>{systemStatus.storage.total_mb}</div>
              <span className={`font-mono text-[8px] ${systemStatus.storage_status==='critical'?'text-error':systemStatus.storage_status==='warning'?'text-amber-400':'text-outline'}`}>MB TOTAL</span>
            </div>
            <div className="flex flex-col justify-between aspect-square bg-surface-container p-3">
              <span className="font-headline text-[10px] text-outline uppercase">PLANS</span>
              <div className="font-mono text-xl font-bold text-on-surface">{systemStatus.storage.plans}</div>
              <span className="font-mono text-[8px] text-outline">STORED</span>
            </div>
            <div className="flex flex-col justify-between aspect-square bg-surface-container p-3">
              <span className="font-headline text-[10px] text-outline uppercase">HISTORY</span>
              <div className="font-mono text-xl font-bold text-on-surface">{systemStatus.storage.history}</div>
              <span className="font-mono text-[8px] text-outline">RUNS</span>
            </div>
            <div className="flex flex-col justify-between aspect-square bg-surface-container p-3">
              <span className="font-headline text-[10px] text-outline uppercase">STRESS</span>
              <div className="font-mono text-xl font-bold text-on-surface">{systemStatus.storage.stress}</div>
              <span className="font-mono text-[8px] text-outline">REPORTS</span>
            </div>
            <div className="flex flex-col justify-between aspect-square bg-surface-container p-3">
              <span className="font-headline text-[10px] text-outline uppercase">KEYS</span>
              <div className="font-mono text-xl font-bold text-on-surface">
                {systemStatus.keys.groq + systemStatus.keys.google + systemStatus.keys.deepseek + systemStatus.keys.mistral}
              </div>
              <span className="font-mono text-[8px] text-outline">TOTAL</span>
            </div>
          </section>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-1">
          <section className="bg-surface-container-low p-6 flex flex-col gap-6">
            <div className="flex items-center justify-between">
              <h2 className="font-headline text-xl font-extrabold tracking-tighter uppercase text-primary">System Integrity</h2>
              <span className="material-symbols-outlined text-secondary text-sm">verified_user</span>
            </div>
            <div className="space-y-6 mt-2">
              {Object.entries(integrity).map(([k, v]) => {
                const pct = Math.min((v as number) * 10, 100);
                const ok = (v as number) > 0;
                return (
                  <div key={k} className="space-y-2">
                    <div className="flex justify-between items-end">
                      <span className="font-mono text-xs text-on-surface-variant uppercase">NODE_{k}</span>
                      <span className={`font-mono text-xs ${ok ? 'text-secondary' : 'text-error'}`}>{(v as number).toFixed(3)} INTG</span>
                    </div>
                    <div className="h-2 w-full bg-surface-container">
                      <div className={`h-full ${ok ? 'bg-secondary' : 'bg-error'}`} style={{ width: `${Math.max(pct, 5)}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="mt-auto pt-6 border-t border-outline-variant/20">
              <div className="bg-surface-container p-4">
                <h3 className="font-headline text-[10px] text-outline uppercase tracking-widest mb-2">Network Map</h3>
                <div className="aspect-video bg-background relative overflow-hidden p-3">
                  <div className="absolute inset-0 opacity-10 bg-[radial-gradient(circle_at_center,#aac7ff_0%,transparent_70%)]" />
                  <div className="relative z-10 grid grid-cols-2 gap-2 h-full">
                    {Object.entries(health?.integrity || {}).map(([k, v]) => {
                      const count = v as number;
                      const ok = count > 0;
                      return (
                        <div key={k} className={`flex flex-col items-center justify-center border ${ok ? 'border-secondary/30 bg-surface-container' : 'border-error/30 bg-error/5'}`}>
                          <span className={`text-[10px] font-mono uppercase ${ok ? 'text-secondary' : 'text-error'}`}>{k}</span>
                          <span className="font-mono text-lg font-bold text-on-surface">{count}</span>
                          <span className="text-[9px] font-mono text-outline">{ok ? 'ONLINE' : 'OFFLINE'}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="bg-surface-container p-6 flex flex-col gap-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 bg-tertiary blink-dot rounded-full" />
                <h2 className="font-headline text-xl font-extrabold tracking-tighter uppercase text-primary">Live Telemetry</h2>
              </div>
              <span className="font-mono text-[10px] text-outline">STREAMS_ACTIVE: {telemetry ? '1' : '0'}</span>
            </div>
            <div className="grid grid-cols-2 gap-1">
              <div className="bg-surface-container-high p-4 flex flex-col justify-between aspect-square">
                <span className="font-headline text-[10px] text-outline uppercase">RPM_LOAD</span>
                <div className="font-mono text-3xl text-secondary font-bold">{Math.round(telemetry?.rpm || 0).toLocaleString()}</div>
                <div className="text-[10px] text-secondary/60">LIVE</div>
              </div>
              <div className="bg-surface-container-high p-4 flex flex-col justify-between aspect-square">
                <span className="font-headline text-[10px] text-outline uppercase">TPS_FLOW</span>
                <div className="font-mono text-3xl text-tertiary font-bold">{(telemetry?.tps || 0).toFixed(1)}</div>
                <div className="text-[10px] text-tertiary/60">NOMINAL</div>
              </div>
              <div className="bg-surface-container-high p-4 flex flex-col justify-between aspect-square">
                <span className="font-headline text-[10px] text-outline uppercase">SUCCESS_RATE</span>
                <div className="font-mono text-3xl text-emerald-400 font-bold">{Math.round((telemetry?.success_rate || 0) * 100) / 100}%</div>
                <div className="flex gap-1 h-1 w-full bg-surface-dim mt-2"><div className="h-full bg-emerald-400 flex-grow" /></div>
              </div>
              <div className="bg-surface-container-high p-4 flex flex-col justify-between aspect-square">
                <span className="font-headline text-[10px] text-outline uppercase">COMPUTE_COST</span>
                <div className="font-mono text-3xl text-secondary font-bold">${(telemetry?.cost || 0).toFixed(2)}</div>
                <span className="font-mono text-[8px] text-outline">PER_1K_TOKENS</span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-1">
              <div className="bg-surface-container-high p-4 flex flex-col justify-between aspect-square">
                <span className="font-headline text-[10px] text-outline uppercase">PROXY_TOKENS</span>
                <div className="font-mono text-2xl text-tertiary font-bold">{Math.round(telemetry?.proxy_tokens || 0).toLocaleString()}</div>
                <span className="font-mono text-[8px] text-outline">{(telemetry?.tokens || 0) > 0 ? Math.round(((telemetry?.proxy_tokens || 0) / telemetry!.tokens) * 100) : 0}% OF TOTAL</span>
              </div>
              <div className="bg-surface-container-high p-4 flex flex-col justify-between aspect-square">
                <span className="font-headline text-[10px] text-outline uppercase">DIRECT_TOKENS</span>
                <div className="font-mono text-2xl text-secondary font-bold">{Math.round(telemetry?.direct_tokens || 0).toLocaleString()}</div>
                <span className="font-mono text-[8px] text-outline">{(telemetry?.tokens || 0) > 0 ? Math.round(((telemetry?.direct_tokens || 0) / telemetry!.tokens) * 100) : 0}% OF TOTAL</span>
              </div>
              <div className="bg-surface-container-high p-4 flex flex-col justify-between aspect-square">
                <span className="font-headline text-[10px] text-outline uppercase">PROXY_COST</span>
                <div className="font-mono text-2xl text-tertiary font-bold">${(telemetry?.proxy_cost || 0).toFixed(2)}</div>
                <span className="font-mono text-[8px] text-outline">{(telemetry?.cost || 0) > 0 ? Math.round(((telemetry?.proxy_cost || 0) / telemetry!.cost) * 100) : 0}% OF TOTAL</span>
              </div>
              <div className="bg-surface-container-high p-4 flex flex-col justify-between aspect-square">
                <span className="font-headline text-[10px] text-outline uppercase">DIRECT_COST</span>
                <div className="font-mono text-2xl text-secondary font-bold">${(telemetry?.direct_cost || 0).toFixed(2)}</div>
                <span className="font-mono text-[8px] text-outline">{(telemetry?.cost || 0) > 0 ? Math.round(((telemetry?.direct_cost || 0) / telemetry!.cost) * 100) : 0}% OF TOTAL</span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-1">
              <div className="bg-surface-container-high p-4 flex flex-col justify-between aspect-square">
                <span className="font-headline text-[10px] text-outline uppercase">PROXY_STRIKES</span>
                <div className="font-mono text-2xl text-tertiary font-bold">{Math.round(telemetry?.proxy_strikes || 0).toLocaleString()}</div>
                <span className="font-mono text-[8px] text-outline">{(telemetry?.proxy_strikes || 0) + (telemetry?.direct_strikes || 0) > 0 ? Math.round(((telemetry?.proxy_strikes || 0) / ((telemetry?.proxy_strikes || 0) + (telemetry?.direct_strikes || 0))) * 100) : 0}% OF TOTAL</span>
              </div>
              <div className="bg-surface-container-high p-4 flex flex-col justify-between aspect-square">
                <span className="font-headline text-[10px] text-outline uppercase">DIRECT_STRIKES</span>
                <div className="font-mono text-2xl text-secondary font-bold">{Math.round(telemetry?.direct_strikes || 0).toLocaleString()}</div>
                <span className="font-mono text-[8px] text-outline">{(telemetry?.proxy_strikes || 0) + (telemetry?.direct_strikes || 0) > 0 ? Math.round(((telemetry?.direct_strikes || 0) / ((telemetry?.proxy_strikes || 0) + (telemetry?.direct_strikes || 0))) * 100) : 0}% OF TOTAL</span>
              </div>
              <div className="bg-surface-container-high p-4 flex flex-col justify-between aspect-square">
                <span className="font-headline text-[10px] text-outline uppercase">QUEUE_DEPTH</span>
                <div className="font-mono text-2xl text-secondary font-bold">{Math.round(telemetry?.queue_depth || 0).toLocaleString()}</div>
                <span className="font-mono text-[8px] text-outline">PLANS WAITING</span>
              </div>
              <div className="bg-surface-container-high p-4 flex flex-col justify-between aspect-square">
                <span className="font-headline text-[10px] text-outline uppercase">QUEUE_STATE</span>
                <div className="font-mono text-2xl text-secondary font-bold">{(telemetry?.queue_state || 'IDLE').toUpperCase()}</div>
                <span className="font-mono text-[8px] text-outline">RUNNER STATUS</span>
              </div>
            </div>
            <div className="flex-grow bg-surface-container-low p-4 flex flex-col">
              <div className="flex justify-between mb-4">
                <span className="font-headline text-[10px] text-outline uppercase">THROUGHPUT_HISTORY (24H)</span>
                <span className="font-mono text-[10px] text-secondary">MAX: {(telemetry?.rpm || 0) > 0 ? (telemetry!.rpm * 1.2).toFixed(1) : '0'}</span>
              </div>
              <div className="flex-grow flex items-end gap-[2px] h-32">
                {[40,55,45,70,85,60,50,40,75,90,80,65,45,30,55,75].map((h,i)=> (
                  <div key={i} className="bg-secondary/20 hover:bg-secondary w-full transition-all" style={{height:`${h}%`}} />
                ))}
              </div>
            </div>
          </section>

          <section className="bg-surface-container-high p-6 flex flex-col gap-6">
            <div className="flex items-center justify-between">
              <h2 className="font-headline text-xl font-extrabold tracking-tighter uppercase text-primary">Engine Settings</h2>
              <span className="material-symbols-outlined text-outline text-sm">settings_input_component</span>
            </div>
            <div className="space-y-3">
              {[
                { key: 'tunnel', label: 'TUNNEL_PROTO', val: settings?.tunnel_mode },
                { key: 'stealth', label: 'STEALTH_OVERRIDE', val: settings?.quiet_mode },
                { key: 'success_logs', label: 'SUCCESS_LOGS', val: settings?.success_logging },
                { key: 'fail_logs', label: 'FAIL_LOGS', val: settings?.failed_logging },
              ].map((t) => (
                <div
                  key={t.key}
                  className={`flex justify-between items-center p-3 bg-surface-container cursor-pointer transition-opacity ${settingsLoading === t.key ? 'opacity-50 pointer-events-none' : ''}`}
                  onClick={() => toggle(t.key as any)}
                >
                  <span className="font-mono text-xs text-on-surface">{t.label}</span>
                  <div className={`w-10 h-5 flex items-center px-1 ${t.val ? 'bg-secondary' : 'bg-outline-variant'}`}>
                    <div className={`w-3 h-3 bg-background ${t.val ? '' : 'ml-auto'}`} />
                  </div>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-3 gap-1">
              {(['stealth','balanced','apex'] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setPerf(m)}
                  disabled={perfLoading}
                  className={`p-3 flex flex-col items-center gap-1 transition-all active:opacity-80 disabled:opacity-50 ${perfMode===m ? 'bg-secondary text-on-secondary' : 'bg-surface-container hover:bg-surface-container-highest text-outline'}`}
                >
                  <span className={`font-headline text-[9px] uppercase ${perfMode===m?'font-bold':''}`}>{m}</span>
                  <span className="material-symbols-outlined text-lg">{m==='stealth'?'visibility_off':m==='balanced'?'balance':'bolt'}</span>
                </button>
              ))}
            </div>
            <div className="flex-grow flex flex-col overflow-hidden bg-background">
              <div className="p-2 border-b border-outline-variant/30 flex justify-between items-center">
                <span className="font-headline text-[10px] text-outline uppercase tracking-widest">STRIKE_HISTORY</span>
                <span className="font-mono text-[9px] text-secondary">LIVE_FEED</span>
              </div>
              <div className="overflow-y-auto flex-grow">
                <table className="w-full text-left font-mono text-[10px]">
                  <thead className="sticky top-0 bg-background border-b border-outline-variant/10">
                    <tr><th className="p-2 font-normal text-outline">TIME</th><th className="p-2 font-normal text-outline">TARGET</th><th className="p-2 font-normal text-outline">RESULT</th></tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/5">
                    {history.map((h, i) => (
                      <tr key={i} className="hover:bg-surface-container-low">
                        <td className="p-2 text-on-surface-variant">{new Date(h.timestamp).toLocaleTimeString()}</td>
                        <td className="p-2">{h.tag}</td>
                        <td className={`p-2 ${h.status==='SUCCESS'?'text-secondary':'text-error'}`}>{h.status}</td>
                      </tr>
                    ))}
                    {history.length===0 && (
                      <tr><td className="p-2 text-outline">—</td><td className="p-2 text-outline">—</td><td className="p-2 text-outline">—</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        </div>

        {/* Storage Alert Banner */}
        {systemStatus && systemStatus.storage_status !== 'ok' && (
          <div className={`p-3 flex items-center gap-3 ${systemStatus.storage_status==='critical'?'bg-error/10 border border-error/30':'bg-amber-400/10 border border-amber-400/30'}`}>
            <span className={`material-symbols-outlined text-lg ${systemStatus.storage_status==='critical'?'text-error':'text-amber-400'}`}>{systemStatus.storage_status==='critical'?'error':'warning'}</span>
            <div className="flex-1">
              <div className={`font-headline text-xs font-bold uppercase ${systemStatus.storage_status==='critical'?'text-error':'text-amber-400'}`}>
                Storage {systemStatus.storage_status}
              </div>
              <div className="font-mono text-[10px] text-on-surface-variant">
                {systemStatus.storage.total_mb} MB used. Consider running cleanup or lowering retention thresholds.
              </div>
            </div>
          </div>
        )}

        {/* Storage Stats Row */}
        <div className="mt-1 grid grid-cols-1 lg:grid-cols-3 gap-1">
          {[
            { key: 'plans', label: 'PLANS STORAGE', icon: 'description', color: 'text-secondary' },
            { key: 'history', label: 'HISTORY STORAGE', icon: 'history', color: 'text-tertiary' },
            { key: 'stress', label: 'STRESS STORAGE', icon: 'speed', color: 'text-secondary' },
          ].map((tile) => {
            const data = storage ? (storage as any)[tile.key] : { count: 0, bytes: 0, oldest_mtime: null };
            return (
              <div key={tile.key} className="bg-surface-container-low p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className={`material-symbols-outlined text-sm ${tile.color}`}>{tile.icon}</span>
                  <div>
                    <div className="font-headline text-[10px] text-outline uppercase">{tile.label}</div>
                    <div className="font-mono text-lg text-on-surface font-bold">{data.count.toLocaleString()} <span className="text-xs text-outline font-normal">files</span></div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-mono text-sm text-secondary font-bold">{fmtBytes(data.bytes)}</div>
                  <div className="font-mono text-[9px] text-outline">OLDEST: {fmtAge(data.oldest_mtime)}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </main>
  );
};

export default Dashboard;
