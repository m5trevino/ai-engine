import React from 'react';

export const BrandingLanding: React.FC = () => {
  return (
    <div className="h-full flex flex-col items-center justify-center px-6 pb-24 overflow-y-auto relative bg-chrome-dark text-gray-300 font-body">
        {/* Logo Section */}
        <div className="relative mb-12 text-center group">
            <div className="absolute -top-12 left-1/2 -translate-x-1/2 w-px h-10 bg-cyber-gold/30"></div>
            <div className="absolute -bottom-12 left-1/2 -translate-x-1/2 w-px h-10 bg-cyber-gold/30"></div>
            <div className="flex flex-col items-center gap-2">
                <span className="text-[10px] font-body tracking-[0.5em] text-cyber-gold/60 mb-2 uppercase">Intelligent Kernel</span>
                <h1 className="text-7xl md:text-9xl font-headline font-bold tracking-tighter hw-metallic-text flex items-baseline italic">
                    PEA<span className="text-cyber-gold not-italic">COCK</span>
                    <span className="text-xs font-body text-cyber-gold ml-2 mb-4 tracking-tighter">V1.0.4</span>
                </h1>
                <div className="w-48 h-[2px] bg-gradient-to-r from-transparent via-cyber-gold/50 to-transparent"></div>
            </div>
        </div>

        {/* Central Input Area */}
        <div className="w-full max-w-3xl">
            {/* Recessed Input Container */}
            <div className="hw-panel-recessed group transition-all duration-300">
                <div className="flex items-center p-2 min-h-[64px]">
                    <button className="p-3 text-white/40 hover:text-cyber-gold transition-colors flex items-center justify-center">
                        <span className="material-symbols-outlined">attach_file</span>
                    </button>
                    <input 
                        className="flex-1 bg-transparent border-none focus:ring-0 font-body text-sm placeholder:text-white/30 py-4 px-2 text-white" 
                        placeholder="Initiate sequence. Data streams accepted." 
                        type="text"
                    />
                    <div className="flex items-center gap-2 px-2">
                        <button className="p-3 text-white/40 hover:text-cyber-gold transition-colors">
                            <span className="material-symbols-outlined">image</span>
                        </button>
                        {/* Gold Send Button */}
                        <button className="hw-button-gold px-5 py-2 flex items-center justify-center">
                            <span className="material-symbols-outlined">arrow_forward</span>
                        </button>
                    </div>
                </div>
                <div className="px-5 py-2 bg-black/40 flex justify-between items-center border-t border-white/5">
                    <div className="flex gap-4">
                        <div className="flex items-center gap-1.5 opacity-40 hover:opacity-100 transition-opacity cursor-pointer">
                            <span className="material-symbols-outlined text-[14px] text-cyber-gold">language</span>
                            <span className="text-[9px] font-body tracking-widest uppercase text-white/60">Search</span>
                        </div>
                        <div className="flex items-center gap-1.5 opacity-40 hover:opacity-100 transition-opacity cursor-pointer">
                            <span className="material-symbols-outlined text-[14px] text-cyber-gold">memory</span>
                            <span className="text-[9px] font-body tracking-widest uppercase text-white/60">Deep Think</span>
                        </div>
                    </div>
                    <div className="text-[9px] font-body text-white/30 uppercase tracking-tighter">
                        Secure Line: 256-bit Encrypted
                    </div>
                </div>
            </div>

            {/* 4 Quick Action Cards - 3D Pop-out */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-8">
                <button className="hw-surface-3d p-4 text-left group">
                    <span className="material-symbols-outlined text-cyber-gold text-xl mb-3 block">auto_awesome</span>
                    <span className="text-[10px] font-body text-white/60 block uppercase tracking-wider leading-tight">Analyze system logs for anomalies</span>
                </button>
                <button className="hw-surface-3d p-4 text-left group">
                    <span className="material-symbols-outlined text-cyber-gold text-xl mb-3 block">code</span>
                    <span className="text-[10px] font-body text-white/60 block uppercase tracking-wider leading-tight">Optimise Vulkan pipeline buffers</span>
                </button>
                <button className="hw-surface-3d p-4 text-left group">
                    <span className="material-symbols-outlined text-cyber-gold text-xl mb-3 block">visibility</span>
                    <span className="text-[10px] font-body text-white/60 block uppercase tracking-wider leading-tight">Identify visual regressions in telemetry</span>
                </button>
                <button className="hw-surface-3d p-4 text-left group">
                    <span className="material-symbols-outlined text-cyber-gold text-xl mb-3 block">history</span>
                    <span className="text-[10px] font-body text-white/60 block uppercase tracking-wider leading-tight">Recall previous deployment states</span>
                </button>
            </div>
        </div>

        {/* Footer Meta */}
        <footer className="absolute bottom-6 left-1/2 -translate-x-1/2 w-full max-w-3xl flex justify-center items-center gap-8 opacity-30 hover:opacity-60 transition-opacity z-10">
            <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-cyber-gold rounded-full animate-pulse"></div>
                <span className="text-[9px] font-body tracking-widest text-white/60 uppercase">Network: Active</span>
            </div>
            <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-cyber-gold rounded-full"></div>
                <span className="text-[9px] font-body tracking-widest text-white/60 uppercase">Latency: 14ms</span>
            </div>
            <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-cyber-gold rounded-full"></div>
                <span className="text-[9px] font-body tracking-widest text-white/60 uppercase">Encrypt: AES-256</span>
            </div>
        </footer>

        {/* Background Decorative Grid */}
        <div className="absolute inset-0 pointer-events-none opacity-[0.02] overflow-hidden z-0">
            <div className="absolute inset-0" style={{ backgroundImage: 'linear-gradient(rgba(249, 217, 74, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(249, 217, 74, 0.1) 1px, transparent 1px)', backgroundSize: '40px 40px' }}></div>
        </div>
    </div>
  );
};
