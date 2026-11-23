import React from 'react';
import { StrikerAPI, StrikerFile, StrikerTelemetry } from '../lib/api';

const Striker: React.FC = () => {
  const [files, setFiles] = React.useState<StrikerFile[]>([]);
  const [status, setStatus] = React.useState<StrikerTelemetry | null>(null);
  const [selected, setSelected] = React.useState<Set<string>>(new Set());
  const [modelId, setModelId] = React.useState('llama-3.3-70b-versatile');
  const [prompt, setPrompt] = React.useState('Analyze the following payload and extract structured intel.');
  const [delay, setDelay] = React.useState(5);
  const [throttle, setThrottle] = React.useState(1.0);
  const [toast, setToast] = React.useState<string | null>(null);

  React.useEffect(() => {
    StrikerAPI.getFiles().then(setFiles);
    const iv = setInterval(() => {
      StrikerAPI.getStatus().then(setStatus);
      StrikerAPI.getFiles().then(setFiles);
    }, 3000);
    return () => clearInterval(iv);
  }, []);

  const showToast = (msg: string) => { setToast(msg); setTimeout(()=>setToast(null), 3000); };

  const toggleSelect = (path: string) => {
    const n = new Set(selected);
    n.has(path) ? n.delete(path) : n.add(path);
    setSelected(n);
  };

  const selectPending = () => {
    const pending = files.filter(f => f.status === 'pending').map(f => f.path);
    setSelected(new Set(pending));
  };

  const launch = async () => {
    if (selected.size === 0) { showToast('No files selected'); return; }
    try {
      await StrikerAPI.execute({ files: Array.from(selected), prompt, modelId, delay, throttle });
      showToast('STRIKE_INITIATED');
    } catch(e:any){ showToast(e.message); }
  };

  const missionRunning = status?.isRunning;

  return (
    <main className="pt-16 pb-8 h-[calc(100vh-64px-32px)] flex flex-col p-4 gap-4 overflow-hidden">
      {/* Radar */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-fit">
        <div className="lg:col-span-8 bg-surface-container-low p-4 flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <div className={`w-2 h-2 rounded-full ${missionRunning?'bg-tertiary animate-pulse':'bg-outline'} `} />
              <span className="font-headline font-bold text-lg tracking-tight uppercase">STRIKER_CORE_ACTIVE</span>
            </div>
            <div className="font-mono text-xs text-tertiary border border-tertiary/20 px-2 py-0.5 bg-tertiary/5">
              STATUS: <span className="text-tertiary">{missionRunning?'RUNNING':status?.isPaused?'PAUSED':'IDLE'}</span>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-surface-container p-3 border-l-2 border-tertiary"><div className="text-[10px] text-outline uppercase font-bold">Processed</div><div className="font-mono text-2xl text-primary">{status?.processedCount || 0}</div></div>
            <div className="bg-surface-container p-3 border-l-2 border-secondary"><div className="text-[10px] text-outline uppercase font-bold">Target Queue</div><div className="font-mono text-2xl text-secondary">{selected.size}</div></div>
            <div className="bg-surface-container p-3 border-l-2 border-error"><div className="text-[10px] text-outline uppercase font-bold">Total Count</div><div className="font-mono text-2xl text-error">{status?.totalCount || 0}</div></div>
            <div className="bg-surface-container p-3 border-l-2 border-primary"><div className="text-[10px] text-outline uppercase font-bold">RPM</div><div className="font-mono text-2xl text-primary">{(status?.rpm || 0).toFixed(1)}</div></div>
          </div>
          <div className="flex gap-2 mt-2">
            <button onClick={launch} disabled={missionRunning} className="flex-1 bg-primary-container text-on-primary-container py-3 font-headline font-bold text-xs tracking-widest uppercase hover:bg-primary transition-colors disabled:opacity-50 flex items-center justify-center gap-2"><span className="material-symbols-outlined text-sm">play_arrow</span>INITIATE</button>
            <button onClick={()=>StrikerAPI.pause().then(()=>showToast('PAUSED'))} disabled={!missionRunning} className="flex-1 bg-surface-container-high text-on-surface py-3 font-headline font-bold text-xs tracking-widest uppercase hover:bg-surface-bright transition-colors disabled:opacity-50 flex items-center justify-center gap-2"><span className="material-symbols-outlined text-sm">pause</span>PAUSE</button>
            <button onClick={()=>StrikerAPI.resume().then(()=>showToast('RESUMED'))} disabled={!status?.isPaused} className="flex-1 bg-surface-container-high text-on-surface py-3 font-headline font-bold text-xs tracking-widest uppercase hover:bg-surface-bright transition-colors disabled:opacity-50 flex items-center justify-center gap-2"><span className="material-symbols-outlined text-sm">refresh</span>RESUME</button>
            <button onClick={()=>StrikerAPI.abort().then(()=>showToast('ABORTED'))} disabled={!missionRunning} className="flex-1 bg-error-container text-on-error-container py-3 font-headline font-bold text-xs tracking-widest uppercase hover:opacity-80 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"><span className="material-symbols-outlined text-sm">cancel</span>ABORT</button>
          </div>
        </div>
        <div className="lg:col-span-4 bg-surface-container-low p-4 flex flex-col gap-3">
          <div className="text-xs font-headline font-bold text-outline uppercase tracking-widest">Current Target Intel</div>
          <div className="bg-surface-container p-4 flex flex-col gap-2">
            <div className="flex justify-between items-end"><span className="text-[10px] font-mono text-outline uppercase">Target_ID</span><span className="text-xs font-mono text-primary">{status?.currentFile || 'NONE'}</span></div>
            <div className="w-full bg-background h-1"><div className="bg-tertiary h-full" style={{width:`${status?.totalCount ? (status.processedCount/status.totalCount)*100 : 0}%`}} /></div>
            <div className="flex justify-between items-center text-[10px] font-mono text-outline"><span>LATENCY: 14MS</span><span>TTL: --:--:--</span></div>
          </div>
          <div className="flex-grow grid grid-cols-2 gap-2">
            <div className="bg-surface-container p-2 flex flex-col items-center justify-center border border-outline-variant/10"><span className="text-[9px] text-outline uppercase mb-1">Load</span><span className="font-mono text-lg text-primary">42%</span></div>
            <div className="bg-surface-container p-2 flex flex-col items-center justify-center border border-outline-variant/10"><span className="text-[9px] text-outline uppercase mb-1">Temp</span><span className="font-mono text-lg text-secondary">54°C</span></div>
          </div>
        </div>
      </section>

      {/* File Grid */}
      <section className="flex-grow flex flex-col gap-2 overflow-hidden">
        <div className="flex justify-between items-end px-2">
          <h2 className="font-headline font-bold text-outline uppercase text-xs tracking-widest">Intel_Cache_Registry</h2>
          <div className="flex gap-2">
            <button onClick={()=>setSelected(new Set(files.map(f=>f.path)))} className="text-[10px] font-mono text-primary hover:text-white">SELECT ALL</button>
            <button onClick={selectPending} className="text-[10px] font-mono text-primary hover:text-white">SELECT PENDING</button>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-1 overflow-y-auto pr-1">
          {files.map((f) => {
            const sel = selected.has(f.path);
            const pending = f.status === 'pending';
            return (
              <div key={f.path} onClick={()=>toggleSelect(f.path)} className={`bg-surface-container p-4 border-l-4 cursor-pointer hover:bg-surface-container-high transition-colors ${sel?'border-tertiary ring-1 ring-tertiary/30':pending?'border-secondary':'border-outline-variant'}`}>
                <div className="flex justify-between items-start mb-2">
                  <div className="font-mono text-xs text-on-surface truncate">{f.name}</div>
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${pending?'bg-secondary':'bg-emerald-500'}`} />
                    <span className={`material-symbols-outlined text-base transition-colors ${sel?'text-tertiary':'text-outline-variant/50'}`}>{sel?'check_box':'check_box_outline_blank'}</span>
                  </div>
                </div>
                <div className="flex justify-between items-end">
                  <div className="text-[10px] font-mono text-outline">{(f.size/1024).toFixed(1)} KB</div>
                  <div className="h-4 w-12 bg-background relative overflow-hidden">
                    <div className="absolute inset-0 bg-secondary/20" />
                    <div className="absolute inset-y-0 left-0 bg-secondary" style={{width:`${Math.min((f.signalIntensity||0)*10,100)}%`}} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Launch Console */}
      <section className="bg-surface-container-low p-6 flex flex-col gap-4 border-t-2 border-secondary">
        <div className="flex flex-col md:flex-row gap-6">
          <div className="flex-grow flex flex-col gap-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-headline font-bold text-outline uppercase tracking-widest">Model_Selector</label>
                <input value={modelId} onChange={e=>setModelId(e.target.value)} className="bg-surface-container-highest border-none text-on-surface font-mono text-sm h-10 px-3 focus:ring-2 focus:ring-secondary/50" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-headline font-bold text-outline uppercase tracking-widest">Delay_s</label>
                <input type="number" value={delay} onChange={e=>setDelay(Number(e.target.value))} className="bg-surface-container-highest border-none text-on-surface font-mono text-sm h-10 px-3 focus:ring-2 focus:ring-secondary/50" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-headline font-bold text-outline uppercase tracking-widest">Throttle</label>
                <input type="number" step="0.1" value={throttle} onChange={e=>setThrottle(Number(e.target.value))} className="bg-surface-container-highest border-none text-on-surface font-mono text-sm h-10 px-3 focus:ring-2 focus:ring-secondary/50" />
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] font-headline font-bold text-outline uppercase tracking-widest">Mission_Prompt_Template</label>
              <textarea value={prompt} onChange={e=>setPrompt(e.target.value)} className="bg-surface-container-highest border-none text-on-surface font-mono text-sm p-4 h-24 resize-none focus:ring-2 focus:ring-secondary/50 placeholder:text-outline/30" placeholder="ENTER INSTRUCTIONS FOR CORE PROCESSOR..." />
            </div>
          </div>
          <div className="w-full md:w-64 flex flex-col">
            <div className="flex-grow border-x border-outline-variant/10 p-4 mb-4 flex flex-col justify-center text-center">
              <div className="text-[10px] font-headline font-bold text-outline uppercase tracking-widest mb-1">Status Verification</div>
              <div className="text-tertiary font-mono text-lg font-bold">{missionRunning?'RUNNING':'READY_TO_LAUNCH'}</div>
              <div className="text-[9px] text-outline-variant mt-2 font-mono">ALL SYSTEMS NOMINAL</div>
            </div>
            <button onClick={launch} className="w-full bg-secondary text-on-secondary py-5 font-headline font-extrabold text-sm tracking-[0.2em] uppercase hover:brightness-110 active:opacity-90 transition-all flex items-center justify-center gap-3">
              <span className="material-symbols-outlined text-lg">bolt</span>LAUNCH MISSION
            </button>
          </div>
        </div>
      </section>
      {toast && <div className="fixed top-20 right-6 bg-surface-container-high border border-outline-variant px-4 py-3 text-sm font-mono z-[100]">{toast}</div>}
    </main>
  );
};

export default Striker;
