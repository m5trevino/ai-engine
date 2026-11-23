import React from 'react';

export interface AnalyticsStats {
    rpm: number;
    tps: number;
    tokens: number;
    cost: number;
    success_rate: string;
}

export const AnalyticsPanel: React.FC<{ stats: AnalyticsStats }> = ({ stats }) => {
    return (
        <div className="w-full h-full flex items-center justify-around gap-4 font-body">
            {/* Throughput Gauge */}
            <div className="flex items-center gap-6">
                <div className="w-32 h-32 relative flex items-center justify-center border-2 border-[#1a1a1c] radar-scan overflow-hidden">
                    <div className="absolute inset-0 border-[6px] border-[#1a1a1c]/50 border-t-cyber-gold/60" />
                    <div className="absolute inset-4 border border-[#262528] border-dashed" />
                    <div className="flex flex-col items-center z-10">
                        <span className="text-4xl font-bold text-white font-headline tracking-widest italic">{stats.tps.toFixed(1)}</span>
                        <span className="text-[9px] text-cyber-gold font-bold uppercase tracking-tighter">TK/SEC</span>
                    </div>
                </div>
                <div className="space-y-2 border-l-2 border-[#1a1a1c] pl-6">
                    <h3 className="font-headline text-white/60 uppercase text-xs tracking-widest font-bold">Throughput</h3>
                    <p className="text-[10px] text-white/40 max-w-[160px] font-bold leading-tight uppercase">
                        NODE_01: STABLE<br/>
                        SUCCESS: {stats.success_rate}
                    </p>
                    <div className="flex gap-1.5">
                        {[1, 2, 3, 4].map(i => (
                            <div key={i} className={`w-2 h-4 ${i <= Math.ceil(stats.tps / 200) ? 'bg-cyber-gold' : 'bg-[#1a1a1c]'}`} />
                        ))}
                    </div>
                </div>
            </div>

            {/* Engine Stress Gauge */}
            <div className="flex items-center gap-6">
                <div className="w-32 h-32 relative flex items-center justify-center border-2 border-[#1a1a1c] radar-scan overflow-hidden">
                    <div className="absolute inset-0 border-[6px] border-[#1a1a1c]/50 border-r-cyber-gold/60" />
                    <div className="absolute inset-2 border border-[#1a1a1c]" />
                    <div className="flex flex-col items-center z-10">
                        <span className="text-4xl font-bold text-white font-headline tracking-widest italic">{stats.rpm}</span>
                        <span className="text-[9px] text-cyber-gold font-bold uppercase tracking-tighter">RPM</span>
                    </div>
                </div>
                <div className="space-y-2 border-l-2 border-[#1a1a1c] pl-6">
                    <h3 className="font-headline text-white/60 uppercase text-xs tracking-widest font-bold">Engine Stress</h3>
                    <p className="text-[10px] text-white/40 max-w-[160px] font-bold leading-tight uppercase">
                        TEMP: NOMINAL<br/>
                        LOAD: {((stats.rpm / 1000) * 10).toFixed(0)}%
                    </p>
                    <div className="flex gap-1.5">
                        {[1, 2, 3].map(i => (
                            <div key={i} className={`w-2 h-4 ${i <= Math.ceil(stats.rpm / 500) ? 'bg-cyber-gold' : 'bg-[#1a1a1c]'}`} />
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};
