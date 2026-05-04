import React from 'react';
import { Icons } from '../dashboard/MaterialIcons';

interface RefineryJob {
  id: string;
  name: string;
  progress: number;
  status: 'ACTIVE' | 'QUEUED' | 'COMPLETE';
}

export const RefineryPanel: React.FC<{ jobs: RefineryJob[] }> = ({ jobs }) => {
  return (
    <div className="flex flex-col h-full bg-black/40 p-4 space-y-4 border-l border-white/5">
      <div className="flex items-center gap-2">
        <Icons.Settings />
        <h2 className="text-xs uppercase tracking-[0.2em] font-bold text-white/60">The Refinery</h2>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 scrollbar-thin scrollbar-thumb-white/10 pr-2">
        {jobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full opacity-10">
            <Icons.Settings />
            <span className="text-[10px] uppercase tracking-widest mt-2 font-mono">Refinery Idle</span>
          </div>
        ) : (
          jobs.map(job => (
            <div 
              key={job.id}
              className="bg-black/60 border border-white/5 p-3 rounded-lg space-y-2 group"
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono text-white/50">{job.name}</span>
                <span className={`text-[9px] font-bold tracking-widest ${
                  job.status === 'ACTIVE' ? 'text-green-400' : 'text-white/20'
                }`}>
                  {job.status}
                </span>
              </div>
              
              <div className="relative h-1 bg-white/5 rounded-full overflow-hidden">
                <div 
                  className={`absolute top-0 left-0 h-full transition-all duration-500 ${
                    job.status === 'ACTIVE' ? 'bg-[#00FF41]' : 'bg-white/10'
                  }`}
                  style={{ width: `${job.progress}%` }}
                />
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-[9px] font-mono text-white/10">{job.progress}% COMPLETE</span>
                <Icons.Activity />
              </div>
            </div>
          ))
        )}
      </div>

      <div className="pt-4 border-t border-white/5">
        <button className="w-full py-2 bg-red-900/10 hover:bg-red-900/20 border border-red-500/20 text-[9px] uppercase tracking-widest font-bold text-red-400/60 rounded transition-all">
          Emergency Purge
        </button>
      </div>
    </div>
  );
};
