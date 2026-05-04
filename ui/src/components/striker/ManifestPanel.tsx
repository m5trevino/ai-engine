import React from 'react';
import { Icons } from '../dashboard/MaterialIcons';

interface ManifestItem {
  id: string;
  name: string;
  type: string;
  size: string;
}

interface ManifestPanelProps {
  items: ManifestItem[];
  onItemClick?: (item: ManifestItem) => void;
}

export const ManifestPanel: React.FC<ManifestPanelProps> = ({ items, onItemClick }) => {
  return (
    <div className="flex flex-col h-full bg-mil-charcoal/20 p-5 space-y-6 overflow-hidden">
      <div className="flex-1 overflow-y-auto space-y-3 scrollbar-tactical pr-2">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full opacity-10 gap-4">
            <div className="p-4 border-2 border-mil-olive-dark rounded-full">
                <Icons.Database className="w-12 h-12" />
            </div>
            <span className="font-headline text-[10px] uppercase tracking-[0.5em] mt-2">VAULT_OFFLINE</span>
          </div>
        ) : (
          items.map(item => (
            <div 
              key={item.id}
              onClick={() => onItemClick?.(item)}
              className="group flex flex-col p-4 machined-shine shadow-box-recessed hover:bg-white/5 transition-all cursor-pointer border-l-2 border-transparent hover:border-mil-cyan"
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono text-mil-offwhite/80 truncate max-w-[160px] uppercase tracking-tighter">{item.name}</span>
                <span className="text-[9px] text-mil-cyan font-headline font-bold opacity-40">{item.type}</span>
              </div>
              <div className="flex items-center justify-between mt-2">
                <span className="text-[9px] text-mil-offwhite/10 font-mono tracking-tighter">HASH: {item.id.slice(0, 8)}</span>
                <span className="text-[9px] text-mil-offwhite/20 font-mono italic">{item.size}</span>
              </div>
            </div>
          ))
        )}
        
        {/* Empty Slot Buffer */}
        <div className="p-4 shadow-box-recessed opacity-5 border-dashed border border-mil-olive flex items-center justify-center">
            <span className="font-mono text-[8px] tracking-[0.4em]">AWAITING_ALLOCATION</span>
        </div>
      </div>

      <div className="pt-4 border-t border-mil-olive-dark/40">
        <button className="w-full mil-btn text-[10px] font-headline tracking-[0.3em] font-bold text-mil-offwhite/40 hover:text-mil-cyan transition-all">
          SYNC_REMOTE_ARCHIVE
        </button>
      </div>
    </div>
  );
};
