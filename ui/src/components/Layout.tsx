import React from 'react';

type Tab = 'DASHBOARD' | 'NEURAL LINK' | 'MODEL REGISTRY' | 'KEY VAULT' | 'STRIKER' | 'LIVE WIRE';

export const TABS: Tab[] = ['DASHBOARD', 'NEURAL LINK', 'MODEL REGISTRY', 'KEY VAULT', 'STRIKER', 'LIVE WIRE'];

export const TopNav: React.FC<{ active: Tab; onChange: (t: Tab) => void }> = ({ active, onChange }) => {
  return (
    <header className="bg-[#181c20] text-[#d6e2ff] font-['Space_Grotesk'] font-bold tracking-tighter uppercase fixed top-0 w-full h-16 z-50 border-b border-[#363a3e] flex justify-between items-center px-6">
      <div className="text-xl font-bold text-[#aac7ff] tracking-widest">PEACOCK ENGINE</div>
      <nav className="hidden md:flex items-center gap-8 text-xs">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => onChange(tab)}
            className={`transition-colors pb-1 ${active === tab ? 'text-[#aac7ff] border-b-2 border-[#f0cd2d]' : 'text-[#363a3e] hover:text-[#d6e2ff]'}`}
          >
            {tab}
          </button>
        ))}
      </nav>
      <div className="flex items-center gap-4">
        <span className="material-symbols-outlined text-[#aac7ff] hover:bg-[#1c2024] p-2 transition-all cursor-pointer">memory</span>
        <span className="material-symbols-outlined text-[#aac7ff] hover:bg-[#1c2024] p-2 transition-all cursor-pointer">notifications</span>
        <span className="material-symbols-outlined text-[#aac7ff] hover:bg-[#1c2024] p-2 transition-all cursor-pointer">settings</span>
        <div className="w-8 h-8 bg-surface-container-highest rounded-full overflow-hidden border border-outline-variant">
          <div className="w-full h-full bg-surface-bright" />
        </div>
      </div>
    </header>
  );
};

export const Footer: React.FC<{ tokens?: string; billing?: string }> = ({ tokens = '0', billing = '$0.00' }) => {
  return (
    <footer className="bg-[#0b0f12] text-[#aac7ff] font-['JetBrains_Mono'] text-[10px] uppercase tracking-wide fixed bottom-0 w-full h-8 z-50 border-t border-[#1c2024] flex items-center justify-between px-4">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 text-[#f0cd2d]">
          <span className="material-symbols-outlined text-sm">sensors</span>
          <span>ENGINE_STABLE_v3.0.0</span>
        </div>
        <div className="flex items-center gap-2 text-[#363a3e] hover:text-[#aac7ff] transition-colors cursor-default">
          <span className="material-symbols-outlined text-sm">lan</span>
          <span>PING: 12ms</span>
        </div>
      </div>
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 text-[#363a3e] hover:text-[#aac7ff] transition-colors cursor-default">
          <span className="material-symbols-outlined text-sm">toll</span>
          <span>TOKENS: {tokens}</span>
        </div>
        <div className="flex items-center gap-2 text-[#363a3e] hover:text-[#aac7ff] transition-colors cursor-default">
          <span className="material-symbols-outlined text-sm">payments</span>
          <span>BILLING: {billing}</span>
        </div>
      </div>
    </footer>
  );
};
