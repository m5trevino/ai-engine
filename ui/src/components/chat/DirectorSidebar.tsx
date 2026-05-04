import React from 'react';

interface DirectorSidebarProps {
    models: any[];
    selectedModel: string;
    setSelectedModel: (id: string) => void;
    onConfigChange?: (config: any) => void;
}

export const DirectorSidebar: React.FC<DirectorSidebarProps> = ({ 
    models, 
    selectedModel, 
    setSelectedModel,
    onConfigChange 
}) => {
    const [temp, setTemp] = React.useState(0.7);
    const [system, setSystem] = React.useState("You are the Peacock Engine Controller. Prioritize system stability and low-latency responses above all. Use technical terminal aesthetics in all communications.");

    const handleTempChange = (val: number) => {
        setTemp(val);
        onConfigChange?.({ temp: val, system });
    };

    const handleSystemChange = (val: string) => {
        setSystem(val);
        onConfigChange?.({ temp, system: val });
    };

    return (
        <aside className="hidden xl:flex flex-col w-[320px] bg-[#0d0d0d] border-l border-white/5 overflow-hidden font-body">
            <div className="p-6 space-y-8 overflow-y-auto h-full">
                {/* Engine Model */}
                <section>
                    <h3 className="text-[10px] font-bold text-cyber-gold/50 tracking-widest uppercase mb-4">Engine_Model</h3>
                    <div className="relative">
                        <select 
                            value={selectedModel}
                            onChange={(e) => setSelectedModel(e.target.value)}
                            className="w-full hw-panel-recessed text-white/80 text-xs p-3 appearance-none focus:border-cyber-gold/50 focus:outline-none bg-transparent"
                        >
                            {models.map(m => (
                                <option key={m.id} value={m.id}>{m.id.toUpperCase()}</option>
                            ))}
                        </select>
                        <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-white/40 pointer-events-none text-sm">expand_more</span>
                    </div>
                </section>

                {/* System Instructions */}
                <section>
                    <h3 className="text-[10px] font-bold text-cyber-gold/50 tracking-widest uppercase mb-4">System_Instructions</h3>
                    <div className="hw-panel-recessed p-3">
                        <textarea 
                            value={system}
                            onChange={(e) => handleSystemChange(e.target.value)}
                            className="w-full bg-transparent border-none focus:ring-0 text-xs text-white/70 resize-none h-32" 
                            placeholder="Enter system prime directives..."
                        />
                    </div>
                </section>

                {/* Operator Persona */}
                <section>
                    <h3 className="text-[10px] font-bold text-cyber-gold/50 tracking-widest uppercase mb-4">Operator_Persona</h3>
                    <div className="grid grid-cols-2 gap-2">
                        <button className="p-2 hw-surface-3d text-cyber-gold text-[10px] text-center border-cyber-gold/30">
                            ANALYTICAL
                        </button>
                        <button className="p-2 hw-panel-recessed hover:border-white/30 text-white/50 text-[10px] text-center transition-colors">
                            CREATIVE
                        </button>
                        <button className="p-2 hw-panel-recessed hover:border-white/30 text-white/50 text-[10px] text-center transition-colors">
                            CONCISE
                        </button>
                        <button className="p-2 hw-panel-recessed hover:border-white/30 text-white/50 text-[10px] text-center transition-colors">
                            DEBUG
                        </button>
                    </div>
                </section>

                {/* Thermal Entropy */}
                <section>
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="text-[10px] font-bold text-cyber-gold/50 tracking-widest uppercase">Thermal_Entropy</h3>
                        <span className="text-[10px] text-cyber-gold">{temp.toFixed(1)}</span>
                    </div>
                    <div className="px-1">
                        <input 
                            type="range" 
                            className="w-full cursor-pointer accent-cyber-gold" 
                            min="0" max="100" 
                            value={temp * 100}
                            onChange={(e) => handleTempChange(parseInt(e.target.value) / 100)}
                        />
                        <div className="flex justify-between mt-2 text-[8px] text-white/30">
                            <span>STABLE</span>
                            <span>CREATIVE</span>
                        </div>
                    </div>
                </section>

                {/* System Toggles */}
                <section>
                    <h3 className="text-[10px] font-bold text-cyber-gold/50 tracking-widest uppercase mb-4">System_Toggles</h3>
                    <div className="space-y-3">
                        {[
                            { label: 'Stream Output', active: true },
                            { label: 'Code Highlight', active: true },
                            { label: 'Auto-Save', active: false }
                        ].map((toggle) => (
                            <div key={toggle.label} className="flex items-center justify-between p-3 hw-panel-recessed">
                                <span className="text-[11px] uppercase text-white/60">{toggle.label}</span>
                                <div className={`w-12 h-6 border border-[#444] relative cursor-pointer ${toggle.active ? 'border-cyber-gold shadow-[0_0_10px_rgba(249,217,74,0.2)]' : 'bg-[#0a0a0c]'}`}>
                                    <div className={`absolute top-0.5 w-[18px] h-[18px] transition-all duration-200 ${toggle.active ? 'right-0.5 bg-cyber-gold shadow-[0_0_10px_rgba(249,217,74,0.5)]' : 'left-0.5 bg-[#444]'}`} />
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

                <div className="mt-auto pt-6 border-t border-white/5 text-center">
                    <div className="text-[10px] text-white/20 tracking-widest uppercase">PEACOCK_SYSTEMS_GLOBAL</div>
                </div>
            </div>
        </aside>
    );
};
