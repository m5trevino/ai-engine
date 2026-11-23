import React from 'react';
import { NeuralLinkAPI, ConversationItem, PeacockWS } from '../lib/api';

const NeuralLink: React.FC = () => {
  const [conversations, setConversations] = React.useState<ConversationItem[]>([]);
  const [messages, setMessages] = React.useState<{role:'user'|'assistant'; content:string; time:string; files?:string[]}[]>([]);
  const [input, setInput] = React.useState('');
  const [attached, setAttached] = React.useState<{name:string;path:string}[]>([]);
  const [models, setModels] = React.useState<Record<string, any[]>>({});
  const [selectedModel, setSelectedModel] = React.useState('llama-3.3-70b-versatile');
  const [sessionTokens, setSessionTokens] = React.useState(0);
  const [sessionCost, setSessionCost] = React.useState(0);
  const [sessionGateway, setSessionGateway] = React.useState('unknown');
  const [logs, setLogs] = React.useState<string[]>([]);
  const [useWS, setUseWS] = React.useState(false);
  const wsRef = React.useRef<WebSocket | null>(null);

  React.useEffect(() => {
    NeuralLinkAPI.listConversations().then(setConversations);
    NeuralLinkAPI.getChatModels().then((d) => { setModels(d); });
  }, []);

  React.useEffect(() => {
    const payload = messages.map(m => ({ role: m.role, content: m.content }));
    NeuralLinkAPI.getSessionContext(selectedModel, payload, useWS ? 1 : 0).then((ctx) => {
      setSessionTokens(ctx.tokens);
      setSessionCost(ctx.cost);
      setSessionGateway(ctx.gateway);
    }).catch(() => {});
  }, [messages, selectedModel, useWS]);

  const addLog = (msg: string) => setLogs((p) => [msg, ...p].slice(0, 50));

  const handleSend = () => {
    if (!input.trim()) return;
    const userMsg = { role: 'user' as const, content: input, time: new Date().toLocaleTimeString(), files: attached.map(a=>a.path) };
    setMessages((m) => [...m, userMsg]);
    setInput('');

    if (useWS) {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        wsRef.current = PeacockWS.connect(selectedModel, 0.7);
        wsRef.current.onmessage = (ev) => {
          try {
            const data = JSON.parse(ev.data);
            if (data.type === 'content') {
              setMessages((m) => {
                const last = m[m.length-1];
                if (last && last.role === 'assistant') {
                  return [...m.slice(0,-1), { ...last, content: last.content + data.content }];
                }
                return [...m, { role: 'assistant' as const, content: data.content, time: new Date().toLocaleTimeString() }];
              });
            } else if (data.type === 'metadata') {
              addLog(`[DONE] tokens=${JSON.stringify(data.usage)}`);
            }
          } catch {}
        };
      }
      setTimeout(() => wsRef.current?.send(JSON.stringify({ type: 'prompt', content: userMsg.content })), 300);
    } else {
      NeuralLinkAPI.streamChat({ message: userMsg.content, model: selectedModel, temperature: 0.7, files: userMsg.files }, (ev: any) => {
        if (ev.event === 'start') {
          setMessages((m) => [...m, { role: 'assistant', content: '', time: new Date().toLocaleTimeString() }]);
        } else if (ev.event === 'token') {
          setMessages((m) => {
            const last = m[m.length-1];
            if (last && last.role === 'assistant') return [...m.slice(0,-1), { ...last, content: last.content + ev.content }];
            return m;
          });
        } else if (ev.event === 'done') {
          addLog(`[DONE] duration=${ev.duration_ms}ms tokens=${ev.usage?.total_tokens}`);
        }
      });
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const res = await NeuralLinkAPI.uploadFile(file);
    setAttached((a) => [...a, { name: res.filename, path: res.path }]);
    addLog(`[UPLOAD] ${res.filename}`);
  };

  return (
    <main className="pt-16 pb-8 h-[calc(100vh-64px-32px)] flex overflow-hidden">
      {/* Left */}
      <aside className="w-64 bg-surface-container-low border-r border-outline-variant/10 flex flex-col shrink-0">
        <div className="p-4">
          <button onClick={() => NeuralLinkAPI.createConversation(selectedModel).then((c)=>{ setConversations(p=>[...p,{id:c.conversation_id,title:c.conversation_id,model:c.model,message_count:0,updated_at:Date.now()/1000,preview:''}]); })} className="w-full bg-secondary text-on-secondary font-label font-bold py-3 flex items-center justify-center gap-2 hover:opacity-90 transition-opacity">
            <span className="material-symbols-outlined text-sm">add</span>
            <span>+ NEW</span>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-2 space-y-1">
          <div className="text-[10px] font-mono text-outline uppercase px-2 mb-2 tracking-widest">Operation_History</div>
          {conversations.map((c, i) => (
            <button key={c.id} className={`w-full text-left p-3 border-l-2 group flex items-start gap-3 ${i===0?'bg-surface-container-high border-secondary':'border-transparent hover:bg-surface-container'}`}>
              <span className={`material-symbols-outlined text-sm ${i===0?'text-secondary':'text-outline group-hover:text-primary'}`}>chat_bubble</span>
              <div className="flex-1 min-w-0">
                <div className="text-[11px] font-mono text-on-surface-variant truncate">{c.title}</div>
                <div className="text-[10px] text-outline truncate">{c.preview || 'New chat'}</div>
              </div>
            </button>
          ))}
        </div>
      </aside>

      {/* Center */}
      <section className="flex-1 flex flex-col bg-background relative">
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="flex items-center justify-center">
            <span className="text-[10px] font-mono px-4 py-1 bg-surface-container-high text-outline-variant uppercase tracking-[0.2em]">Neural_Link_Established // Secure_Channel_7</span>
          </div>
          {messages.map((m, i) => (
            <div key={i} className={`flex flex-col max-w-[85%] ${m.role==='user'?'items-end ml-auto':'items-start'}`}>
              <div className="flex items-center gap-2 mb-1 px-1">
                {m.role==='assistant' ? (
                  <><span className="text-[9px] font-mono text-tertiary">ASSISTANT_V3</span><span className="text-[9px] font-mono text-outline/40">{m.time}</span></>
                ) : (
                  <><span className="text-[9px] font-mono text-outline/40">{m.time}</span><span className="text-[9px] font-mono text-primary">OPERATOR</span></>
                )}
              </div>
              <div className={`${m.role==='user'?'bg-surface-container-high border border-primary/20 text-primary':'bg-surface-container-low border border-tertiary/30 text-on-surface'} p-4 text-sm leading-relaxed whitespace-pre-wrap`}>
                {m.content}
              </div>
            </div>
          ))}
        </div>

        <div className="p-4 border-t border-outline-variant/10 bg-surface-container-low">
          <div className="flex gap-2 mb-3 overflow-x-auto pb-1">
            {attached.map((f, i) => (
              <div key={i} className="flex items-center gap-2 px-2 py-1 bg-surface-container-high border border-outline-variant/30 text-[10px] font-mono text-primary shrink-0">
                <span className="material-symbols-outlined text-xs">description</span>
                <span>{f.name}</span>
                <button onClick={()=>setAttached(a=>a.filter((_,idx)=>idx!==i))} className="material-symbols-outlined text-xs hover:text-error">close</button>
              </div>
            ))}
          </div>
          <div className="relative bg-background border-b-2 border-outline-variant focus-within:border-secondary transition-colors p-3">
            <textarea value={input} onChange={(e)=>setInput(e.target.value)} onKeyDown={(e)=>{if(e.key==='Enter' && !e.shiftKey){e.preventDefault();handleSend();}}} className="w-full bg-transparent border-none focus:ring-0 text-sm resize-none h-20 font-body placeholder:text-outline/40" placeholder="Awaiting operational command..." />
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-outline-variant/10">
              <div className="flex items-center gap-1">
                <label className="p-2 hover:bg-surface-container text-outline hover:text-primary transition-colors cursor-pointer">
                  <span className="material-symbols-outlined text-xl">attach_file</span>
                  <input type="file" className="hidden" onChange={handleUpload} />
                </label>
                <button className="p-2 hover:bg-surface-container text-outline hover:text-primary transition-colors"><span className="material-symbols-outlined text-xl">add_photo_alternate</span></button>
                <button className="p-2 hover:bg-surface-container text-outline hover:text-primary transition-colors"><span className="material-symbols-outlined text-xl">mic</span></button>
                <label className="flex items-center gap-1 ml-2 text-[10px] text-outline cursor-pointer">
                  <input type="checkbox" checked={useWS} onChange={(e)=>setUseWS(e.target.checked)} className="accent-secondary" />
                  WS MODE
                </label>
              </div>
              <button onClick={handleSend} className="bg-primary text-on-primary-fixed px-6 py-2 font-label font-bold text-xs uppercase tracking-widest hover:opacity-90">SEND PROMPT</button>
            </div>
          </div>
        </div>
      </section>

      {/* Right */}
      <aside className="w-80 bg-surface-container border-l border-outline-variant/10 flex flex-col shrink-0">
        <div className="p-4 space-y-4">
          <div className="text-[10px] font-mono text-outline uppercase tracking-widest">Session_Context</div>
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-surface-container-low p-3 space-y-1">
              <div className="text-[9px] font-mono text-outline">LOADED_TOKENS</div>
              <div className="text-xl font-mono text-primary">{sessionTokens}</div>
            </div>
            <div className="bg-surface-container-low p-3 space-y-1">
              <div className="text-[9px] font-mono text-outline">SESSION_COST</div>
              <div className="text-xl font-mono text-secondary">${sessionCost.toFixed(2)}</div>
            </div>
          </div>
          <div className="bg-surface-container-low">
            <div className="px-3 py-2 border-b border-outline-variant/10 text-[9px] font-mono text-outline uppercase">Active_Objects</div>
            <div className="divide-y divide-outline-variant/5">
              <div className="p-3 flex items-center justify-between"><div className="flex items-center gap-2"><div className="w-1.5 h-1.5 bg-tertiary" /><span className="text-[11px] font-mono">CHAT_STREAM</span></div><span className="text-[9px] font-mono text-outline">{useWS ? 'WS_ACTIVE' : 'REST_ACTIVE'}</span></div>
              <div className="p-3 flex items-center justify-between"><div className="flex items-center gap-2"><div className="w-1.5 h-1.5 bg-secondary" /><span className="text-[11px] font-mono">GATEWAY_LINK</span></div><span className="text-[9px] font-mono text-outline uppercase">{sessionGateway}</span></div>
            </div>
          </div>
          <div className="flex-1 flex flex-col min-h-0 bg-black p-3 font-mono text-[10px] text-tertiary leading-tight border border-outline-variant/20 h-48 overflow-y-auto">
            {logs.length===0 && <div className="text-outline/40">[IDLE] Waiting for input...</div>}
            {logs.map((l,i)=>(<div key={i} className="mb-1">{l}</div>))}
            <div className="animate-pulse">_</div>
          </div>
        </div>
      </aside>
    </main>
  );
};

export default NeuralLink;
