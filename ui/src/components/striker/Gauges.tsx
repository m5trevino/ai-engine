import React from 'react';

interface GaugeProps {
  label: string;
  value: string | number;
  sublabel?: string;
  trend?: 'up' | 'down' | 'neutral';
  color?: string;
}

export const Gauge: React.FC<GaugeProps> = ({ label, value, sublabel, trend, color = 'text-mil-cyan' }) => {
  return (
    <div className="bg-mil-charcoal-deep/40 border-l-2 border-white/5 p-5 flex flex-col gap-2 machined-shine shadow-box-recessed">
      <div className="flex justify-between items-start">
        <span className="text-[9px] uppercase tracking-[0.3em] text-mil-offwhite/30 font-headline font-bold">{label}</span>
        {trend && (
          <div className={`p-1 ${trend === 'up' ? 'text-mil-cyan bg-mil-cyan/10' : 'text-mil-magenta bg-mil-magenta/10'}`}>
             <span className="text-[10px] font-bold">{trend === 'up' ? '▲' : '▼'}</span>
          </div>
        )}
      </div>
      
      <div className="flex items-baseline gap-2">
        <span className={`text-3xl font-rugged tracking-widest ${color}`}>{value}</span>
      </div>
      
      {sublabel && (
        <div className="mt-2 pt-2 border-t border-white/5 flex items-center justify-between">
            <span className="text-[9px] text-mil-offwhite/20 font-mono tracking-widest uppercase">{sublabel}</span>
            <div className="flex gap-1">
                {[1,2,3,4].map(i => <div key={i} className={`h-2 w-1 ${i < 3 ? 'bg-mil-cyan' : 'bg-mil-olive-dark'}`} />)}
            </div>
        </div>
      )}
    </div>
  );
};

export const MetricsGrid: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-4">
      {children}
    </div>
  );
};
