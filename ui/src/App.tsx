/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from 'react';
import { 
  Zap,
  Bell, 
  Settings, 
  PlusCircle as AddCircle, 
  FileText, 
  Image as ImageIcon, 
  Paperclip as AttachFile, 
  ImagePlus as AddPhotoAlternate, 
  Mic, 
  BarChart3 as Analytics, 
  Database, 
  Terminal, 
  Maximize2 as OpenInFull, 
  Cpu, 
  Puzzle as Extension, 
  Network as Hub, 
  ExternalLink as OpenInNew,
  Shield, 
  UserCog,
  Search,
  Plus as Add,
  Copy as ContentCopy,
  Brain as Psychology,
  Coins as Token,
  DollarSign as MonetizationOn,
  Map as MapIcon,
  Calculator as Calculate,
  Code2 as CodeBlocks,
  Share2 as Schema,
  X as Close,
  HelpCircle as HelpOutline,
  BookOpen as MenuBook,
  CreditCard as Payments,
  Activity,
  Target,
  SlidersHorizontal,
  ArrowRight,
  Layers,
  Server,
  Lock,
  ChevronRight,
  ChevronLeft,
  Eye,
  ArrowLeft,
  Check,
  Folder
} from 'lucide-react';

const Bolt = Zap;
const Memory = Cpu;
const DataObject = Database;
const AdminPanelSettings = UserCog;
const FileTextIcon = FileText;
const Description = FileText;

import { motion, AnimatePresence } from 'framer-motion';
import { PeacockAPI, PeacockWS, type ModelConfig, type KeyTelemetry } from './lib/api';
import { SequenceOrchestrator, type StrikeSlot } from './lib/SequenceOrchestrator';

type Screen = 'DASHBOARD' | 'STRIKER' | 'ANALYTICS' | 'LOGS' | 'DEPLOYMENT' | 'SYSTEM';
type SubScreen = 'ENGINE_STATUS' | 'CORE_MODULES' | 'NETWORK_MESH' | 'STORAGE_NODES' | 'SECURITY_PROTOCOL' | 'SYSTEM_ADMIN';

