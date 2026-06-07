import React from 'react';

export const Footer: React.FC<{ tokens?: string; billing?: string }> = ({ tokens = '0', billing = '$0.00' }) => {
  return (
    <footer className="bg-[#0b0f12] text-[#aac7ff] font-['JetBrains_Mono'] text-[10px] uppercase tracking-wide h-8 z-50 border-t border-[#1c2024] flex items-center justify-between px-4 shrink-0">
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
