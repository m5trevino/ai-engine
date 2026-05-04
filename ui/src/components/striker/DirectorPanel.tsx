import React from 'react';

interface DirectorPanelProps {
  models: any[];
  selectedModel: string;
  onModelSelect: (id: string) => void;
  onStrike: (payload: any) => void;
}

export const DirectorPanel: React.FC<DirectorPanelProps> = ({ models, selectedModel, onModelSelect, onStrike }) => {
  const [prompt, setPrompt] = React.useState('');
  const [settings, setSettings] = React.useState({
    temp: 0.7,
    top_p: 1.0,
    top_k: 40
  });

  const handleStrike = () => {
    if (!prompt.trim()) return;
    onStrike({ prompt, ...settings });
    setPrompt('');
  };

  return (
    <div className="h-full flex flex-col bg-[#0e0e10] overflow-hidden border-t-2 border-mil-olive-dark shadow-[inset_0_2px_10px_rgba(0,0,0,0.5)]">
      <div className="flex-1 p-5 space-y-6 overflow-y-auto scrollbar-tactical">
        {/* Model Selection Bay */}
        <div className="space-y-3">
          <label className="font-headline text-[10px] text-mil-offwhite/40 font-bold tracking-[0.3em] uppercase block">TARGET_GATEWAY</label>
          <div className="machined-shine shadow-box-popout p-[1px] relative group">
             <select 
                value={selectedModel}
                onChange={(e) => onModelSelect(e.target.value)}
                className="w-full bg-[#131416] border-none text-mil-cyan font-mono text-[11px] px-4 py-3 outline-none focus:glow-text-cyan appearance-none cursor-pointer relative z-10"
              >
                {models.map(m => (
                  <option key={m.id} value={m.id}>{m.id.toUpperCase()}</option>
                ))}
              </select>
              <div className="absolute right-4 top-1/2 -translate-y-1/2 w-2 h-2 border-r-2 border-b-2 border-mil-cyan/40 rotate-45 pointer-events-none group-hover:border-mil-cyan transition-colors" />
          </div>
        </div>

        {/* Tactical Parameters Array */}
        <div className="space-y-7">
           {/* Entropy Control */}
           <div className="space-y-4">
             <div className="flex justify-between items-baseline text-[10px] font-headline">
                <span className="text-mil-offwhite/40 tracking-widest uppercase">THERMAL_ENTROPY</span>
                <span className="text-mil-cyan glow-text-cyan font-bold tracking-widest">{settings.temp.toFixed(1)}</span>
             </div>
             <div className="h-[2px] w-full bg-mil-olive-dark/20 relative">
                 <div className="absolute top-0 left-0 h-full bg-gradient-to-r from-mil-cyan/10 to-mil-cyan/40" style={{ width: `${(settings.temp / 2) * 100}%` }} />
                 <input 
                    type="range" min="0" max="2" step="0.1" 
                    value={settings.temp}
                    onChange={(e) => setSettings({...settings, temp: parseFloat(e.target.value)})}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                  />
                  <div className="absolute top-1/2 -translate-y-1/2 w-4 h-[22px] bg-mil-cyan shadow-[0_0_15px_rgba(0,243,255,0.4)] border-t border-white/40 pointer-events-none" style={{ left: `calc(${(settings.temp / 2) * 100}% - 8px)` }} />
             </div>
           </div>

           {/* Nucleus Control */}
           <div className="space-y-4">
             <div className="flex justify-between items-baseline text-[10px] font-headline">
                <span className="text-mil-offwhite/40 tracking-widest uppercase">NUCLEUS_P</span>
                <span className="text-mil-cyan glow-text-cyan font-bold tracking-widest">{settings.top_p.toFixed(2)}</span>
             </div>
             <div className="h-[2px] w-full bg-mil-olive-dark/20 relative">
                 <div className="absolute top-0 left-0 h-full bg-gradient-to-r from-mil-cyan/10 to-mil-cyan/40" style={{ width: `${settings.top_p * 100}%` }} />
                 <input 
                    type="range" min="0" max="1" step="0.01" 
                    value={settings.top_p}
                    onChange={(e) => setSettings({...settings, top_p: parseFloat(e.target.value)})}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                  />
                   <div className="absolute top-1/2 -translate-y-1/2 w-4 h-[22px] bg-mil-cyan shadow-[0_0_15px_rgba(0,243,255,0.4)] border-t border-white/40 pointer-events-none" style={{ left: `calc(${settings.top_p * 100}% - 8px)` }} />
             </div>
           </div>
        </div>

        {/* Strike Directive Well */}
        <div className="space-y-3 flex-1 flex flex-col pt-2">
          <label className="font-headline text-[10px] text-mil-offwhite/40 font-bold uppercase tracking-[0.3em] block">MANUAL_DIRECTIVE</label>
          <div className="flex-1 shadow-box-recessed p-1 bg-[#050505]/60 machined-shine min-h-[120px]">
             <textarea 
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="w-full h-full bg-transparent border-none text-mil-offwhite/80 p-4 font-mono text-[11px] outline-none placeholder:text-mil-offwhite/10 resize-none leading-relaxed tracking-wide"
                placeholder="ENTER MISSION PARAMETERS // AWAITING INPUT..."
              />
          </div>
        </div>
      </div>

      <div className="p-6 bg-[#0c0c0e] border-t-2 border-mil-olive-dark shadow-[0_-4px_20px_rgba(0,0,0,0.5)]">
        <button 
          onClick={handleStrike}
          disabled={!prompt.trim()}
          className="w-full mil-btn mil-btn-accent font-rugged text-xs tracking-[0.4em] uppercase hover:shadow-[0_0_20px_rgba(255,140,0,0.4)] active:scale-[0.98] transition-all"
        >
          EXECUTE_STRIKE
        </button>
      </div>
    </div>
  );
};
