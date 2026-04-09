/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from 'react';
import { 
  Bolt, 
  Bell as NotificationsActive, 
  Settings, 
  PlusCircle as AddCircle, 
  FileText as Description, 
  Image as ImageIcon, 
  Paperclip as AttachFile, 
  ImagePlus as AddPhotoAlternate, 
  Mic, 
  BarChart3 as Analytics, 
  Database as DataObject, 
  Terminal, 
  Maximize2 as OpenInFull, 
  Cpu as Memory, 
  Puzzle as Extension, 
  Network as Hub, 
  Database, 
  Shield, 
  UserCog as AdminPanelSettings,
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
  ExternalLink as OpenInNew,
  X as Close,
  HelpCircle as HelpOutline,
  BookOpen as MenuBook,
  CreditCard as Payments,
  Send,
  Cpu,
  Activity,
  Layers,
  Server,
  Lock,
  UserCog
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { PeacockAPI, PeacockWS, type ModelConfig, type KeyTelemetry } from './lib/api';

type Screen = 'DASHBOARD' | 'ANALYTICS' | 'LOGS' | 'DEPLOYMENT' | 'SYSTEM';
type SubScreen = 'ENGINE_STATUS' | 'CORE_MODULES' | 'NETWORK_MESH' | 'STORAGE_NODES' | 'SECURITY_PROTOCOL' | 'SYSTEM_ADMIN';

interface Message {
  role: 'user' | 'model';
  content: string;
  time: string;
}

export default function App() {
  const [activeScreen, setActiveScreen] = useState<Screen>('DASHBOARD');
  const [activeSubScreen, setActiveSubScreen] = useState<SubScreen>('CORE_MODULES');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);
  const [models, setModels] = useState<Record<string, ModelConfig[]>>({});
  const [selectedModel, setSelectedModel] = useState("gemini-2.0-flash-lite");
  const [keys, setKeys] = useState<KeyTelemetry[]>([]);
  const [sessionUsage, setSessionUsage] = useState({ tokens: 142200, cost: 4.82 });
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(true);
  const [genSettings, setGenSettings] = useState({
    temp: 0.7,
    top_p: 1.0,
    maxTokens: 2048,
    system: "You are the Peacock Engine, a high-performance AI orchestration unit. Maintain precision and industrial-grade logic."
  });
  const modelMenuRef = useRef<HTMLDivElement>(null);

  // Initial Data Load
  useEffect(() => {
    const init = async () => {
      try {
        const modelData = await PeacockAPI.getModels();
        setModels(modelData);
        
        const keyData = await PeacockAPI.getKeyUsage();
        setKeys(keyData);
      } catch (e) {
        console.error("Failed to load initial engine data", e);
      }
    };
    init();

    // Refresh telemetry every 30s
    const timer = setInterval(async () => {
      try {
        const keyData = await PeacockAPI.getKeyUsage();
        setKeys(keyData);
      } catch (e) {}
    }, 30000);

    return () => clearInterval(timer);
  }, []);

  // Close model menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (modelMenuRef.current && !modelMenuRef.current.contains(event.target as Node)) {
        setIsModelMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [modelMenuRef]);

  const handleSubScreenClick = (sub: SubScreen) => {
    setActiveSubScreen(sub);
    setActiveScreen('SYSTEM');
  };

  return (
    <div className="flex flex-col h-screen bg-background text-on-surface font-body overflow-hidden">
      {/* Top Navigation */}
      <header className="bg-surface-container-low h-16 w-full flex items-center z-50 px-6 justify-between shrink-0">
        <div className="flex items-center gap-8">
          <span className="text-primary font-headline text-xl font-bold tracking-tighter uppercase cursor-pointer" onClick={() => setActiveScreen('DASHBOARD')}>PEACOCK ENGINE</span>
          <nav className="hidden md:flex items-center h-full gap-2">
            {(['DASHBOARD', 'ANALYTICS', 'LOGS', 'DEPLOYMENT'] as Screen[]).map((screen) => (
              <button
                key={screen}
                onClick={() => setActiveScreen(screen)}
                className={`h-16 flex items-center px-4 font-headline font-medium tracking-tighter uppercase transition-all border-b-2 ${
                  activeScreen === screen ? 'text-primary border-primary' : 'text-gray-400 border-transparent hover:text-primary'
                }`}
              >
                {screen}
              </button>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-6">
          <div className="relative" ref={modelMenuRef} style={{ zIndex: 9999 }}>
            <button 
              onClick={(e: React.MouseEvent) => {
                e.stopPropagation();
                setIsModelMenuOpen(!isModelMenuOpen);
              }}
              className="bg-surface-container flex items-center gap-3 px-4 py-2 hover:bg-surface-bright transition-all active:scale-95 border border-outline-variant/10"
            >
              <Bolt className="text-secondary w-4 h-4" />
              <span className="font-label text-xs tracking-widest uppercase">{selectedModel}</span>
              <Settings className={`w-3 h-3 transition-transform ${isModelMenuOpen ? 'rotate-180' : ''}`} />
            </button>
            
            {isModelMenuOpen && (
              <div 
                className="absolute right-0 top-full mt-2 w-80 bg-surface-container-high border border-outline-variant shadow-2xl max-h-[70vh] overflow-y-auto no-scrollbar"
                style={{ zIndex: 10000 }}
                onClick={(e: React.MouseEvent) => e.stopPropagation()}
              >
                <div className="p-4 space-y-4">
                  {Object.keys(models).length === 0 ? (
                    <div className="text-xs text-outline uppercase tracking-widest p-2">Loading models...</div>
                  ) : (
                    Object.entries(models).map(([gateway, gatewayModels]) => (
                      <div key={gateway} className="space-y-1">
                        <div className="text-[10px] font-bold text-outline uppercase tracking-[0.2em] mb-2 px-2 border-l-2 border-secondary/50">{gateway} GATEWAY</div>
                        {(gatewayModels as ModelConfig[]).map((m) => (
                          <button
                            key={m.id}
                            onClick={() => {
                              setSelectedModel(m.id);
                              setIsModelMenuOpen(false);
                            }}
                            className={`w-full text-left px-3 py-2 text-xs font-label uppercase tracking-widest transition-all flex justify-between items-center ${
                              selectedModel === m.id ? 'bg-secondary text-on-secondary' : 'hover:bg-surface-bright text-on-surface-variant'
                            }`}
                          >
                            <span className="truncate mr-2">{m.id}</span>
                            <span className="text-[9px] opacity-60 shrink-0">{m.tier.toUpperCase()}</span>
                          </button>
                        ))}
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
          <div className="flex items-center gap-4">
            <button className="text-on-surface-variant hover:text-primary transition-colors active:scale-95">
              <NotificationsActive className="w-5 h-5" />
            </button>
            <button className="text-on-surface-variant hover:text-primary transition-colors active:scale-95">
              <Settings className="w-5 h-5" />
            </button>
            <div className="h-8 w-8 bg-surface-container-highest overflow-hidden">
              <img 
                className="w-full h-full object-cover" 
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuDXqk1oqFhLlkc4NBG6Zp3TSKMhbD6MVPU_cQPqMnfxkQ_rF5MvjntXgm1vQoURTxOplWXQPSrVsESHEE-p_a8Y4YznJ5pkkEXmYoByiBitn-PzJCf2uzrMm31Kh0sE2lrud2mvjZzVA1zUxaIwCzHruQVkaAN-xNr_xyLL4WMUa_3i7GFCBBnpaRRDikiKehsmLniNikpuuhb7k2iFpXM1npKuWC3XW8znwZTjmKgJz84emz8EmXpDbv_7dL-J5_mrPgl8QOGI8VYq" 
                alt="Operator"
                referrerPolicy="no-referrer"
              />
            </div>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 bg-surface-container-low shrink-0 flex flex-col border-r border-outline-variant/10">
          <div className="p-6 border-b border-outline-variant/10">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-surface-container flex items-center justify-center border border-primary/20">
                <Shield className="text-secondary w-6 h-6" />
              </div>
              <div>
                <div className="font-headline text-sm font-bold text-secondary tracking-tight uppercase">OPERATOR-01</div>
                <div className="font-label text-[10px] text-outline tracking-widest uppercase">PRECISION-LEVEL-4</div>
              </div>
            </div>
          </div>
          
          <nav className="flex-1 py-4 overflow-y-auto space-y-1">
            <SidebarItem 
              icon={<Memory className="w-4 h-4" />} 
              label="Engine Status" 
              active={activeSubScreen === 'ENGINE_STATUS' && activeScreen === 'SYSTEM'} 
              onClick={() => handleSubScreenClick('ENGINE_STATUS')} 
            />
            <SidebarItem 
              icon={<Extension className="w-4 h-4" />} 
              label="Core Modules" 
              active={activeSubScreen === 'CORE_MODULES' && activeScreen === 'SYSTEM'} 
              onClick={() => handleSubScreenClick('CORE_MODULES')} 
            />
            <SidebarItem 
              icon={<Hub className="w-4 h-4" />} 
              label="Network Mesh" 
              active={activeSubScreen === 'NETWORK_MESH' && activeScreen === 'SYSTEM'} 
              onClick={() => handleSubScreenClick('NETWORK_MESH')} 
            />
            <SidebarItem 
              icon={<Database className="w-4 h-4" />} 
              label="Storage Nodes" 
              active={activeSubScreen === 'STORAGE_NODES' && activeScreen === 'SYSTEM'} 
              onClick={() => handleSubScreenClick('STORAGE_NODES')} 
            />
            <SidebarItem 
              icon={<Shield className="w-4 h-4" />} 
              label="Security Protocol" 
              active={activeSubScreen === 'SECURITY_PROTOCOL' && activeScreen === 'SYSTEM'} 
              onClick={() => handleSubScreenClick('SECURITY_PROTOCOL')} 
            />
            <SidebarItem 
              icon={<AdminPanelSettings className="w-4 h-4" />} 
              label="System Admin" 
              active={activeSubScreen === 'SYSTEM_ADMIN' && activeScreen === 'SYSTEM'} 
              onClick={() => handleSubScreenClick('SYSTEM_ADMIN')} 
            />
          </nav>

          <div className="p-6 mt-auto space-y-4">
            <button className="w-full bg-secondary text-on-secondary py-3 text-[10px] font-bold tracking-[0.2em] hover:opacity-90 active:scale-95 transition-all gold-glow uppercase">
              INITIALIZE SEQUENCE
            </button>
            <div className="flex flex-col gap-2 pt-4 border-t border-outline-variant/10">
              <button className="flex items-center gap-2 text-[10px] text-gray-600 hover:text-secondary font-label uppercase tracking-widest">
                <HelpOutline className="w-3 h-3" /> Support
              </button>
              <button className="flex items-center gap-2 text-[10px] text-gray-600 hover:text-secondary font-label uppercase tracking-widest">
                <MenuBook className="w-3 h-3" /> Documentation
              </button>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col relative bg-background overflow-hidden">
          <AnimatePresence mode="wait">
            {activeScreen === 'DASHBOARD' && (
              <motion.div key="dashboard" className="flex-1 flex overflow-hidden">
                <Dashboard 
                  selectedModel={selectedModel} 
                  sessionUsage={sessionUsage} 
                  setSessionUsage={setSessionUsage}
                  genSettings={genSettings}
                  setGenSettings={setGenSettings}
                  isRightSidebarOpen={isRightSidebarOpen}
                  setIsRightSidebarOpen={setIsRightSidebarOpen}
                />
              </motion.div>
            )}
            {activeScreen === 'ANALYTICS' && (
              <motion.div key="analytics" className="flex-1 flex overflow-hidden">
                <AnalyticsScreen keys={keys} />
              </motion.div>
            )}
            {activeScreen === 'LOGS' && (
              <motion.div key="logs" className="flex-1 flex overflow-hidden">
                <LogsScreen 
                  models={models} 
                  selectedModel={selectedModel} 
                  setSelectedModel={setSelectedModel} 
                  onOpenModal={() => setIsModalOpen(true)} 
                />
              </motion.div>
            )}
            {activeScreen === 'DEPLOYMENT' && (
              <motion.div key="deployment" className="flex-1 flex overflow-hidden">
                <DeploymentScreen />
              </motion.div>
            )}
            {activeScreen === 'SYSTEM' && (
              <motion.div key="system" className="flex-1 flex overflow-hidden">
                <SystemScreen subScreen={activeSubScreen} />
              </motion.div>
            )}
          </AnimatePresence>
        </main>
      </div>

      {/* Status Bar */}
      <footer className="bg-surface-container-lowest h-8 w-full shrink-0 flex items-center justify-between px-4 z-50 border-t border-outline-variant/10">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00C851] gold-glow"></span>
            <span className="font-mono text-[10px] text-secondary uppercase tracking-[0.2em]">ENGINE_STABLE_v3.0.0</span>
          </div>
          <div className="h-3 w-[1px] bg-outline-variant/30"></div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] text-outline uppercase tracking-widest">LATENCY:</span>
            <span className="font-mono text-[10px] text-on-surface font-bold">14ms</span>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] text-outline uppercase tracking-widest">SESSION_TOKENS:</span>
            <span className="font-mono text-[10px] text-primary font-bold">{sessionUsage.tokens.toLocaleString()}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] text-outline uppercase tracking-widest">BILLING_TOTAL:</span>
            <span className="font-mono text-[10px] text-secondary font-bold">${sessionUsage.cost.toFixed(2)}</span>
          </div>
          <div className="h-3 w-[1px] bg-outline-variant/30"></div>
          <span className="font-mono text-[10px] text-outline-variant uppercase tracking-widest">PEACOCK ENGINE v4.2.0-STABLE</span>
        </div>
      </footer>

      {/* Modal */}
      <AnimatePresence>
        {isModalOpen && (
          <CustomToolModal onClose={() => setIsModalOpen(false)} />
        )}
      </AnimatePresence>
    </div>
  );
}

function SidebarItem({ icon, label, active, onClick }: { icon: React.ReactNode, label: string, active: boolean, onClick: () => void }) {
  return (
    <button 
      onClick={onClick}
      className={`w-full flex items-center gap-4 px-6 py-3 transition-all ${
        active ? 'bg-surface-container text-primary border-l-4 border-primary' : 'text-gray-500 hover:bg-surface-bright hover:text-white'
      }`}
    >
      {icon}
      <span className="text-sm font-medium uppercase tracking-widest">{label}</span>
    </button>
  );
}

function LogEntry({ time, status, message }: { time: string, status: 'OK' | 'ERROR' | 'INFO', message: string }) {
  const color = status === 'OK' ? 'text-[#00C851]' : status === 'ERROR' ? 'text-error' : 'text-[#00BFFF]';
  return (
    <div className="flex gap-2">
      <span className={color}>{time}</span>
      <span className={status === 'ERROR' ? 'text-error' : status === 'INFO' ? 'text-on-surface' : 'text-outline'}>{message}</span>
    </div>
  );
}

function Dashboard({ 
  selectedModel, 
  sessionUsage, 
  setSessionUsage,
  genSettings,
  setGenSettings,
  isRightSidebarOpen,
  setIsRightSidebarOpen
}: { 
  selectedModel: string, 
  sessionUsage: { tokens: number, cost: number }, 
  setSessionUsage: React.Dispatch<React.SetStateAction<{ tokens: number, cost: number }>>,
  genSettings: any,
  setGenSettings: any,
  isRightSidebarOpen: boolean,
  setIsRightSidebarOpen: any
}) {
  const [messages, setMessages] = useState<Message[]>([
    { 
      role: 'model', 
      content: "PEACOCK ENGINE INITIALIZED. NEURAL_LINK_STABLE. STANDING BY FOR OPERATOR COMMANDS.", 
      time: "14:20:00" 
    }
  ]);
  const [input, setInput] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<PeacockWS | null>(null);

  const handleSend = async () => {
    if (!input.trim() || isGenerating) return;

    const userMsg = input;
    setInput('');
    const time = new Date().toLocaleTimeString([], { hour12: false });
    
    // Add user message
    const userMessageObj: Message = { role: 'user', content: userMsg, time };
    setMessages((prev: Message[]) => [...prev, userMessageObj]);
    setIsGenerating(true);

    // Initial AI placeholder for streaming
    setMessages((prev: Message[]) => [...prev, { role: 'model', content: "", time: new Date().toLocaleTimeString([], { hour12: false }) }]);

    if (!wsRef.current) {
      wsRef.current = new PeacockWS(
        (chunk: string) => {
          setMessages((prev: Message[]) => {
            const last = [...prev];
            last[last.length - 1].content = chunk;
            return last;
          });
        },
        (error: any) => {
          setIsGenerating(false);
          setMessages((prev: Message[]) => [...prev, { role: 'model', content: `ERROR: ${error}`, time: new Date().toLocaleTimeString([], { hour12: false }) }]);
        },
        (full: string, usage: any) => {
          setIsGenerating(false);
          if (usage) {
            setSessionUsage((prev: { tokens: number, cost: number }) => ({
              tokens: prev.tokens + (usage.total_tokens || 0),
              cost: prev.cost + (usage.cost || 0)
            }));
          }
        }
      );
    }

    try {
      if (wsRef.current) {
        await wsRef.current.connect(selectedModel, {
          temp: genSettings.temp,
          top_p: genSettings.top_p,
          max_tokens: genSettings.maxTokens,
          system: genSettings.system
        });
        wsRef.current.sendPrompt(userMsg);
      }
    } catch (e) {
      setIsGenerating(false);
      setMessages((prev: Message[]) => [...prev, { role: 'model', content: "ERROR: NEURAL_LINK_STABILITY_FAILURE", time: new Date().toLocaleTimeString([], { hour12: false }) }]);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-1 overflow-hidden"
    >
      <div className="flex-1 flex flex-col relative overflow-hidden">
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-8 space-y-8 max-w-4xl mx-auto w-full no-scrollbar">
          {messages.map((msg: Message, idx: number) => (
            <div key={idx} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} gap-3`}>
              {msg.role === 'model' && (
                <div className="flex items-center gap-3 mb-1">
                  <div className="w-6 h-6 bg-primary flex items-center justify-center">
                    <Bolt className="text-on-primary w-4 h-4 fill-current" />
                  </div>
                  <span className="font-headline text-xs font-bold tracking-widest text-primary uppercase">PEACOCK_ENGINE</span>
                </div>
              )}
              <div className={`p-4 max-w-[85%] border-l ${msg.role === 'user' ? 'bg-surface-container-high border-primary/20' : 'bg-surface-container border-secondary/20'}`}>
                <p className="text-sm leading-relaxed text-on-surface whitespace-pre-wrap">{msg.content}</p>
              </div>
              <div className="flex items-center gap-2 font-label text-[9px] text-outline uppercase tracking-wider">
                <span>{msg.role === 'user' ? 'OPERATOR' : 'STABLE_STATE'}</span> <span className={msg.role === 'user' ? 'text-primary-fixed-dim' : 'text-secondary'}>{msg.time}</span>
              </div>
            </div>
          ))}
          {isGenerating && (
            <div className="flex flex-col items-start gap-3 animate-pulse">
              <div className="flex items-center gap-3 mb-1">
                <div className="w-6 h-6 bg-surface-container-highest flex items-center justify-center">
                  <Bolt className="text-outline w-4 h-4" />
                </div>
                <span className="font-headline text-xs font-bold tracking-widest text-outline uppercase">THINKING...</span>
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-6 bg-surface-dim shrink-0">
          <div className="max-w-4xl mx-auto relative flex flex-col gap-3">
            <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
              <div className="bg-surface-container px-3 py-1.5 flex items-center gap-2 group cursor-pointer hover:bg-surface-bright transition-all">
                <Description className="w-3 h-3 text-primary" />
                <span className="font-label text-[10px] text-on-surface-variant uppercase tracking-tighter">config_main.yml</span>
                <Close className="w-3 h-3 text-outline group-hover:text-error transition-colors" />
              </div>
            </div>
            <div className="relative bg-surface-container-low kinetic-focus transition-all group border-b border-outline-variant/30">
              <textarea 
                value={input}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setInput(e.target.value)}
                onKeyDown={(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                className="w-full bg-transparent border-none focus:ring-0 p-4 font-body text-sm text-on-surface placeholder:text-outline-variant resize-none min-h-[100px]" 
                placeholder="INPUT COMMANDS OR SYSTEM QUERIES..."
              ></textarea>
              <div className="flex items-center justify-between p-3 bg-surface-container-lowest/50">
                <div className="flex items-center gap-1">
                  <button className="p-2 text-outline hover:text-primary transition-all active:scale-95">
                    <AttachFile className="w-5 h-5" />
                  </button>
                  <button className="p-2 text-outline hover:text-primary transition-all active:scale-95">
                    <AddPhotoAlternate className="w-5 h-5" />
                  </button>
                  <button className="p-2 text-outline hover:text-primary transition-all active:scale-95">
                    <Mic className="w-5 h-5" />
                  </button>
                </div>
                <button 
                  onClick={handleSend}
                  disabled={isGenerating || !input.trim()}
                  className={`bg-gradient-to-br from-primary-fixed-dim to-[#0066cc] text-on-primary font-headline text-xs font-bold px-6 py-2 tracking-widest active:scale-95 transition-all ${isGenerating ? 'opacity-50 cursor-not-allowed' : 'hover:brightness-110'}`}
                >
                  {isGenerating ? 'PROCESSING...' : 'EXECUTE_PROMPT'}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Floating Sidebar Toggle */}
        <div className="absolute top-1/2 -right-1 transform -translate-y-1/2 z-40">
          <button 
            onClick={() => setIsRightSidebarOpen(!isRightSidebarOpen)}
            className="w-4 h-16 bg-surface-container-high border-y border-l border-outline-variant/30 flex items-center justify-center hover:bg-surface-bright text-outline-variant hover:text-primary transition-all rounded-l-md"
          >
            {isRightSidebarOpen ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Right Context Panel - Collapsible */}
      <AnimatePresence mode="popLayout">
        {isRightSidebarOpen && (
          <motion.aside 
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 384, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="bg-surface-container-low shrink-0 flex flex-col border-l border-outline-variant/10 overflow-hidden"
          >
            <div className="flex flex-col h-full w-[384px] overflow-y-auto no-scrollbar">
              <div className="p-6 space-y-8">
                {/* Section A: Strategic Objectives (Goals) */}
                <section>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-headline text-[10px] font-bold tracking-[0.2em] text-outline uppercase flex items-center gap-2">
                      <Target className="w-3 h-3 text-secondary" /> Strategic Objectives
                    </h3>
                  </div>
                  <div className="space-y-2">
                    <ObjectiveItem label="WebSocket Streaming" status="OPERATIONAL" progress={100} />
                    <ObjectiveItem label="Neural Link Bridge" status="OPERATIONAL" progress={100} />
                    <ObjectiveItem label="Sand Hill UI Implementation" status="SYNCHRONIZING..." progress={85} active />
                    <ObjectiveItem label="Universal Provider Scaling" status="PENDING" progress={40} />
                  </div>
                </section>

                {/* Section B: System Protocol (Instructions) */}
                <section>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-headline text-[10px] font-bold tracking-[0.2em] text-outline uppercase flex items-center gap-2">
                      <Terminal className="w-3 h-3 text-primary" /> System Protocol
                    </h3>
                  </div>
                  <div className="bg-surface-container-lowest p-3 border border-outline-variant/20 kinetic-focus">
                    <textarea 
                      value={genSettings.system}
                      onChange={(e) => setGenSettings({...genSettings, system: e.target.value})}
                      className="w-full h-32 bg-transparent border-none focus:ring-0 p-0 text-[11px] font-mono text-on-surface-variant placeholder:text-gray-700 resize-none uppercase leading-relaxed"
                      placeholder="DEFINE GLOBAL OPERATIONAL INSTRUCTIONS..."
                    />
                  </div>
                </section>

                {/* Section C: Run Settings (Generation) */}
                <section>
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="font-headline text-[10px] font-bold tracking-[0.2em] text-outline uppercase flex items-center gap-2">
                      <Tune className="w-3 h-3 text-primary" /> Run Settings
                    </h3>
                  </div>
                  <div className="space-y-6">
                    <GenerationSlider 
                      label="Temperature" 
                      value={genSettings.temp} 
                      min={0} max={2} step={0.05}
                      onChange={(v) => setGenSettings({...genSettings, temp: v})} 
                    />
                    <GenerationSlider 
                      label="Top P" 
                      value={genSettings.top_p} 
                      min={0} max={1} step={0.01}
                      onChange={(v) => setGenSettings({...genSettings, top_p: v})} 
                    />
                    <GenerationSlider 
                      label="Max Tokens" 
                      value={genSettings.maxTokens} 
                      min={1} max={32000} step={1}
                      onChange={(v) => setGenSettings({...genSettings, maxTokens: v})} 
                    />
                  </div>
                </section>

                {/* Section D: Operational Intel (Usage) */}
                <section className="pt-4 border-t border-outline-variant/10">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-surface-container p-4">
                      <div className="text-[9px] text-outline-variant font-label uppercase mb-1">Session Tokens</div>
                      <div className="font-mono text-xl text-primary font-medium tracking-tight">
                        {sessionUsage.tokens.toLocaleString()}
                      </div>
                    </div>
                    <div className="bg-surface-container p-4">
                      <div className="text-[9px] text-outline-variant font-label uppercase mb-1">Session Cost</div>
                      <div className="font-mono text-xl text-secondary font-medium tracking-tight">
                        ${sessionUsage.cost.toFixed(3)}
                      </div>
                    </div>
                  </div>
                </section>
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function ObjectiveItem({ label, status, progress, active }: { label: string, status: string, progress: number, active?: boolean }) {
  return (
    <div className={`p-3 bg-surface-container-low border-l-2 transition-all ${active ? 'border-secondary bg-surface-container' : 'border-outline-variant/30 opacity-70'}`}>
      <div className="flex justify-between items-center mb-1.5">
        <span className="text-[10px] font-headline font-bold text-on-surface uppercase tracking-tight">{label}</span>
        <span className={`text-[8px] font-mono px-1.5 py-0.5 ${active ? 'bg-secondary/10 text-secondary' : 'bg-surface-container-highest text-outline'}`}>{status}</span>
      </div>
      <div className="h-1 w-full bg-surface-container-lowest rounded-full overflow-hidden">
        <div 
          className={`h-full transition-all duration-1000 ${active ? 'bg-secondary gold-glow' : 'bg-outline-variant'}`}
          style={{ width: `${progress}%` }}
        ></div>
      </div>
    </div>
  );
}

function GenerationSlider({ label, value, min, max, step, onChange }: { label: string, value: number, min: number, max: number, step: number, onChange: (v: number) => void }) {
  return (
    <div className="space-y-3">
      <div className="flex justify-between items-center">
        <label className="font-headline text-[10px] font-bold text-gray-400 uppercase tracking-widest">{label}</label>
        <div className="bg-surface-container px-2 py-0.5 border border-outline-variant/20">
          <span className="font-mono text-[10px] text-primary font-bold">{value}</span>
        </div>
      </div>
      <input 
        type="range"
        min={min} max={max} step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-1 bg-surface-container-lowest appearance-none cursor-pointer accent-primary" 
      />
    </div>
  );
}

function SystemScreen({ subScreen }: { subScreen: SubScreen }) {
  const renderContent = () => {
    switch (subScreen) {
      case 'ENGINE_STATUS':
        return (
          <div className="space-y-8">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <StatusCard icon={<Cpu className="w-6 h-6" />} label="CPU LOAD" value="24%" status="HEALTHY" />
              <StatusCard icon={<Memory className="w-4 h-4" />} label="MEMORY_USE" value="12.4GB" status="OPTIMAL" />
              <StatusCard icon={<Activity className="w-6 h-6" />} label="THROUGHPUT" value="850T/s" status="HIGH" />
            </div>
            <div className="bg-surface-container p-6 border-l-2 border-primary">
              <h3 className="font-headline text-sm font-bold uppercase tracking-widest mb-4">Neural Pathway Health</h3>
              <div className="space-y-4">
                {[1, 2, 3, 4].map((i: number) => (
                  <div key={i} className="flex items-center gap-4">
                    <span className="font-mono text-[10px] text-outline w-24">PATHWAY_0{i}</span>
                    <div className="flex-1 h-2 bg-surface-container-highest rounded-full overflow-hidden">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.random() * 40 + 60}%` }}
                        className="h-full bg-primary"
                      />
                    </div>
                    <span className="font-mono text-[10px] text-primary">STABLE</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );
      case 'CORE_MODULES':
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <ModuleCard name="NEURAL_CORE_V4" status="ACTIVE" version="4.2.0" uptime="142d 04h" />
            <ModuleCard name="GEOSPATIAL_ENGINE" status="ACTIVE" version="2.1.5" uptime="88d 12h" />
            <ModuleCard name="SECURITY_LAYER_X" status="ACTIVE" version="1.0.0" uptime="312d 22h" />
            <ModuleCard name="DATA_MESH_SYNC" status="STANDBY" version="3.4.2" uptime="0d 0h" />
          </div>
        );
      case 'NETWORK_MESH':
        return (
          <div className="space-y-6">
            <div className="bg-surface-container p-6">
              <h3 className="font-headline text-sm font-bold uppercase tracking-widest mb-6 flex items-center gap-2">
                <Hub className="w-5 h-5 text-secondary" /> Global Mesh Topology
              </h3>
              <div className="aspect-video bg-surface-container-lowest border border-outline-variant/20 relative flex items-center justify-center overflow-hidden">
                <div className="absolute inset-0 opacity-20 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')]"></div>
                <div className="relative w-full h-full">
                   {/* Simulated Map Nodes */}
                   <div className="absolute top-1/4 left-1/3 w-3 h-3 bg-primary gold-glow rounded-full"></div>
                   <div className="absolute top-1/2 left-1/2 w-3 h-3 bg-secondary gold-glow rounded-full"></div>
                   <div className="absolute bottom-1/3 right-1/4 w-3 h-3 bg-primary gold-glow rounded-full"></div>
                   <svg className="absolute inset-0 w-full h-full pointer-events-none">
                     <line x1="33%" y1="25%" x2="50%" y2="50%" stroke="rgba(170, 199, 255, 0.3)" strokeWidth="1" />
                     <line x1="50%" y1="50%" x2="75%" y2="66%" stroke="rgba(240, 205, 45, 0.3)" strokeWidth="1" />
                   </svg>
                </div>
                <div className="absolute bottom-4 left-4 bg-surface-container-high/80 p-3 text-[10px] font-mono space-y-1">
                  <div className="flex items-center gap-2"><span className="w-2 h-2 bg-primary"></span> US-EAST-01: ACTIVE</div>
                  <div className="flex items-center gap-2"><span className="w-2 h-2 bg-secondary"></span> EU-WEST-02: OPTIMIZING</div>
                </div>
              </div>
            </div>
          </div>
        );
      case 'STORAGE_NODES':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <StorageCard label="Primary Vault" capacity="500TB" used="342TB" />
              <StorageCard label="Neural Cache" capacity="50TB" used="12TB" />
            </div>
            <div className="bg-surface-container p-6">
              <h3 className="font-headline text-sm font-bold uppercase tracking-widest mb-4">Recent Access Logs</h3>
              <div className="space-y-2">
                <LogEntry time="14:55:01" status="OK" message="READ_ACCESS: /vault/neural/weights_v4.bin" />
                <LogEntry time="14:54:32" status="OK" message="WRITE_ACCESS: /cache/session_8812.tmp" />
                <LogEntry time="14:52:10" status="INFO" message="COMPRESSION_ROUTINE_STARTED" />
              </div>
            </div>
          </div>
        );
      case 'SECURITY_PROTOCOL':
        return (
          <div className="space-y-8">
            <div className="flex items-center justify-between bg-error-container/20 p-6 border border-error/30">
              <div className="flex items-center gap-4">
                <Shield className="w-10 h-10 text-error" />
                <div>
                  <h3 className="font-headline text-lg font-bold text-error uppercase tracking-tight">Threat Level: Minimal</h3>
                  <p className="text-xs text-on-error-container font-label uppercase tracking-widest">Last scan completed 4 minutes ago</p>
                </div>
              </div>
              <button className="bg-error text-on-error px-6 py-2 font-bold text-xs tracking-widest uppercase">Initiate Lockdown</button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-surface-container p-6">
                <h4 className="font-headline text-xs font-bold uppercase tracking-widest mb-4 text-outline">Active Firewalls</h4>
                <div className="space-y-3">
                  <FirewallItem label="External Gateway" status="ACTIVE" />
                  <FirewallItem label="Neural Isolation" status="ACTIVE" />
                  <FirewallItem label="Data Encryption" status="ACTIVE" />
                </div>
              </div>
              <div className="bg-surface-container p-6">
                <h4 className="font-headline text-xs font-bold uppercase tracking-widest mb-4 text-outline">Auth Protocols</h4>
                <div className="space-y-3">
                  <FirewallItem label="Multi-Factor" status="ENABLED" />
                  <FirewallItem label="Biometric Link" status="DISABLED" />
                  <FirewallItem label="Hardware Key" status="REQUIRED" />
                </div>
              </div>
            </div>
          </div>
        );
      case 'SYSTEM_ADMIN':
        return (
          <div className="space-y-8">
            <div className="bg-surface-container p-6">
              <h3 className="font-headline text-sm font-bold uppercase tracking-widest mb-6 flex items-center gap-2">
                <UserCog className="w-5 h-5 text-primary" /> Administrative Controls
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-4">
                  <h4 className="text-xs font-bold text-outline uppercase tracking-widest">System Overrides</h4>
                  <div className="flex items-center justify-between p-3 bg-surface-container-low">
                    <span className="text-xs font-label uppercase">Maintenance Mode</span>
                    <Toggle active={false} />
                  </div>
                  <div className="flex items-center justify-between p-3 bg-surface-container-low">
                    <span className="text-xs font-label uppercase">Debug Verbosity</span>
                    <Toggle active={true} />
                  </div>
                </div>
                <div className="space-y-4">
                  <h4 className="text-xs font-bold text-outline uppercase tracking-widest">Danger Zone</h4>
                  <button className="w-full py-3 border border-error/30 text-error hover:bg-error/10 transition-all font-bold text-xs tracking-widest uppercase">Purge System Cache</button>
                  <button className="w-full py-3 bg-error text-on-error font-bold text-xs tracking-widest uppercase">Factory Reset Engine</button>
                </div>
              </div>
            </div>
          </div>
        );
      default:
        return <div>Select a sub-screen from the sidebar.</div>;
    }
  };

  return (
    <div className="p-8 h-full overflow-y-auto no-scrollbar w-full">
      <div className="mb-8">
        <h1 className="text-3xl font-headline font-medium tracking-tighter uppercase text-on-surface">{subScreen.replace('_', ' ')}</h1>
        <p className="text-outline font-label text-[10px] tracking-widest uppercase">SYSTEM_COMPONENT_ID: {subScreen}_v4.2.0</p>
      </div>
      {renderContent()}
    </div>
  );
}

function StatusCard({ icon, label, value, status }: { icon: React.ReactNode, label: string, value: string, status: string }) {
  return (
    <div className="bg-surface-container p-6 border-b-2 border-secondary/30">
      <div className="flex items-center justify-between mb-4">
        <div className="text-secondary">{icon}</div>
        <span className="text-[10px] font-mono text-[#00C851] bg-[#00C851]/10 px-2 py-0.5 uppercase">{status}</span>
      </div>
      <div className="text-[10px] font-label text-outline uppercase tracking-widest mb-1">{label}</div>
      <div className="text-2xl font-headline text-white">{value}</div>
    </div>
  );
}

function ModuleCard({ name, status, version, uptime }: { name: string, status: string, version: string, uptime: string }) {
  return (
    <div className="bg-surface-container p-6 border border-outline-variant/10 hover:border-primary/30 transition-all group">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h3 className="font-headline text-lg font-bold text-white uppercase tracking-tight">{name}</h3>
          <span className="text-[10px] font-mono text-primary uppercase">v{version}</span>
        </div>
        <div className={`px-3 py-1 text-[10px] font-bold uppercase ${status === 'ACTIVE' ? 'bg-[#00C851]/20 text-[#00C851]' : 'bg-outline-variant/20 text-outline'}`}>
          {status}
        </div>
      </div>
      <div className="flex justify-between items-end">
        <div>
          <div className="text-[9px] font-label text-outline uppercase tracking-widest mb-1">UPTIME</div>
          <div className="text-sm font-mono text-on-surface">{uptime}</div>
        </div>
        <button className="text-primary text-[10px] font-bold uppercase tracking-widest hover:underline">Configure</button>
      </div>
    </div>
  );
}

function StorageCard({ label, capacity, used }: { label: string, capacity: string, used: string }) {
  const percent = (parseInt(used) / parseInt(capacity)) * 100;
  return (
    <div className="bg-surface-container p-6">
      <div className="flex justify-between items-end mb-4">
        <div>
          <h3 className="font-headline text-sm font-bold text-white uppercase tracking-tight">{label}</h3>
          <p className="text-[10px] font-label text-outline uppercase tracking-widest">{used} / {capacity}</p>
        </div>
        <span className="text-xl font-headline text-primary">{Math.round(percent)}%</span>
      </div>
      <div className="h-2 bg-surface-container-highest rounded-full overflow-hidden">
        <div className="h-full bg-primary" style={{ width: `${percent}%` }}></div>
      </div>
    </div>
  );
}

function FirewallItem({ label, status }: { label: string, status: string }) {
  return (
    <div className="flex items-center justify-between p-3 bg-surface-container-low">
      <span className="text-xs font-label uppercase text-on-surface">{label}</span>
      <span className={`text-[10px] font-bold uppercase ${status === 'ACTIVE' || status === 'ENABLED' || status === 'REQUIRED' ? 'text-[#00C851]' : 'text-error'}`}>
        {status}
      </span>
    </div>
  );
}

function Toggle({ active }: { active: boolean }) {
  return (
    <div className={`w-10 h-5 rounded-full p-1 transition-all cursor-pointer ${active ? 'bg-primary' : 'bg-outline-variant'}`}>
      <div className={`w-3 h-3 bg-white rounded-full transition-all ${active ? 'translate-x-5' : 'translate-x-0'}`}></div>
    </div>
  );
}

function AnalyticsScreen({ keys }: { keys: KeyTelemetry[] }) {
  return (
    <div className="p-8 space-y-8 overflow-y-auto no-scrollbar w-full">
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-end mb-8 gap-6">
        <div className="space-y-1">
          <h1 className="text-3xl font-headline font-medium tracking-tighter uppercase text-on-surface">API Key Management</h1>
          <p className="text-outline font-label text-[10px] tracking-widest uppercase">SECURE_GATEWAY_AUTH_CONTROL_PANEL_v4.2.0</p>
        </div>
        <div className="flex flex-wrap gap-4">
          <MetricCard label="TOTAL_KEYS" value={keys.length.toString()} color="primary" />
          <MetricCard label="HEALTHY_NODES" value={keys.filter(k => k.success_rate > 90).length.toString()} color="success" dot />
          <MetricCard label="TELEMETRY_STATUS" value="LIVE" color="secondary" />
          <button className="bg-secondary text-on-secondary px-6 h-full flex items-center justify-center font-bold text-[10px] tracking-[0.15em] hover:opacity-90 active:scale-95 transition-all gold-glow uppercase py-4">
            <Add className="mr-2 w-4 h-4" /> ADD NEW KEY
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <div className="xl:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4">
          {keys.map((k: KeyTelemetry) => (
            <ApiKeyCard 
              key={k.account}
              name={k.account} 
              id={k.gateway.toUpperCase()} 
              keyStr="sk-••••••••••••••••" 
              usage={k.total_tokens % 100} 
              latency={k.last_used.split('T')[1]?.split('.')[0] || "N/A"} 
              status={k.success_rate > 90 ? 'healthy' : 'warning'}
            />
          ))}
          <div className="bg-surface-container/20 border border-dashed border-outline-variant/30 flex flex-col items-center justify-center min-h-[200px] gap-2 opacity-50 hover:opacity-100 transition-all group cursor-pointer">
            <AddCircle className="w-6 h-6 text-outline group-hover:text-primary" />
            <span className="text-[10px] font-label text-outline uppercase tracking-widest">Provision New Slot</span>
          </div>
        </div>

        <div className="space-y-6">
          <div className="glass-panel p-6 border-l border-primary/20 flex flex-col gap-6">
            <div className="flex justify-between items-center border-b border-outline-variant/10 pb-4">
              <h2 className="text-sm font-headline font-bold uppercase tracking-widest text-secondary">Key Telemetry</h2>
              <MonetizationOn className="text-outline w-4 h-4" />
            </div>
            <div className="space-y-6">
              <div className="space-y-2">
                <label className="text-[10px] font-label text-outline uppercase tracking-[0.15em]">Active Transmission</label>
                <div className="bg-surface-container-lowest p-4 font-mono text-[11px] leading-relaxed text-primary-fixed-dim/70">
                  <div className="flex justify-between mb-1">
                    <span className="text-primary-fixed-dim">TIMESTAMP</span>
                    <span>2023-11-24T14:32:01.002Z</span>
                  </div>
                  <div className="flex justify-between mb-1">
                    <span className="text-primary-fixed-dim">REQUEST_ID</span>
                    <span>REQ-V9X0-8812</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-primary-fixed-dim">STATUS</span>
                    <span className="text-[#00C851]">200_OK</span>
                  </div>
                </div>
              </div>
              <div className="space-y-4">
                <ProgressBar label="Throughput Capacity" value={82} color="primary" />
                <ProgressBar label="Error Frequency (24h)" value={12} color="error" />
              </div>
              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-outline-variant/10">
                <div>
                  <div className="text-[9px] font-label text-outline uppercase tracking-widest mb-1">COOLDOWN_TIMER</div>
                  <div className="text-lg font-headline text-white">00:00:00</div>
                </div>
                <div>
                  <div className="text-[9px] font-label text-outline uppercase tracking-widest mb-1">ROTATION_POLICY</div>
                  <div className="text-lg font-headline text-secondary">BI-WEEKLY</div>
                </div>
              </div>
              <button className="w-full border border-outline-variant text-outline py-3 text-[10px] font-bold tracking-[0.2em] hover:bg-surface-bright hover:text-white transition-all active:scale-95 uppercase">
                Manual Key Rotation
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, color, dot }: { label: string, value: string, color: 'primary' | 'secondary' | 'success', dot?: boolean }) {
  const borderColor = color === 'primary' ? 'border-primary/30' : color === 'secondary' ? 'border-secondary/30' : 'border-[#00C851]/30';
  const textColor = color === 'primary' ? 'text-primary' : color === 'secondary' ? 'text-secondary' : 'text-[#00C851]';
  
  return (
    <div className={`bg-surface-container p-4 min-w-[160px] border-b-2 ${borderColor}`}>
      <div className="flex items-center gap-2 mb-1">
        {dot && <div className="w-[6px] h-[6px] bg-[#00C851]"></div>}
        <div className="text-[10px] font-label text-outline uppercase tracking-widest">{label}</div>
      </div>
      <div className={`text-2xl font-headline ${textColor}`}>{value}</div>
    </div>
  );
}

interface ApiKeyCardProps {
  key?: React.Key;
  name: string;
  id: string;
  keyStr: string;
  usage: number;
  latency: string;
  status: 'healthy' | 'warning' | 'error';
  icon?: React.ReactNode;
}

function ApiKeyCard({ name, id, keyStr, usage, latency, status, icon }: ApiKeyCardProps) {
  const statusColor = status === 'healthy' ? 'bg-[#00C851]' : status === 'warning' ? 'bg-secondary' : 'bg-error';
  const hoverBorder = status === 'healthy' ? 'hover:border-primary' : status === 'warning' ? 'hover:border-secondary' : 'hover:border-error';
  
  return (
    <div className={`bg-surface-container p-5 hover:border-l-4 ${hoverBorder} transition-all group cursor-pointer active:scale-[0.98] ${status === 'error' ? 'opacity-60' : ''}`}>
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-surface-container-low flex items-center justify-center">
            {icon || <Search className="text-primary w-5 h-5" />}
          </div>
          <div>
            <h3 className="text-sm font-headline font-bold text-white tracking-tight uppercase">{name}</h3>
            <p className="text-[10px] font-label text-outline tracking-wider uppercase">GATEWAY_ID: {id}</p>
          </div>
        </div>
        <div className={`w-[6px] h-[6px] ${statusColor}`}></div>
      </div>
      <div className="space-y-4">
        <div className="bg-surface-container-lowest p-2 font-mono text-xs text-primary/80 flex justify-between items-center">
          <span>{keyStr}</span>
          <ContentCopy className="w-3 h-3 cursor-pointer hover:text-white" />
        </div>
        <div className="flex justify-between items-end">
          <div>
            <div className="text-[9px] font-label text-outline uppercase tracking-widest mb-1">USAGE_PERCENT</div>
            <div className="w-32 h-1 bg-surface-container-high overflow-hidden">
              <div className={`h-full ${status === 'error' ? 'bg-error' : 'bg-primary'}`} style={{ width: `${usage}%` }}></div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-[9px] font-label text-outline uppercase tracking-widest mb-1">{status === 'error' ? 'COOLDOWN' : 'LATENCY'}</div>
            <div className={`text-xs font-mono ${status === 'error' ? 'text-error' : status === 'warning' ? 'text-secondary' : 'text-[#00C851]'}`}>{latency}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ProgressBar({ label, value, color }: { label: string, value: number, color: 'primary' | 'error' }) {
  return (
    <div>
      <div className="flex justify-between text-[10px] font-label text-outline uppercase tracking-widest mb-2">
        <span>{label}</span>
        <span className={color === 'primary' ? 'text-primary' : 'text-error'}>{value}%</span>
      </div>
      <div className="h-1.5 bg-surface-container-highest">
        <div className={`h-full ${color === 'primary' ? 'bg-gradient-to-r from-primary to-primary-container' : 'bg-error'}`} style={{ width: `${value}%` }}></div>
      </div>
    </div>
  );
}

function LogsScreen({ models, selectedModel, setSelectedModel, onOpenModal }: { models: Record<string, ModelConfig[]>, selectedModel: string, setSelectedModel: (m: string) => void, onOpenModal: () => void }) {
  return (
    <div className="flex flex-col h-full overflow-hidden w-full">
      <div className="flex-1 overflow-y-auto no-scrollbar">
        <div className="px-8 py-10">
          <h1 className="text-4xl font-headline font-medium tracking-tighter uppercase mb-2">Model Registry</h1>
          <p className="text-on-surface-variant text-sm font-body max-w-2xl">High-precision neural assets currently deployed to the mesh. Precision tuning required for Level 4 operations.</p>
        </div>

        <div className="grid grid-cols-12 bg-surface-container px-8 py-3 text-[10px] font-label text-outline tracking-widest uppercase sticky top-0 z-10">
          <div className="col-span-5">Model Identity</div>
          <div className="col-span-2">Deployment Status</div>
          <div className="col-span-2 text-right">Context Window</div>
          <div className="col-span-3 text-right">Pricing / 1K Tokens</div>
        </div>

        <div className="divide-y divide-outline-variant/10">
          {Object.entries(models).flatMap(([gateway, gatewayModels]: [string, ModelConfig[]]) => 
            gatewayModels.map((m: ModelConfig) => (
              <ModelRow 
                key={m.id}
                name={m.id.split('/').pop()?.toUpperCase() || m.id.toUpperCase()} 
                uuid={m.id} 
                status={m.tier === 'deprecated' ? 'FROZEN_STATE' : 'ACTIVE_NODE'} 
                context={m.tpm > 500000 ? "1M" : "128K"} 
                price={`$${(m.rpd / 10000).toFixed(4)}`} 
                color={m.tier === 'free' ? '#00C851' : m.tier === 'expensive' ? '#ff9a00' : '#00BFFF'} 
                isDefault={m.id === selectedModel}
                onClick={() => setSelectedModel(m.id)}
              />
            ))
          )}
        </div>
      </div>

      {/* Details Panel Overlay (Simulated as being on the right) */}
      <aside className="w-80 h-full fixed right-0 top-16 bg-surface-container-low flex flex-col border-l border-outline-variant/10 z-40 overflow-y-auto no-scrollbar">
        <div className="p-6 border-b border-outline-variant/10">
          <div className="flex justify-between items-start mb-6">
            <h2 className="text-xl font-headline font-medium tracking-tighter uppercase text-primary">STRATOS-ALPHA-9</h2>
            <Close className="text-outline cursor-pointer hover:text-white w-5 h-5" />
          </div>
          <div className="space-y-6">
            <div>
              <label className="text-[10px] font-label text-outline tracking-widest uppercase mb-2 block">Visual Profile</label>
              <img 
                className="w-full grayscale brightness-75 hover:grayscale-0 transition-all" 
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuCgTMpmCp1Bv7vnAuh73GDlh2UdlJyrF5WyCHO2F69JfxcX0-mNU8QoWd1wGQi_5pn9Wb6K3cN0hE7_k_QRMHXi9Us-cELjpLBba4d9pp1ak1bLUIv421_avFLOrwwl1q3pmGns_PACFJai05dZcAe1nH3c5Rj1f3K7xm-T8_PVJx5I2Kx-yli0UWz2fAwjd6Rd_wf8QQTbO19_34Vpm1UCbF8SvpTqdq_XpYu8UzB5aUlcmmNm6f3qaQ48jLyd9tjGqOQtDJNjDvf4" 
                alt="Model Profile"
                referrerPolicy="no-referrer"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-surface-container p-3">
                <div className="text-[9px] font-label text-outline uppercase tracking-wider mb-1">Latency</div>
                <div className="text-lg font-label text-[#00C851]">42ms</div>
              </div>
              <div className="bg-surface-container p-3">
                <div className="text-[9px] font-label text-outline uppercase tracking-wider mb-1">Throughput</div>
                <div className="text-lg font-label text-primary">850T/s</div>
              </div>
            </div>
            <div>
              <label className="text-[10px] font-label text-outline tracking-widest uppercase mb-2 block">Performance Mesh</label>
              <div className="h-1 bg-outline-variant/10 w-full mb-1">
                <div className="h-full bg-secondary w-[88%]"></div>
              </div>
              <div className="flex justify-between text-[9px] font-label text-outline uppercase">
                <span>Reliability Index</span>
                <span>99.8%</span>
              </div>
            </div>
            <div className="bg-surface-container-lowest p-4 font-label">
              <label className="text-[10px] text-primary tracking-widest uppercase mb-3 block">Specifications (Technical)</label>
              <div className="space-y-2 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-outline">ARCH_TYPE:</span>
                  <span className="text-on-surface">TRANSFORMER_V4</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-outline">PARAM_COUNT:</span>
                  <span className="text-on-surface">175.4B</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-outline">QUANT_METHOD:</span>
                  <span className="text-on-surface">INT-8_PRECISION</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-outline">CONTEXT_CAP:</span>
                  <span className="text-on-surface">131,072_TOKENS</span>
                </div>
              </div>
            </div>
            <div className="pt-4 space-y-2">
              <button 
                onClick={onOpenModal}
                className="w-full py-4 bg-secondary text-on-secondary font-headline font-bold text-sm tracking-widest uppercase gold-glow"
              >
                PRIMARY ENGINE ACTIONS
              </button>
              <div className="grid grid-cols-2 gap-2">
                <button className="py-2 border border-outline-variant/30 text-on-surface font-headline font-bold text-[10px] uppercase hover:bg-surface-bright">Config JSON</button>
                <button className="py-2 border border-outline-variant/30 text-on-surface font-headline font-bold text-[10px] uppercase hover:bg-surface-bright">Logs Stream</button>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}

interface ModelRowProps {
  key?: React.Key;
  name: string;
  uuid: string;
  status: string;
  context: string;
  price: string;
  color: string;
  isDefault?: boolean;
  onClick: () => void;
}

function ModelRow({ name, uuid, status, context, price, color, isDefault, onClick }: ModelRowProps) {
  return (
    <div 
      onClick={onClick}
      className={`grid grid-cols-12 px-8 py-4 bg-background border-l-2 hover:bg-surface-container-high transition-colors group cursor-pointer`}
      style={{ borderLeftColor: color }}
    >
      <div className="col-span-5 flex items-center gap-4">
        <div className="w-1.5 h-1.5 rounded-none" style={{ backgroundColor: color, boxShadow: `0 0 8px ${color}80` }}></div>
        <div>
          <div className="flex items-center gap-2">
            <span className={`text-sm font-headline font-medium ${status === 'ERROR_OFFLINE' ? 'text-error' : 'text-primary'}`}>{name}</span>
            {isDefault && <span className="bg-secondary text-on-secondary text-[9px] px-2 py-0.5 font-label font-bold uppercase">Default</span>}
          </div>
          <div className="text-[10px] font-label text-outline mt-1 uppercase">UUID: {uuid}</div>
        </div>
      </div>
      <div className="col-span-2 flex items-center">
        <span className="text-[10px] px-2.5 py-1 font-label uppercase" style={{ backgroundColor: `${color}1a`, color }}>{status}</span>
      </div>
      <div className="col-span-2 flex items-center justify-end text-sm font-label text-on-surface">{context}</div>
      <div className="col-span-3 flex items-center justify-end gap-6">
        <span className="text-sm font-label text-on-surface">{price}</span>
        <div className="opacity-0 group-hover:opacity-100 flex gap-2">
          <button className="bg-secondary text-on-secondary px-3 py-1 font-headline font-bold text-[10px] uppercase gold-glow">Test</button>
          <button className="border border-outline-variant/30 text-on-surface px-3 py-1 font-headline font-bold text-[10px] uppercase hover:bg-surface-bright">Freeze</button>
        </div>
      </div>
    </div>
  );
}

function DeploymentScreen() {
  return (
    <div className="flex flex-col lg:flex-row h-full overflow-hidden w-full">
      <section className="flex-grow overflow-y-auto p-8 space-y-8 no-scrollbar">
        <div className="flex justify-between items-end">
          <div>
            <h1 className="text-4xl font-headline font-medium tracking-tighter text-primary uppercase">Tool Configuration</h1>
            <p className="text-gray-500 font-label text-xs tracking-[0.2em] mt-2 uppercase">ACTIVE MODULE: CORE_EXPANSION_V4</p>
          </div>
          <div className="flex gap-4">
            <div className="flex items-center gap-2 px-4 py-2 bg-surface-container-low">
              <span className="w-1.5 h-1.5 bg-[#00C851] rounded-full"></span>
              <span className="text-[10px] font-label text-gray-400 tracking-widest uppercase">Nodes: 14/14</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 bg-surface-container-low">
              <span className="w-1.5 h-1.5 bg-secondary rounded-full"></span>
              <span className="text-[10px] font-label text-gray-400 tracking-widest uppercase">Latency: 12ms</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          <ToolCard 
            icon={<Search className="w-6 h-6" />} 
            name="Google Search" 
            module="WEB_INDEX_API" 
            description="Execute advanced search queries across global indexes with neural filtering." 
            tags={['Web', 'Index']}
            active
          />
          <ToolCard 
            icon={<MapIcon className="w-6 h-6" />} 
            name="Maps Engine" 
            module="GEOSPATIAL_V2" 
            description="High-precision vector mapping and routing optimization protocols." 
            tags={['Geo', 'Visual']}
          />
          <ToolCard 
            icon={<Calculate className="w-6 h-6" />} 
            name="Compute Core" 
            module="MATH_ACCEL_X" 
            description="Arithmetic and complex algebraic computations with 256-bit precision." 
            tags={['Logic', 'Fast']}
            active
          />
          <ToolCard 
            icon={<CodeBlocks className="w-6 h-6" />} 
            name="Logic Script" 
            module="PYTHON_ENV_311" 
            description="Sandboxed execution environment for complex logic and data processing." 
            tags={['Python', 'Sandbox']}
            active
          />
          <ToolCard 
            icon={<Schema className="w-6 h-6" />} 
            name="Semantics" 
            module="RELATIONAL_GRAPH" 
            description="Map complex relationships between disparate data entities via knowledge node links." 
            tags={['RAG', 'Graph']}
          />
          <div className="border-2 border-dashed border-surface-container-high flex flex-col items-center justify-center p-6 hover:bg-surface-container-low/50 transition-all cursor-pointer group">
            <AddCircle className="w-10 h-10 text-gray-700 group-hover:text-primary mb-2" />
            <span className="font-headline text-xs font-bold text-gray-600 group-hover:text-primary uppercase tracking-widest">Install New Tool</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <SummaryCard label="Active Toolsets" value="08" />
          <SummaryCard label="API Call Vol" value="1.2M" subValue="/hr" />
          <SummaryCard label="Error Rate" value="0.02%" color="text-error" />
          <SummaryCard label="Uptime" value="99.99%" color="text-[#00C851]" />
        </div>
      </section>

      <aside className="w-full lg:w-96 bg-surface-container-low flex flex-col h-full border-l border-outline-variant/10">
        <div className="p-6 border-b border-outline-variant/10">
          <h2 className="font-headline text-lg font-bold text-on-surface uppercase tracking-tight">Tool Parameters</h2>
          <p className="text-[10px] font-label text-gray-500 tracking-widest mt-1 uppercase">SELECTED: GOOGLE SEARCH V2</p>
        </div>
        <div className="p-6 space-y-8 overflow-y-auto no-scrollbar">
          <ParameterSlider label="Result Density" value="15 items" />
          <ParameterSlider label="Neural Filter Temp" value="0.75" />
          <div className="space-y-4">
            <label className="font-headline text-xs font-bold text-gray-400 uppercase tracking-widest">Default Search Operator</label>
            <div className="bg-surface-container-lowest p-3 kinetic-focus border-b border-primary/30">
              <input className="bg-transparent border-none w-full text-xs font-label text-primary focus:ring-0 uppercase" type="text" defaultValue="site:*.edu" />
            </div>
          </div>
          <div className="space-y-4">
            <label className="font-headline text-xs font-bold text-gray-400 uppercase tracking-widest">Region Constraint</label>
            <div className="bg-surface-container-lowest p-3 kinetic-focus border-b border-primary/30">
              <select className="bg-transparent border-none w-full text-xs font-label text-primary focus:ring-0 uppercase">
                <option>Global Index</option>
                <option>EU West Cluster</option>
                <option>US East Cluster</option>
                <option>APAC Mainframe</option>
              </select>
            </div>
          </div>
          <button className="w-full py-4 bg-secondary text-on-secondary font-headline font-bold text-xs tracking-[0.2em] uppercase gold-glow hover:opacity-90 active:scale-[0.98] transition-all">
            Test tool sequence
          </button>
        </div>
        <div className="mt-auto bg-surface-container-lowest p-4 h-64 flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <span className="font-headline text-[10px] font-bold text-gray-500 uppercase tracking-widest">Execution logs</span>
            <Terminal className="w-4 h-4 text-gray-700" />
          </div>
          <div className="flex-grow overflow-y-auto font-label text-[10px] space-y-1.5 text-gray-500 custom-scrollbar">
            <LogEntry time="14:02:11" status="OK" message="SYS: INITIALIZING WEB_INDEX_API..." />
            <LogEntry time="14:02:12" status="OK" message="SYS: HANDSHAKE COMPLETED AT NODE_42" />
            <LogEntry time="14:02:14" status="INFO" message="TASK: PARSING SYSTEM_QUERY 'PEACOCK ENGINE'" />
            <LogEntry time="14:02:15" status="ERROR" message="WARN: LATENCY SPIKE DETECTED (124ms)" />
            <LogEntry time="14:02:16" status="OK" message="RES: 142 ENTITIES RECOVERED FROM CACHE" />
            <LogEntry time="14:02:18" status="OK" message="SYS: SEQUENCE TERMINATED_SUCCESSFULLY" />
          </div>
        </div>
      </aside>
    </div>
  );
}

function ToolCard({ icon, name, module, description, tags, active }: { icon: React.ReactNode, name: string, module: string, description: string, tags: string[], active?: boolean }) {
  return (
    <div className="bg-surface-container-low p-6 group hover:bg-surface-container transition-all cursor-pointer relative overflow-hidden">
      <div className="absolute top-0 right-0 p-2">
        <OpenInNew className="w-4 h-4 text-gray-700 group-hover:text-primary transition-colors" />
      </div>
      <div className="flex items-start gap-4 mb-6">
        <div className="w-12 h-12 bg-surface-container-lowest flex items-center justify-center text-primary">
          {icon}
        </div>
        <div>
          <h3 className="font-headline text-lg font-bold text-on-surface uppercase tracking-tight">{name}</h3>
          <p className="text-[10px] font-label text-gray-500 tracking-widest uppercase">MODULE: {module}</p>
        </div>
      </div>
      <p className="text-sm text-gray-400 mb-6 font-body leading-relaxed">{description}</p>
      <div className="flex items-center justify-between">
        <div className="flex gap-1">
          {tags.map(tag => (
            <span key={tag} className="px-2 py-0.5 bg-background text-[9px] font-label text-primary uppercase">{tag}</span>
          ))}
        </div>
        <label className="relative inline-flex items-center cursor-pointer">
          <input type="checkbox" className="sr-only peer" defaultChecked={active} />
          <div className="w-8 h-4 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-[#00C851]"></div>
        </label>
      </div>
    </div>
  );
}

function SummaryCard({ label, value, subValue, color }: { label: string, value: string, subValue?: string, color?: string }) {
  return (
    <div className="bg-surface-container p-4">
      <span className="font-label text-[10px] text-gray-500 uppercase tracking-widest">{label}</span>
      <div className={`text-2xl font-headline mt-1 ${color || 'text-on-surface'}`}>
        {value} {subValue && <span className="text-xs font-label text-gray-600">{subValue}</span>}
      </div>
    </div>
  );
}

function ParameterSlider({ label, value }: { label: string, value: string }) {
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <label className="font-headline text-xs font-bold text-gray-400 uppercase tracking-widest">{label}</label>
        <span className="font-label text-xs text-primary">{value}</span>
      </div>
      <input className="w-full h-1 bg-surface-container-lowest appearance-none cursor-pointer accent-primary" type="range" />
    </div>
  );
}

function CustomToolModal({ onClose }: { onClose: () => void }) {
  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[60] flex items-center justify-center bg-background/60 backdrop-blur-[12px] p-6"
    >
      <motion.div 
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="w-full max-w-3xl bg-surface-container-high/60 backdrop-blur-[12px] shadow-2xl overflow-hidden flex flex-col border-none"
      >
        <div className="px-8 py-6 flex justify-between items-center bg-surface-container-highest/20 border-b border-outline-variant/10">
          <div>
            <h2 className="font-headline text-2xl font-medium tracking-tight text-white uppercase">Custom Tool Creation</h2>
            <p className="font-mono text-[10px] text-primary-fixed-dim uppercase tracking-[0.2em] mt-1">ENGINEERING_OVERRIDE_ACTIVE</p>
          </div>
          <button onClick={onClose} className="text-outline hover:text-white transition-colors">
            <Close className="w-6 h-6" />
          </button>
        </div>

        <div className="p-8 space-y-8 overflow-y-auto max-h-[70vh] custom-scrollbar">
          <div className="grid grid-cols-2 gap-8">
            <div className="flex flex-col gap-2 kinetic-focus border-b border-outline-variant/30 py-2">
              <label className="font-headline text-[10px] font-medium uppercase tracking-widest text-outline">TOOL_NAME</label>
              <input className="bg-transparent border-none focus:ring-0 p-0 text-primary-fixed-dim font-mono placeholder:text-gray-700 text-sm uppercase" placeholder="E.G. VECTOR_PARSER_V1" type="text" />
            </div>
            <div className="flex flex-col gap-2 kinetic-focus border-b border-outline-variant/30 py-2">
              <label className="font-headline text-[10px] font-medium uppercase tracking-widest text-outline">ENDPOINT_URL</label>
              <input className="bg-transparent border-none focus:ring-0 p-0 text-primary-fixed-dim font-mono placeholder:text-gray-700 text-sm" placeholder="https://api.peacock.internal/v4/..." type="text" />
            </div>
          </div>

          <div className="flex flex-col gap-2 kinetic-focus border-b border-outline-variant/30 py-2">
            <label className="font-headline text-[10px] font-medium uppercase tracking-widest text-outline">TECHNICAL_DESCRIPTION</label>
            <textarea className="bg-transparent border-none focus:ring-0 p-0 text-primary-fixed-dim font-mono placeholder:text-gray-700 text-sm resize-none uppercase" placeholder="DEFINE THE OPERATIONAL PARAMETERS FOR THIS CUSTOM COMPONENT..." rows={2}></textarea>
          </div>

          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <label className="font-headline text-[10px] font-medium uppercase tracking-widest text-outline">AUTHORIZATION_HEADERS</label>
              <button className="text-secondary font-mono text-[10px] hover:underline uppercase">+ ADD_HEADER</button>
            </div>
            <div className="space-y-2">
              <HeaderRow name="X-API-KEY" value="********" type="password" />
              <HeaderRow name="Content-Type" value="application/json" type="text" disabled />
            </div>
          </div>

          <div className="grid grid-cols-4 gap-4">
            <ParamBox label="TIMEOUT" value="5000MS" />
            <ParamBox label="RETRY_LIMIT" value="03" />
            <ParamBox label="CACHING" value="ENABLED" color="text-[#00C851]" />
            <ParamBox label="LOGGING" value="VERBOSE" />
          </div>
        </div>

        <div className="px-8 py-6 bg-surface-container-highest/40 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-[6px] h-[6px] bg-[#00C851] gold-glow"></div>
            <span className="font-mono text-[9px] text-outline uppercase tracking-widest">VALID_CONFIGURATION_DETECTED</span>
          </div>
          <div className="flex gap-4">
            <button onClick={onClose} className="px-6 py-3 font-headline font-bold text-xs tracking-widest text-outline border border-outline-variant/20 hover:bg-white/5 transition-all uppercase">Abort_Sequence</button>
            <button className="px-10 py-3 bg-secondary text-on-secondary font-headline font-bold text-xs tracking-widest gold-glow active:scale-95 transition-all uppercase">Deploy Custom Tool</button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

function HeaderRow({ name, value, type, disabled }: { name: string, value: string, type: string, disabled?: boolean }) {
  return (
    <div className={`grid grid-cols-[1fr,1.5fr,40px] gap-4 items-center ${disabled ? 'opacity-60' : ''}`}>
      <div className="bg-surface-container-lowest/50 p-3 border-b border-outline-variant/30">
        <input className="w-full bg-transparent border-none focus:ring-0 p-0 text-[10px] font-mono text-primary uppercase" type="text" defaultValue={name} />
      </div>
      <div className="bg-surface-container-lowest/50 p-3 border-b border-outline-variant/30">
        <input className="w-full bg-transparent border-none focus:ring-0 p-0 text-[10px] font-mono text-white" type={type} defaultValue={value} />
      </div>
      <button className="text-error/60 hover:text-error transition-colors">
        <Close className="w-4 h-4" />
      </button>
    </div>
  );
}

function ParamBox({ label, value, color }: { label: string, value: string, color?: string }) {
  return (
    <div className="bg-surface-container-lowest/30 p-4 border-l border-primary/20">
      <div className="font-headline text-[9px] text-outline mb-1 uppercase">{label}</div>
      <div className={`font-mono text-xs ${color || 'text-white'}`}>{value}</div>
    </div>
  );
}
