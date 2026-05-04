import React from 'react';
import { KeyVaultAPI, GatewayKeys, KeyTelemetry } from '../lib/api';

const KeyVault: React.FC = () => {
  const [keys, setKeys] = React.useState<GatewayKeys[]>([]);
  const [telemetry, setTelemetry] = React.useState<KeyTelemetry | null>(null);
  const [expanded, setExpanded] = React.useState<Set<string>>(new Set(['google']));
  const [formOpen, setFormOpen] = React.useState<Record<string,boolean>>({});
  const [form, setForm] = React.useState<{label:string; key:string}>({label:'',key:''});
  const [toast, setToast] = React.useState<string | null>(null);

  const load = async () => {
    const [k, t] = await Promise.all([KeyVaultAPI.getKeys(), KeyVaultAPI.getTelemetry()]);
    setKeys(k);
    setTelemetry(t);
  };

  React.useEffect(() => { load(); const iv = setInterval(load, 10000); return ()=>clearInterval(iv); }, []);

  const showToast = (msg: string) => { setToast(msg); setTimeout(()=>setToast(null), 3000); };

  const toggleExpand = (g: string) => {
    const n = new Set(expanded);
    n.has(g) ? n.delete(g) : n.add(g);
    setExpanded(n);
  };

  const handleTest = async (gateway: string, label: string) => {
    try { const r = await KeyVaultAPI.testKey(gateway, label); showToast(`${label}: ${r.valid?'OK':'FAIL'} ${r.latency_ms.toFixed(0)}ms`); }
    catch(e:any){ showToast(e.message); }
  };

  const handleToggle = async (gateway: string, label: string) => {
    const r = await KeyVaultAPI.toggleKey(gateway, label);
    showToast(r.message);
    load();
  };

  const handleDelete = async (gateway: string, label: string) => {
    if (!confirm(`Delete ${label}?`)) return;
    await KeyVaultAPI.deleteKey(gateway, label);
    showToast('Deleted'); load();
  };

  const handleAdd = async (gateway: string) => {
    if (!form.label || !form.key) return;
    await KeyVaultAPI.addKey(gateway, form.label, form.key);
    setForm({label:'',key:''});
    setFormOpen(o=>({...o,[gateway]:false}));
    showToast('Key added'); load();
  };

  const gateways = ['google','groq','deepseek','mistral'];

  return (
    <main className="pt-16 pb-8 min-h-screen overflow-y-auto">
      <div className="px-6 py-8 max-w-[1440px] mx-auto">
        <section className="mb-10">
          <div className="flex items-end justify-between mb-6">
            <div>
              <h1 className="text-4xl font-headline font-bold tracking-tighter text-primary uppercase">Key Management</h1>
              <p className="text-on-surface-variant font-mono text-xs mt-1">SEC_VAULT_ACTIVE // ROOT_ACCESS_GRANTED</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-[1px] bg-background border border-outline-variant/20">
            <StatCard label="Total Keys" value={String(telemetry?.total_keys ?? 0)} sub="+3_THIS_MONTH" color="text-on-surface" />
            <StatCard label="Healthy" value={`${telemetry?.healthy_keys ?? 0}`} sub="SYNC_OPTIMAL" color="text-tertiary" />
            <StatCard label="Cost (MTD)" value={`$${(telemetry?.estimated_daily_cost ?? 0).toFixed(2)}`} sub="EST_$2.1K_END" color="text-on-surface" />
            <StatCard label="Error Rate" value={`${((telemetry?.error_rate ?? 0)*100).toFixed(2)}%`} sub="GATEWAY_TIMEOUTS" color="text-error" />
          </div>
        </section>

        <section className="flex flex-col gap-4">
          {gateways.map(gw => {
            const section = keys.find(k => k.gateway === gw);
            const isOpen = expanded.has(gw);
            const statusColor = section?.status==='active'?'text-tertiary border-tertiary/20 bg-tertiary/10':section?.status==='degraded'?'text-secondary border-secondary/20 bg-secondary/10':'text-error border-error/20 bg-error/10';
            return (
              <div key={gw} className="bg-surface-container-low overflow-hidden">
                <div onClick={()=>toggleExpand(gw)} className="flex items-center justify-between p-4 bg-surface-container cursor-pointer hover:bg-surface-container-high transition-colors">
                  <div className="flex items-center gap-4">
                    <span className="material-symbols-outlined text-primary">{iconFor(gw)}</span>
                    <div>
                      <h3 className="font-headline font-bold text-on-surface uppercase tracking-tight">{gw.toUpperCase()}</h3>
                      <p className="font-mono text-[10px] text-outline">{section?.keys.length ? `${section.key_count} KEYS` : 'NO KEYS'}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="flex flex-col items-end">
                      <span className="font-mono text-xs text-on-surface">{section?.key_count || 0} KEYS</span>
                      <span className="font-mono text-[10px] text-tertiary">{section?.healthy_count || 0} ACTIVE</span>
                    </div>
                    <span className={`px-2 py-0.5 text-[10px] font-mono uppercase tracking-widest border ${statusColor}`}>{(section?.status || 'UNKNOWN').toUpperCase()}</span>
                    <span className="material-symbols-outlined text-outline">{isOpen?'expand_less':'expand_more'}</span>
                  </div>
                </div>
                {isOpen && (
                  <div className="p-4 flex flex-col gap-[2px]">
                    {(section?.keys || []).map((k:any, idx:number) => (
                      <div key={idx} className="grid grid-cols-12 items-center py-3 px-4 bg-surface-container-lowest hover:bg-surface-container transition-colors group">
                        <div className="col-span-3"><p className="font-headline font-bold text-sm text-on-surface uppercase">{k.label}</p></div>
                        <div className="col-span-4 flex items-center gap-2">
                          <span className="font-mono text-xs text-outline">{k.masked_key}</span>
                        </div>
                        <div className="col-span-1 flex justify-center">
                          <div className={`w-2 h-2 rounded-full ${k.status==='healthy'?'bg-tertiary shadow-[0_0_8px_#c3e7ff]':'bg-error'}`} />
                        </div>
                        <div className="col-span-2 text-right"><span className="font-mono text-xs text-outline uppercase">Usage: <span className="text-on-surface">{k.usage_today} req</span></span></div>
                        <div className="col-span-2 flex justify-end gap-3">
                          <button onClick={()=>handleTest(gw,k.label)} className="text-[10px] font-mono text-primary hover:text-white transition-colors">TEST</button>
                          <button onClick={()=>handleToggle(gw,k.label)} className="text-[10px] font-mono text-secondary hover:text-white transition-colors">{k.on_cooldown?'ENABLE':'DISABLE'}</button>
                          <button onClick={()=>handleDelete(gw,k.label)} className="text-[10px] font-mono text-error hover:text-white transition-colors">DELETE</button>
                        </div>
                      </div>
                    ))}
                    <div className="mt-4 border border-dashed border-outline-variant/30 p-4 bg-surface-container-lowest flex flex-col gap-4">
                      <div className="flex items-center justify-between">
                        <h4 className="font-headline font-bold text-xs text-outline uppercase tracking-widest">Register New Key</h4>
                        <button onClick={()=>setFormOpen(o=>({...o,[gw]:!o[gw]}))} className="text-[10px] font-mono text-on-surface-variant hover:text-primary transition-colors">{formOpen[gw]?'CLOSE_FORM':'OPEN_FORM'}</button>
                      </div>
                      {formOpen[gw] && (
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div className="flex flex-col gap-1">
                            <label className="text-[10px] font-mono text-outline uppercase">Label</label>
                            <input value={form.label} onChange={e=>setForm(f=>({...f,label:e.target.value}))} className="bg-surface-container-high border-none text-sm font-mono focus:ring-1 focus:ring-secondary h-10 px-2" placeholder="e.g. PROD_KEY" />
                          </div>
                          <div className="flex flex-col gap-1">
                            <label className="text-[10px] font-mono text-outline uppercase">Secret Key</label>
                            <input value={form.key} onChange={e=>setForm(f=>({...f,key:e.target.value}))} type="password" className="bg-surface-container-high border-none text-sm font-mono focus:ring-1 focus:ring-secondary h-10 px-2" placeholder="••••••••" />
                          </div>
                          <div className="flex items-end"><button onClick={()=>handleAdd(gw)} className="w-full bg-primary-container text-on-primary-container font-headline font-bold text-xs h-10 uppercase tracking-tighter hover:bg-primary transition-colors">Add Key to Vault</button></div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </section>
      </div>
      {toast && <div className="fixed top-20 right-6 bg-surface-container-high border border-outline-variant px-4 py-3 text-sm font-mono z-[100]">{toast}</div>}
    </main>
  );
};

function iconFor(gw:string){ return gw==='google'?'cloud':gw==='groq'?'bolt':gw==='deepseek'?'psychology':'wind_power'; }

const StatCard: React.FC<{label:string;value:string;sub:string;color:string}> = ({label,value,sub,color}) => (
  <div className="bg-surface-container-low p-5 flex flex-col gap-1">
    <span className="text-[10px] font-mono text-outline uppercase">{label}</span>
    <span className={`text-3xl font-headline font-bold tracking-tighter ${color}`}>{value}</span>
    <span className="text-[10px] font-mono text-tertiary">{sub}</span>
  </div>
);

export default KeyVault;
