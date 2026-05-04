import React from 'react';
import { LiveWireAPI, API_BASE } from '../lib/api';

const LiveWire: React.FC = () => {
  const [batchId, setBatchId] = React.useState<string | null>(null);
  const [events, setEvents] = React.useState<{time:string; type:string; content:string; color:string}[]>([]);
  const [progress, setProgress] = React.useState(0);
  const [modelId, setModelId] = React.useState('llama-3.3-70b-versatile');
  const [resolvedGateway, setResolvedGateway] = React.useState<string>('groq');
  const [promptPath, setPromptPath] = React.useState('/home/flintx/hetzner/ai-engine/peacock/prompts/default.md');
  const [filePaths, setFilePaths] = React.useState<string>('');
  const [name, setName] = React.useState('LIVE_WIRE_MISSION');

  React.useEffect(() => {
    fetch(`${API_BASE}/v1/models`).then(r => r.json()).then((d: any) => {
      const found = d?.data?.find((m: any) => m.id === modelId);
      setResolvedGateway(found?.owned_by || 'unknown');
    }).catch(() => setResolvedGateway('unknown'));
  }, [modelId]);

  const addEvent = (type: string, content: string, color = 'text-on-surface') => {
    setEvents((e) => [...e, { time: new Date().toLocaleTimeString(), type, content, color }].slice(-200));
  };

  const initiate = async () => {
    try {
      const res = await LiveWireAPI.initiateMission({
        name,
        prompt_path: promptPath,
        file_paths: filePaths.split('\n').map(s=>s.trim()).filter(Boolean),
        model_id: modelId,
        settings: { temperature: 0.3, max_tokens: 4096, output_format: 'markdown' }
      });
      setBatchId(res.batch_id);
      addEvent('system', `MISSION_IGNITION_${res.batch_id}`, 'text-tertiary');
    } catch (e: any) { addEvent('error', e.message, 'text-error'); }
  };

  React.useEffect(() => {
    if (!batchId) return;
    const es = LiveWireAPI.streamMission(batchId, (ev: any) => {
      if (ev.type === 'system') addEvent('system', ev.content, 'text-tertiary');
      else if (ev.type === 'item_start') { addEvent('item_start', `Processing ${ev.file || ev.id}`, 'text-primary-container'); setProgress(p=>Math.min(p+10,90)); }
      else if (ev.type === 'item_chunk') addEvent('chunk', ev.content?.slice(0,60)+'...', 'text-outline');
      else if (ev.type === 'item_done') { addEvent('done', `Completed ${ev.id}`, 'text-emerald-400'); }
      else if (ev.type === 'mission_complete') { addEvent('complete', 'MISSION_COMPLETE', 'text-secondary font-bold'); setProgress(100); }
      else if (ev.type === 'error') addEvent('error', ev.content, 'text-error');
    });
    return () => es.close();
  }, [batchId]);

  return (
    <main className="pt-16 pb-8 h-[calc(100vh-64px-32px)] flex flex-col md:flex-row overflow-hidden">
      {/* Launcher */}
      <section className="w-full md:w-[420px] bg-surface-container-low border-r border-outline-variant/10 p-6 overflow-y-auto">
        <div className="flex items-center gap-3 mb-8">
          <span className="material-symbols-outlined text-secondary">bolt</span>
          <h1 className="font-headline font-bold text-2xl tracking-tight">LIVE WIRE MISSION</h1>
        </div>
        <div className="space-y-6">
          <div>
            <label className="block font-mono text-[10px] text-outline uppercase mb-2">MISSION_NAME</label>
            <input value={name} onChange={e=>setName(e.target.value)} className="w-full bg-surface-container-highest border-none p-3 font-mono text-sm focus:ring-0 focus:border-b-2 focus:border-secondary transition-all" />
          </div>
          <div>
            <label className="block font-mono text-[10px] text-outline uppercase mb-2">MODEL_ID</label>
            <input value={modelId} onChange={e=>setModelId(e.target.value)} className="w-full bg-surface-container-highest border-none p-3 font-mono text-sm focus:ring-0 focus:border-b-2 focus:border-secondary transition-all" />
            <div className="mt-2 flex items-center gap-2 text-[10px] font-mono text-outline">
              <span className="material-symbols-outlined text-xs">router</span>
              <span>GATEWAY_RESOLVE:</span>
              <span className="text-secondary uppercase font-bold">{resolvedGateway}</span>
            </div>
          </div>
          <div>
            <label className="block font-mono text-[10px] text-outline uppercase mb-2">PROMPT_PATH</label>
            <input value={promptPath} onChange={e=>setPromptPath(e.target.value)} className="w-full bg-surface-container-highest border-none p-3 font-mono text-sm focus:ring-0 focus:border-b-2 focus:border-secondary transition-all" />
          </div>
          <div>
            <label className="block font-mono text-[10px] text-outline uppercase mb-2">FILE_PATHS (one per line)</label>
            <textarea value={filePaths} onChange={e=>setFilePaths(e.target.value)} className="w-full bg-surface-container-highest border-none p-3 font-mono text-sm h-32 focus:ring-0 focus:border-b-2 focus:border-secondary transition-all" />
          </div>
          <div className="p-4 bg-surface-container-high border-l-2 border-secondary">
            <p className="text-[11px] text-on-surface-variant leading-relaxed"><strong className="text-secondary uppercase block mb-1">Tactical Warning</strong>Payload injection is permanent once initiated. Ensure all encryption keys are synced with the KEY VAULT before execution.</p>
          </div>
          <button onClick={initiate} className="w-full py-4 bg-secondary text-on-secondary font-headline font-bold text-sm tracking-widest uppercase flex items-center justify-center gap-2 hover:opacity-90 active:scale-[0.98] transition-all">
            <span className="material-symbols-outlined">rocket_launch</span>INITIATE PAYLOAD
          </button>
          {batchId && (
            <div className="pt-4 border-t border-outline-variant/20">
              <div className="text-[10px] font-mono text-outline uppercase mb-1">ACTIVE_BATCH_ID</div>
              <div className="bg-black p-2 font-mono text-xs text-tertiary break-all">{batchId}</div>
            </div>
          )}
        </div>
      </section>

      {/* Stream Monitor */}
      <section className="flex-1 flex flex-col bg-background p-4 md:p-8 space-y-4">
        <div className="w-full bg-surface-container p-4 flex flex-col gap-3">
          <div className="flex justify-between items-end">
            <div className="flex flex-col">
              <span className="font-mono text-[10px] text-outline uppercase">MISSION_PROGRESS</span>
              <h2 className="font-headline font-bold text-xl text-primary">{batchId ? (progress===100 ? 'MISSION_COMPLETE' : 'UPLOADING_CORE_PAYLOAD') : 'AWAITING_LAUNCH'}</h2>
            </div>
            <div className="font-mono text-xl text-secondary">{progress.toFixed(1)}%</div>
          </div>
          <div className="h-1 w-full bg-surface-container-highest"><div className="h-full bg-secondary shadow-[0_0_10px_#f0cd2d]" style={{width:`${progress}%`}} /></div>
          <div className="flex justify-between text-[10px] font-mono text-outline"><span>EVENTS: {events.length}</span><span>{batchId ? 'STREAMING' : 'IDLE'}</span></div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 h-full overflow-hidden">
          <div className="md:col-span-2 bg-[#0b0f12] flex flex-col overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 border-b border-white/5">
              <div className="flex items-center gap-2"><div className="w-2 h-2 bg-secondary animate-pulse" /><span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest">LIVE_PAYLOAD_TRACKING</span></div>
              <span className="material-symbols-outlined text-outline text-sm">terminal</span>
            </div>
            <div className="flex-1 p-4 font-mono text-[11px] overflow-y-auto space-y-1">
              {events.map((e,i)=> (
                <div key={i} className="flex gap-4">
                  <span className="text-outline">{e.time}</span>
                  <span className={e.color}>{e.type.toUpperCase()}</span>
                  <span className="text-on-surface">{e.content}</span>
                </div>
              ))}
              {events.length===0 && <div className="text-outline/40">No active stream.</div>}
              <div className="animate-pulse flex gap-4"><span className="text-outline">{new Date().toLocaleTimeString()}</span><span className="text-tertiary">_</span></div>
            </div>
          </div>
          <div className="space-y-4 flex flex-col h-full">
            <div className="bg-surface-container p-4 flex flex-col gap-2">
              <span className="font-mono text-[10px] text-outline uppercase tracking-widest">REALTIME_VISUALIZER</span>
              <div className="aspect-video w-full bg-surface-container-highest relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-t from-background/80 to-transparent z-10" />
                <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_center,#aac7ff_0%,transparent_70%)]" />
                <div className="absolute top-2 left-2 flex gap-1 z-20"><div className="w-1 h-3 bg-tertiary" /><div className="w-1 h-3 bg-tertiary opacity-60" /><div className="w-1 h-3 bg-tertiary opacity-30" /></div>
              </div>
            </div>
            <div className="flex-1 bg-surface-container-low p-4 flex flex-col">
              <span className="font-mono text-[10px] text-outline uppercase tracking-widest mb-4">NODE_HEALTH</span>
              <div className="space-y-3">
                <HealthBar label="ENCRYPTION_LOAD" pct={22} color="bg-tertiary" />
                <HealthBar label="SIGNAL_INTEGRITY" pct={89} color="bg-secondary" />
                <HealthBar label="CPU_THERMALS" pct={42} color="bg-on-surface" />
              </div>
              <div className="mt-auto pt-4 flex gap-2">
                <button onClick={()=>{setBatchId(null); setEvents([]); setProgress(0);}} className="flex-1 bg-surface-container-highest py-2 text-[10px] font-mono font-bold uppercase hover:bg-surface-bright">RESET</button>
                <button className="flex-1 bg-surface-container-highest py-2 text-[10px] font-mono font-bold uppercase hover:bg-surface-bright">FREEZE</button>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
};

const HealthBar: React.FC<{label:string; pct:number; color:string}> = ({label,pct,color}) => (
  <div className="flex flex-col gap-1">
    <div className="flex justify-between text-[11px] font-mono"><span>{label}</span><span>{pct}%</span></div>
    <div className="h-1 bg-surface-container-highest w-full"><div className={`h-full ${color}`} style={{width:`${pct}%`}} /></div>
  </div>
);

export default LiveWire;
