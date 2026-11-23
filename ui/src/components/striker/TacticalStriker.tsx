import React from 'react';

interface MissionItem {
  id: string;
  name: string;
  status: 'STAGED' | 'REFINING' | 'SECURED' | 'FAILED';
  progress?: number;
}

interface TacticalStrikerProps {
  activeMission: string | null;
  items: MissionItem[];
  onUpload: (files: File[]) => void;
  onparcel: (missionId: string) => void;
}

export const TacticalStriker: React.FC<TacticalStrikerProps> = ({
  activeMission,
  items,
  onUpload,
  onparcel
}) => {
  const [isDragging, setIsDragging] = React.useState(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) onUpload(files);
  };

  return (
    <div className="flex flex-col h-full bg-[#0d0d0d] space-y-3 overflow-hidden font-body">
        <div className="flex-1 overflow-y-auto space-y-3 custom-scrollbar">
          {items.length === 0 && !activeMission ? (
            <div 
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                className={`h-full border border-dashed transition-all flex flex-col items-center justify-center gap-4 p-6 ${
                    isDragging ? 'border-cyber-gold bg-cyber-gold/5' : 'border-white/10 bg-black/20'
                }`}
            >
                <span className={`material-symbols-outlined text-4xl transition-all ${isDragging ? 'text-cyber-gold scale-110' : 'text-white/20'}`}>cloud_upload</span>
                <div className="text-center space-y-1">
                    <p className="text-[10px] text-white/40 tracking-widest uppercase">Staging_Zone_Active</p>
                    <p className="text-[8px] text-white/20 uppercase tracking-tighter">Drop manifest or files</p>
                </div>
            </div>
          ) : (
            <>
                {items.map((item) => (
                    <div 
                        key={item.id}
                        className={`p-3 bg-white/5 border transition-all ${item.status === 'REFINING' ? 'border-cyber-gold/30 bg-cyber-gold/5' : 'border-white/10'}`}
                    >
                        <div className="flex justify-between items-center text-[10px] mb-2 font-bold">
                            <span className="text-white/70 uppercase">ID: #{item.id.slice(-4)}</span>
                            <span className={`${item.status === 'SECURED' ? 'text-cyber-gold' : 'text-white/40'} uppercase tracking-widest`}>{item.status}</span>
                        </div>
                        <div className="h-3 bg-[#0a0a0c] border border-[#1a1a1c] relative overflow-hidden">
                            <div 
                                className={`h-full ${item.status === 'REFINING' ? 'bg-cyber-gold' : 'bg-white/20'} transition-all duration-500`} 
                                style={{ width: `${item.progress || (item.status === 'SECURED' ? 100 : 0)}%` }}
                            />
                        </div>
                    </div>
                ))}
                
                {/* Visual Connector/Slot */}
                <div className="p-4 border-dashed border border-white/5 flex flex-col items-center justify-center gap-2 opacity-40 hover:opacity-100 transition-all cursor-crosshair group hover:bg-white/5">
                    <span className="material-symbols-outlined text-white/20 group-hover:text-cyber-gold transition-colors">add_circle</span>
                    <span className="text-[8px] tracking-widest font-bold text-white/20 group-hover:text-cyber-gold transition-colors uppercase">Awaiting_Payload_0{items.length + 1}</span>
                </div>
            </>
          )}
        </div>
    </div>
  );
};