export default function App() {
  const [activeScreen, setActiveScreen] = useState<Screen>('DASHBOARD');
  const [activeSubScreen, setActiveSubScreen] = useState<SubScreen>('CORE_MODULES');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);
  const [models, setModels] = useState<Record<string, ModelConfig[]>>({});
  const [selectedModel, setSelectedModel] = useState("gemini-1.5-flash");
  const [keys, setKeys] = useState<KeyTelemetry[]>([]);
  const [sessionUsage, setSessionUsage] = useState({ tokens: 142200, cost: 4.82 });
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(true);
  const [genSettings, setGenSettings] = useState({
    temp: 0.7,
    top_p: 1.0,
    maxTokens: 2048,
    system: "You are the Peacock Engine, a high-performance AI orchestration unit."
  });
  
  const [telemetry, setTelemetry] = useState({ tps: 0, rpm: 0 });
  const modelMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const init = async () => {
      try {
        const modelData = await PeacockAPI.getModels();
        setModels(modelData);
        const keyData = await PeacockAPI.getKeyUsage();
        setKeys(keyData);
      } catch (e) {}
    };
    init();
  }, []);

  return (
    <div className="flex flex-col h-screen bg-background text-on-surface font-body overflow-hidden">
      <header className="bg-surface-container-low h-16 w-full flex items-center z-50 px-6 justify-between shrink-0">
        <div className="flex items-center gap-8">
          <span className="text-primary font-headline text-xl font-bold tracking-tighter uppercase cursor-pointer" onClick={() => setActiveScreen('DASHBOARD')}>PEACOCK ENGINE</span>
          <nav className="hidden md:flex items-center h-full gap-2">
            {(['DASHBOARD', 'STRIKER', 'ANALYTICS', 'LOGS', 'DEPLOYMENT'] as Screen[]).map((screen) => (
              <button
                key={screen}
                onClick={() => setActiveScreen(screen)}
                className={`h-16 flex items-center px-4 font-headline font-medium tracking-tighter uppercase transition-all border-b-2 ${
                  activeScreen === screen ? 'text-primary border-primary' : 'text-gray-400 border-transparent hover:text-primary'
                }`}
              >
                {screen === 'STRIKER' ? 'REFINERY' : screen}
              </button>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-6">
           <div className="relative" ref={modelMenuRef}>
             <button onClick={() => setIsModelMenuOpen(!isModelMenuOpen)} className="bg-surface-container flex items-center gap-3 px-4 py-2 hover:bg-surface-bright transition-all border border-outline-variant/10">
               <Zap className="text-secondary w-4 h-4" />
               <span className="font-label text-xs tracking-widest uppercase">{selectedModel}</span>
               <Settings className="w-3 h-3" />
             </button>
           </div>
           <div className="flex items-center gap-4">
              <Activity className="w-5 h-5 text-secondary" />
           </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <aside className="w-64 bg-surface-container-low shrink-0 flex flex-col border-r border-outline-variant/10">
          <nav className="flex-1 py-4 overflow-y-auto space-y-1">
            <SidebarItem icon={<Memory className="w-4 h-4" />} label="Refinery Core" active={activeScreen === 'STRIKER'} onClick={() => setActiveScreen('STRIKER')} />
            <SidebarItem icon={<Analytics className="w-4 h-4" />} label="Analytics" active={activeScreen === 'ANALYTICS'} onClick={() => setActiveScreen('ANALYTICS')} />
            <SidebarItem icon={<Terminal className="w-4 h-4" />} label="Logs" active={activeScreen === 'LOGS'} onClick={() => setActiveScreen('LOGS')} />
          </nav>
          <div className="p-6 mt-auto">
            <button onClick={() => setActiveScreen('STRIKER')} className="w-full bg-secondary text-on-secondary py-3 text-[10px] font-bold tracking-[0.2em] uppercase gold-glow">
              LAUNCH REFINERY
            </button>
          </div>
        </aside>

        <main className="flex-1 flex flex-col relative bg-background overflow-hidden">
          <AnimatePresence mode="wait">
            {activeScreen === 'DASHBOARD' && <Dashboard key="dash" selectedModel={selectedModel} genSettings={genSettings} setGenSettings={setGenSettings} />}
            {activeScreen === 'STRIKER' && <PayloadStrikerScreen key="striker" selectedModel={selectedModel} genSettings={genSettings} />}
            {activeScreen === 'ANALYTICS' && <AnalyticsScreen key="analytics" keys={keys} />}
            {activeScreen === 'LOGS' && <LogsScreen key="logs" models={models} selectedModel={selectedModel} setSelectedModel={setSelectedModel} onOpenModal={() => setIsModalOpen(true)} />}
            {activeScreen === 'DEPLOYMENT' && <DeploymentScreen key="deployment" />}
            {activeScreen === 'SYSTEM' && <SystemScreen key="system" subScreen={activeSubScreen} />}
          </AnimatePresence>
        </main>
      </div>

      <footer className="bg-surface-container-lowest h-8 w-full shrink-0 flex items-center justify-between px-4 z-50 border-t border-outline-variant/10">
        <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00C851] gold-glow"></span>
            <span className="font-mono text-[10px] text-secondary uppercase tracking-[0.2em]">OPERATOR-01_ONLINE</span>
        </div>
        <span className="font-mono text-[10px] text-outline-variant uppercase tracking-widest">PEACOCK ENGINE v4.2.0-STABLE</span>
      </footer>
    </div>
  );
}

function SidebarItem({ icon, label, active, onClick }: any) {
  return (
    <button onClick={onClick} className={`w-full flex items-center gap-4 px-6 py-3 transition-all ${active ? 'bg-secondary/10 text-secondary border-r-2 border-secondary' : 'text-outline hover:bg-surface-bright hover:text-on-surface'}`}>
      {icon}
      <span className="text-xs font-label uppercase tracking-widest">{label}</span>
    </button>
  );
}

function Dashboard({ selectedModel, genSettings, setGenSettings }: any) {
  return (
    <div className="p-8 space-y-8 overflow-y-auto no-scrollbar flex-1">
       <div className="flex justify-between items-end border-b border-outline-variant/20 pb-6">
          <h1 className="text-4xl font-headline font-bold text-white tracking-tighter">ENGINE_DASHBOARD</h1>
          <div className="text-right">
             <div className="text-[10px] text-outline uppercase tracking-[0.3em]">ACTIVE_MODEL</div>
             <div className="text-xl font-headline text-secondary font-black">{selectedModel}</div>
          </div>
       </div>
       <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-surface-container p-6 border-l-2 border-primary">
             <div className="text-[10px] text-outline uppercase mb-2">Throughput</div>
             <div className="text-3xl font-headline text-white">1.2M <span className="text-xs text-outline">TOKENS</span></div>
          </div>
          <div className="bg-surface-container p-6 border-l-2 border-secondary">
             <div className="text-[10px] text-outline uppercase mb-2">System Load</div>
             <div className="text-3xl font-headline text-white">42%</div>
          </div>
          <div className="bg-surface-container p-6 border-l-2 border-[#00C851]">
             <div className="text-[10px] text-outline uppercase mb-2">Architectural Integrity</div>
             <div className="text-3xl font-headline text-[#00C851]">99.8%</div>
          </div>
       </div>
    </div>
  );
}

function PayloadStrikerScreen({ selectedModel, genSettings }: any) {
  const [molds, setMolds] = useState<any[]>([]);
  const [activeMold, setActiveMold] = useState<any | null>(null);
  const [legoData, setLegoData] = useState<any>({ items: [], current: '', parent: null });
  const [selectedLegos, setSelectedLegos] = useState<string[]>([]);
  const [processingLegos, setProcessingLegos] = useState<Record<string, { status: 'PENDING' | 'DONE' | 'ERROR', result?: string }>>({});
  const [forensicsFile, setForensicsFile] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      try {
        const m = await PeacockAPI.getMolds();
        setMolds(m);
        const l = await PeacockAPI.browseLegos();
        setLegoData(l);
      } catch (e) {} finally { setIsLoading(false); }
    };
    init();
  }, []);

  const handleBrowse = async (path: string) => {
    setIsLoading(true);
    try {
      const l = await PeacockAPI.browseLegos(path);
      setLegoData(l);
    } catch (e) {} finally { setIsLoading(false); }
  };

  const toggleLegoSelection = (path: string) => {
    if (selectedLegos.includes(path)) setSelectedLegos(selectedLegos.filter(p => p !== path));
    else setSelectedLegos([...selectedLegos, path]);
  };

  const startRefinerySequence = async () => {
    if (!activeMold || selectedLegos.length === 0) return;
    const initStatus: Record<string, any> = {};
    selectedLegos.forEach(p => { initStatus[p] = { status: 'PENDING' }; });
    setProcessingLegos(initStatus);
    try {
      const data = await PeacockAPI.processStrike(activeMold.path, selectedLegos, selectedModel);
      if (data.status === 'REFINERY_SEQUENCE_COMPLETE') {
         const finalStatus: Record<string, any> = {};
         data.cast_results.forEach((res: any) => {
            // Find the original path based on the filename (since backend returns lego name)
            const originalPath = selectedLegos.find(p => p.endsWith(res.lego)) || res.lego;
            finalStatus[originalPath] = { 
               status: res.status === 'SUCCESS' ? 'DONE' : 'ERROR', 
               result: res.status === 'SUCCESS' 
                  ? `[INVARIANT_CAST_SUCCESS]\nROOT_MANIFEST: ${res.lego}\nOUTPUT_PATH: ${res.invariant_path}\nSIGNAL_STRENGTH: 0.998\nSTAMP: ${new Date().toISOString()}`
                  : `[STRIKE_FAILURE]\nREASON: ${res.error || 'Unknown'}`
            };
         });
         setProcessingLegos(finalStatus);
      }
    } catch (e) {
      console.error("[Refinery] Execution Error:", e);
      setProcessingLegos(prev => {
        const next = { ...prev };
        selectedLegos.forEach(p => { if (next[p].status === 'PENDING') next[p].status = 'ERROR'; });
        return next;
      });
    }
  };

  const openForensics = async (item: any) => {
    try {
      const content = await PeacockAPI.getRefineryFile(item.path);
      setForensicsFile({ ...item, content });
    } catch (e) {}
  };

  return (
    <div className="flex-1 flex overflow-hidden bg-[#0b0f12]">
      {/* PANE 1: DIRECTOR */}
      <div className="w-80 border-r border-outline-variant/10 flex flex-col bg-surface-container-low">
        <div className="p-4 border-b border-outline-variant/10 flex justify-between items-center bg-surface-container-low">
          <h3 className="font-headline text-[10px] font-bold tracking-[0.2em] text-secondary uppercase">1. DIRECTOR</h3>
          <span className="font-mono text-[9px] text-outline">v{molds.length}</span>
        </div>
        <div className="flex-1 overflow-y-auto no-scrollbar p-2 space-y-1">
          {molds.map((m) => (
            <div key={m.path} onClick={() => setActiveMold(m)} className={`p-3 cursor-pointer transition-all border-l-2 flex justify-between items-center group ${activeMold?.path === m.path ? 'bg-secondary/10 border-secondary text-secondary' : 'border-transparent hover:bg-surface-bright text-outline'}`}>
              <span className="text-[10px] font-bold tracking-tight uppercase truncate">{m.name.replace('.txt', '')}</span>
              <Eye onClick={(e) => { e.stopPropagation(); openForensics(m); }} className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100" />
            </div>
          ))}
        </div>
      </div>

      {/* PANE 2: STAGING */}
      <div className="w-96 border-r border-outline-variant/10 flex flex-col bg-background">
        <div className="p-4 border-b border-outline-variant/10 flex justify-between items-center bg-background">
          <h3 className="font-headline text-[10px] font-bold tracking-[0.2em] text-primary uppercase flex items-center gap-2"><Layers className="w-3 h-3" /> 2. STAGING</h3>
          <div className="flex gap-2">
            {legoData?.parent && <ArrowLeft onClick={() => handleBrowse(legoData.parent)} className="w-3.5 h-3.5 hover:text-primary cursor-pointer" />}
            <button onClick={() => setSelectedLegos(legoData.items.filter((i:any)=>i.type==='file').map((i:any)=>i.path))} className="text-[9px] font-bold text-outline border border-outline-variant/30 px-2">ALL</button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto no-scrollbar">
          {isLoading ? <div className="p-12 text-center text-[10px] text-outline animate-pulse uppercase tracking-widest">STABILIZING...</div> : 
            legoData?.items?.map((item: any) => (
              <div key={item.path} className="group border-b border-outline-variant/5 hover:bg-surface-container transition-all flex items-center px-4 py-3 gap-3">
                {item.type === 'directory' ? <Folder className="w-4 h-4 text-secondary/40" /> : 
                  <div onClick={() => toggleLegoSelection(item.path)} className={`w-4 h-4 border flex items-center justify-center cursor-pointer ${selectedLegos.includes(item.path) ? 'bg-primary border-primary' : 'border-outline-variant/50'}`}>
                    {selectedLegos.includes(item.path) && <Check className="w-3 h-3 text-on-primary" />}
                  </div>
                }
                <div className="flex-1 min-w-0" onClick={() => item.type === 'directory' ? handleBrowse(item.path) : toggleLegoSelection(item.path)}>
                  <div className={`text-[11px] font-medium truncate ${item.type === 'directory' ? 'text-on-surface' : 'text-on-surface-variant group-hover:text-primary'}`}>{item.name}</div>
                  {item.size && <div className="text-[9px] text-outline font-mono">{(item.size / 1024).toFixed(1)} KB</div>}
                </div>
                {item.type === 'file' && <Eye onClick={() => openForensics(item)} className="opacity-0 group-hover:opacity-100 p-1 text-outline hover:text-white transition-opacity w-6 h-6" />}
              </div>
            ))
          }
        </div>
      </div>

      {/* PANE 3: ACTIVE STRIKE */}
      <div className="flex-1 flex flex-col border-r border-outline-variant/10 bg-[#0a0f13]">
        <div className="p-4 border-b border-outline-variant/10 flex justify-between items-center bg-surface-container-low shadow-lg">
          <h3 className="font-headline text-[10px] font-bold tracking-[0.2em] text-[#ffdb3c] uppercase flex items-center gap-2"><Zap className="w-3 h-3 fill-current" /> 3. ACTIVE STRIKE</h3>
          <button onClick={startRefinerySequence} disabled={!activeMold || selectedLegos.length === 0} className={`px-8 py-3 bg-[#ffdb3c] text-[#0c305f] font-headline font-bold text-[10px] tracking-widest gold-glow transition-all active:scale-95 ${(!activeMold || selectedLegos.length === 0) ? 'opacity-30 grayscale cursor-not-allowed' : 'hover:opacity-90'}`}>EXECUTE LIM SECURITY PROTOCOL</button>
        </div>
        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 border-r border-outline-variant/5 flex flex-col overflow-hidden bg-[#101418]">
             <div className="px-5 py-3 bg-surface-container-highest/20 text-[10px] font-bold text-outline tracking-[0.25em] border-b border-outline-variant/10 flex justify-between items-center"><span>BOX 1: PRIMITIVES</span></div>
             <div className="flex-1 overflow-y-auto p-4 space-y-3 no-scrollbar focus-rings">
                {selectedLegos.map(path => (
                    <motion.div key={path} className={`p-4 border border-outline-variant/10 bg-[#181c20] ${processingLegos[path]?.status === 'PENDING' ? 'border-[#ffdb3c]/40 bg-[#ffdb3c]/5' : processingLegos[path]?.status === 'DONE' ? 'border-[#00C851]/40 bg-[#00C851]/5' : ''}`}>
                       <div className="flex justify-between items-center mb-1">
                          <span className="text-[11px] font-bold text-white uppercase truncate">{path.split('/').pop()}</span>
                          <span className={`text-[8px] font-bold px-2 py-0.5 tracking-tighter ${processingLegos[path]?.status === 'PENDING' ? 'bg-[#ffdb3c] text-black animate-pulse' : processingLegos[path]?.status === 'DONE' ? 'bg-[#00C851] text-white' : 'bg-outline-variant/30 text-outline'}`}>{processingLegos[path]?.status || 'STAGED'}</span>
                       </div>
                    </motion.div>
                ))}
             </div>
          </div>
          <div className="flex-1 flex flex-col overflow-hidden bg-surface-container-lowest/20">
             <div className="px-5 py-3 bg-surface-container-highest/20 text-[10px] font-bold text-outline tracking-[0.25em] border-b border-outline-variant/10 flex justify-between items-center"><span>BOX 2: INVARIANTS</span></div>
             <div className="flex-1 overflow-y-auto p-4 space-y-4 no-scrollbar">
                {selectedLegos.map(path => processingLegos[path]?.result && (
                    <motion.div key={`out-${path}`} className="p-5 bg-[#181c20] border-l-2 border-secondary/50 shadow-xl">
                       <div className="flex justify-between items-center mb-3 text-[10px] text-secondary font-bold uppercase tracking-widest">CAST_COMPLETE</div>
                       <div className="text-[12px] text-on-surface font-mono leading-relaxed bg-black/20 p-3">{processingLegos[path].result}</div>
                    </motion.div>
                ))}
             </div>
          </div>
        </div>
      </div>

      {/* FORENSICS MODAL */}
      <AnimatePresence>
        {forensicsFile && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#0b0f12]/90 backdrop-blur-lg p-12">
             <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="w-full max-w-6xl h-full bg-[#181c20] border border-primary/20 shadow-2xl flex flex-col relative">
                <div className="px-8 py-6 border-b border-outline-variant/10 flex justify-between items-center bg-[#1c2024]">
                   <h4 className="text-primary font-headline text-xl font-bold tracking-tighter uppercase">CORE MODE FORENSICS</h4>
                   <Close onClick={() => setForensicsFile(null)} className="w-6 h-6 cursor-pointer hover:bg-white/5" />
                </div>
                <div className="flex-1 overflow-y-auto p-8 custom-scrollbar bg-black/40 text-[13px] font-mono text-[#aac7ff]/90 whitespace-pre-wrap">{forensicsFile.content}</div>
                <div className="p-6 bg-[#1c2024] border-t border-outline-variant/10 flex justify-end gap-4">
                   <button onClick={() => setForensicsFile(null)} className="px-8 py-3 text-[10px] font-bold tracking-widest text-outline border border-outline-variant/20 uppercase">TERMINATE</button>
                   {forensicsFile.type === 'file' && !selectedLegos.includes(forensicsFile.path) && (
                     <button onClick={() => { toggleLegoSelection(forensicsFile.path); setForensicsFile(null); }} className="px-10 py-3 bg-primary text-on-primary text-[10px] font-bold tracking-widest gold-glow uppercase">INITIALIZE_STAGING</button>
                   )}
                </div>
             </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

function SystemScreen({ subScreen }: any) { return <div className="p-8 text-white uppercase tracking-widest font-headline">System Screen: {subScreen}</div>; }
function AnalyticsScreen({ keys }: any) { return <div className="p-8 text-white uppercase tracking-widest font-headline">Analytics Screen</div>; }
function LogsScreen({ models, selectedModel, setSelectedModel, onOpenModal }: any) { return <div className="p-8 text-white uppercase tracking-widest font-headline">Logs Screen</div>; }
function DeploymentScreen() { return <div className="p-8 text-white uppercase tracking-widest font-headline">Deployment Screen</div>; }
function CustomToolModal({ onClose }: any) { return null; }
