import React from 'react';
import { ModelRegistryAPI, ModelDetail, ModelRegistryResponse, RegisterModelRequest } from '../lib/api';

const ModelRegistry: React.FC = () => {
  const [data, setData] = React.useState<ModelRegistryResponse | null>(null);
  const [filter, setFilter] = React.useState<string>('ALL');
  const [testingId, setTestingId] = React.useState<string | null>(null);
  const [toast, setToast] = React.useState<string | null>(null);
  const [showForm, setShowForm] = React.useState(false);
  const [form, setForm] = React.useState<RegisterModelRequest>({
    id: '', gateway: 'groq', tier: 'free', note: '', rpm: undefined, tpm: undefined, context_window: undefined, input_price_1m: 0, output_price_1m: 0
  });

  React.useEffect(() => {
    ModelRegistryAPI.getRegistry().then(setData);
  }, []);

  const showToast = (msg: string) => { setToast(msg); setTimeout(()=>setToast(null), 3000); };

  const test = async (id: string) => {
    setTestingId(id);
    try {
      const res = await ModelRegistryAPI.testModel(id);
      showToast(`${id}: ${res.working ? 'OK' : 'FAIL'} ${res.latency_ms.toFixed(0)}ms`);
    } catch (e: any) { showToast(`Test error: ${e.message}`); }
    setTestingId(null);
  };

  const freeze = async (id: string) => {
    await ModelRegistryAPI.freezeModel(id);
    setData((d) => d ? { ...d, models: d.models.map(m => m.id===id ? {...m, status:'frozen'} : m), frozen_count: d.frozen_count+1, active_count: Math.max(0, d.active_count-1) } : d);
    showToast(`${id} frozen`);
  };

  const unfreeze = async (id: string) => {
    await ModelRegistryAPI.unfreezeModel(id);
    setData((d) => d ? { ...d, models: d.models.map(m => m.id===id ? {...m, status:'active'} : m), frozen_count: Math.max(0, d.frozen_count-1), active_count: d.active_count+1 } : d);
    showToast(`${id} unfrozen`);
  };

  const register = async () => {
    if (!form.id || !form.gateway || !form.tier) { showToast('Fill required fields'); return; }
    try {
      await ModelRegistryAPI.registerModel(form);
      showToast(`${form.id} registered`);
      setShowForm(false);
      setForm({ id: '', gateway: 'groq', tier: 'free', note: '', rpm: undefined, tpm: undefined, context_window: undefined, input_price_1m: 0, output_price_1m: 0 });
      ModelRegistryAPI.getRegistry().then(setData);
    } catch (e: any) { showToast(e.message); }
  };

  const models = React.useMemo(() => {
    if (!data) return [];
    if (filter === 'ALL') return data.models;
    return data.models.filter(m => m.gateway.toUpperCase() === filter);
  }, [data, filter]);

  return (
    <main className="pt-16 pb-8 min-h-screen overflow-y-auto">
      <div className="p-8 max-w-[1600px] mx-auto">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <h1 className="text-4xl font-headline font-bold tracking-tighter uppercase text-primary">Model Registry</h1>
              <div className="flex gap-2">
                <span className="px-2 py-0.5 bg-[#181c20] text-tertiary font-mono text-xs flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />{data?.active_count || 0} ACTIVE</span>
                <span className="px-2 py-0.5 bg-[#181c20] text-secondary font-mono text-xs flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-secondary" />{data?.frozen_count || 0} FROZEN</span>
              </div>
            </div>
            <p className="text-on-surface-variant max-w-2xl font-body text-sm">Central repository for neural network weights, deployment configurations, and operational throughput monitoring.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {['ALL','GOOGLE','GROQ','DEEPSEEK','MISTRAL'].map(g => (
              <button key={g} onClick={()=>setFilter(g)} className={`px-4 py-2 font-headline font-bold text-xs uppercase tracking-wider transition-colors ${filter===g?'bg-primary-container text-on-primary-container':'bg-surface-container hover:bg-surface-container-high text-on-surface-variant'}`}>{g==='ALL'?'ALL_GATEWAYS':g}</button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-1">
          {models.map((m) => (
            <ModelCard key={m.id} model={m} testing={testingId===m.id} onTest={()=>test(m.id)} onFreeze={()=>freeze(m.id)} onUnfreeze={()=>unfreeze(m.id)} />
          ))}
          <div onClick={()=>setShowForm(true)} className="bg-surface-container/50 p-5 flex items-center justify-center border-dashed border-2 border-outline-variant/20 hover:bg-surface-container hover:border-primary/40 cursor-pointer transition-all">
            <div className="flex flex-col items-center gap-2">
              <span className="material-symbols-outlined text-4xl text-outline-variant">add_box</span>
              <span className="font-headline font-bold text-xs uppercase tracking-widest text-outline-variant">REGISTER_NEW_MODEL</span>
            </div>
          </div>
        </div>

        <div className="mt-12 grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-[#181c20] p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="font-headline font-bold text-xl uppercase tracking-tighter text-primary">Deployment History</h2>
              <span className="text-[10px] font-mono text-on-surface-variant">AUTO_RELOAD: ON</span>
            </div>
            <div className="space-y-4">
              <LogRow time="14:02:11" tag="SYSTEM" text="MODEL N-ALPHA-70B-v4 DEPLOYMENT SUCCESSFUL" color="emerald" />
              <LogRow time="13:45:00" tag="GATEWAY" text="SIGMA_LITE_13B MOVED TO FROZEN STATE" color="secondary" />
              <LogRow time="13:12:44" tag="SYNC" text="REGISTRY SYNC COMPLETED ACROSS 12 GLOBAL NODES" color="primary" />
              <LogRow time="12:59:02" tag="ALARM" text="THROUGHPUT ANOMALY DETECTED ON OMNI_GATE_BASE" color="error" />
            </div>
          </div>
          <div className="bg-surface-container p-6 relative overflow-hidden">
            <div className="relative z-10 flex flex-col h-full justify-between">
              <div>
                <h2 className="font-headline font-bold text-xl uppercase tracking-tighter text-secondary mb-2">Quota Summary</h2>
                <div className="space-y-4 mt-6">
                  <QuotaBar label="TOTAL_TPM_CAPACITY" pct={84} color="bg-primary" />
                  <QuotaBar label="REGISTRY_SLOTS_USED" pct={64} color="bg-secondary" />
                </div>
              </div>
              <button className="w-full border border-outline-variant/30 text-on-surface-variant hover:text-on-surface hover:border-primary py-3 font-headline font-bold text-xs uppercase tracking-[0.2em] transition-all mt-6">UPGRADE_REGISTRY_TIER</button>
            </div>
          </div>
        </div>
      </div>
      {showForm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[110] p-4">
          <div className="bg-surface-container-low w-full max-w-lg p-6 space-y-4 border border-outline-variant/20">
            <div className="flex justify-between items-center">
              <h3 className="font-headline font-bold text-lg uppercase tracking-tight">Register New Model</h3>
              <button onClick={()=>setShowForm(false)} className="material-symbols-outlined text-outline hover:text-primary">close</button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex flex-col gap-1 md:col-span-2">
                <label className="text-[10px] font-mono text-outline uppercase">Model ID *</label>
                <input value={form.id} onChange={e=>setForm({...form, id: e.target.value})} className="bg-surface-container-highest border-none p-2 font-mono text-sm" placeholder="e.g. my-model-id" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-mono text-outline uppercase">Gateway *</label>
                <select value={form.gateway} onChange={e=>setForm({...form, gateway: e.target.value as any})} className="bg-surface-container-highest border-none p-2 font-mono text-sm">
                  {['groq','google','deepseek','mistral'].map(g => <option key={g} value={g}>{g.toUpperCase()}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-mono text-outline uppercase">Tier *</label>
                <select value={form.tier} onChange={e=>setForm({...form, tier: e.target.value as any})} className="bg-surface-container-highest border-none p-2 font-mono text-sm">
                  {['free','cheap','expensive'].map(t => <option key={t} value={t}>{t.toUpperCase()}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1 md:col-span-2">
                <label className="text-[10px] font-mono text-outline uppercase">Note</label>
                <input value={form.note} onChange={e=>setForm({...form, note: e.target.value})} className="bg-surface-container-highest border-none p-2 font-mono text-sm" placeholder="Short description" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-mono text-outline uppercase">RPM</label>
                <input type="number" value={form.rpm || ''} onChange={e=>setForm({...form, rpm: Number(e.target.value) || undefined})} className="bg-surface-container-highest border-none p-2 font-mono text-sm" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-mono text-outline uppercase">TPM</label>
                <input type="number" value={form.tpm || ''} onChange={e=>setForm({...form, tpm: Number(e.target.value) || undefined})} className="bg-surface-container-highest border-none p-2 font-mono text-sm" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-mono text-outline uppercase">Context Window</label>
                <input type="number" value={form.context_window || ''} onChange={e=>setForm({...form, context_window: Number(e.target.value) || undefined})} className="bg-surface-container-highest border-none p-2 font-mono text-sm" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-mono text-outline uppercase">Input Price / 1M</label>
                <input type="number" step="0.001" value={form.input_price_1m || ''} onChange={e=>setForm({...form, input_price_1m: Number(e.target.value) || undefined})} className="bg-surface-container-highest border-none p-2 font-mono text-sm" />
              </div>
            </div>
            <div className="flex gap-2 pt-2">
              <button onClick={register} className="flex-1 bg-primary text-on-primary py-2 font-headline font-bold text-xs uppercase tracking-widest hover:opacity-90">Register</button>
              <button onClick={()=>setShowForm(false)} className="flex-1 bg-surface-container-high text-on-surface py-2 font-headline font-bold text-xs uppercase tracking-widest hover:bg-surface-bright">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {toast && (
        <div className="fixed top-20 right-6 bg-surface-container-high border border-outline-variant px-4 py-3 text-sm font-mono z-[100]">
          {toast}
        </div>
      )}
    </main>
  );
};

const ModelCard: React.FC<{model: ModelDetail; testing: boolean; onTest:()=>void; onFreeze:()=>void; onUnfreeze:()=>void}> = ({model, testing, onTest, onFreeze, onUnfreeze}) => {
  const isFrozen = model.status === 'frozen';
  return (
    <div className={`bg-surface-container p-5 flex flex-col gap-4 transition-all ${isFrozen?'opacity-70 hover:opacity-100 border-l-2 border-secondary/30':''}`}>
      <div className="flex justify-between items-start">
        <div className="space-y-1">
          <div className="text-[10px] text-primary font-mono tracking-widest uppercase opacity-60">ID: {model.id}</div>
          <h3 className="font-mono text-lg font-bold text-on-surface uppercase tracking-tight">{model.id.replace(/-/g,'_').toUpperCase()}</h3>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className="text-[10px] bg-primary/10 text-primary px-2 py-0.5 font-bold tracking-tighter">{model.tier?.toUpperCase() || 'TIER_STD'}</span>
          <span className={`flex items-center gap-1 text-[10px] font-bold ${isFrozen?'text-secondary':'text-emerald-500'}`}>
            <span className="material-symbols-outlined text-xs" style={{fontVariationSettings:"'FILL' 1"}}>{isFrozen?'ac_unit':'check_circle'}</span>
            {isFrozen ? 'FROZEN' : 'OPERATIONAL'}
          </span>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2 py-4 border-y border-outline-variant/10">
        <div className="flex flex-col"><span className="text-[9px] text-on-surface-variant uppercase font-mono">RPM</span><span className="font-mono text-base font-bold text-on-surface">{model.rpm ?? '—'}</span></div>
        <div className="flex flex-col"><span className="text-[9px] text-on-surface-variant uppercase font-mono">TPM</span><span className="font-mono text-base font-bold text-on-surface">{model.tpm ?? '—'}</span></div>
        <div className="flex flex-col"><span className="text-[9px] text-on-surface-variant uppercase font-mono">CTX</span><span className="font-mono text-base font-bold text-on-surface">{model.context_window ? `${(model.context_window/1000).toFixed(0)}K` : '—'}</span></div>
      </div>
      <div className="flex justify-between items-center text-[10px]">
        <span className="text-on-surface-variant font-mono">EST. COST: <span className="text-secondary">${model.input_price_1m?.toFixed(3) || '0.000'} / 1M TKNS</span></span>
        <span className="text-on-surface-variant font-mono">{model.gateway.toUpperCase()}</span>
      </div>
      <div className="flex gap-1 mt-2">
        <button disabled={testing || isFrozen} onClick={onTest} className="flex-1 bg-primary-container text-on-primary-container font-headline font-bold text-[10px] py-2 uppercase tracking-widest disabled:opacity-50">{testing?'TESTING...':'RUN_TEST'}</button>
        {isFrozen ? (
          <button onClick={onUnfreeze} className="flex-1 bg-secondary text-on-secondary font-headline font-bold text-[10px] py-2 uppercase tracking-widest transition-all">UNFREEZE</button>
        ) : (
          <button onClick={onFreeze} className="flex-1 bg-surface-container-high hover:bg-secondary text-on-surface-variant hover:text-on-secondary font-headline font-bold text-[10px] py-2 uppercase tracking-widest transition-all">FREEZE</button>
        )}
      </div>
    </div>
  );
};

const LogRow: React.FC<{time:string; tag:string; text:string; color:'emerald'|'secondary'|'primary'|'error'}> = ({time,tag,text,color}) => {
  const border = color==='emerald'?'border-emerald-500':color==='secondary'?'border-secondary':color==='primary'?'border-primary':'border-error';
  const textCol = color==='emerald'?'text-emerald-500':color==='secondary'?'text-secondary':color==='primary'?'text-primary':'text-error';
  return (
    <div className={`flex items-center gap-4 text-[11px] font-mono border-l-2 ${border} pl-4 py-1`}>
      <span className="text-on-surface-variant shrink-0">{time}</span>
      <span className={`${textCol} shrink-0`}>[{tag}]</span>
      <span className="text-on-surface">{text}</span>
    </div>
  );
};

const QuotaBar: React.FC<{label:string; pct:number; color:string}> = ({label,pct,color}) => (
  <div className="space-y-1">
    <div className="flex justify-between text-[10px] font-mono text-on-surface-variant"><span>{label}</span><span>{pct}%</span></div>
    <div className="h-1 bg-surface-container-highest w-full"><div className={`h-full ${color}`} style={{width:`${pct}%`}} /></div>
  </div>
);

export default ModelRegistry;
