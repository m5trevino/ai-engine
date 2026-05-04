import React from 'react';

export interface MessageProps {
    role: 'engine' | 'operator';
    content: string;
    timestamp: string;
    id: string;
}

export const MessageBubble: React.FC<MessageProps> = ({ role, content, timestamp, id }) => {
    const isEngine = role === 'engine';
    
    return (
        <div className={`flex gap-4 max-w-4xl mx-auto w-full ${!isEngine ? 'flex-row-reverse' : ''}`}>
            {/* Avatar / Icon */}
            <div className={`flex-shrink-0 w-10 h-10 ${isEngine ? 'bg-gradient-to-br from-cyber-gold to-cyber-gold-dim flex items-center justify-center' : 'hw-panel-recessed flex items-center justify-center overflow-hidden'}`}>
                {isEngine ? (
                    <span className="material-symbols-outlined text-black" style={{ fontVariationSettings: "'FILL' 1" }}>smart_toy</span>
                ) : (
                    <div className="w-full h-full bg-chrome-light flex items-center justify-center text-white/40 font-bold text-sm">OP</div>
                )}
            </div>

            {/* Message Body */}
            <div className={`flex-1 space-y-2 ${!isEngine ? 'text-right' : ''}`}>
                <div className={`flex items-center gap-3 ${!isEngine ? 'justify-end' : ''}`}>
                    {isEngine ? (
                        <>
                            <span className="font-body text-[10px] font-bold text-cyber-gold tracking-widest uppercase">PEACOCK_ENGINE</span>
                            <span className="font-body text-[9px] text-white/30">{timestamp}</span>
                        </>
                    ) : (
                        <>
                            <span className="font-body text-[9px] text-white/30">{timestamp}</span>
                            <span className="font-body text-[10px] font-bold text-white/60 tracking-widest uppercase">OPERATOR_LEAD</span>
                        </>
                    )}
                </div>

                <div className={`${isEngine ? 'hw-message-bot' : 'hw-message-user inline-block text-left max-w-[80%]'} p-5 transition-all duration-300`}>
                    <div className="font-body text-sm leading-relaxed text-white/80 whitespace-pre-wrap">
                        {content}
                    </div>
                    
                    {/* Optional Code/Terminal block if engine */}
                    {isEngine && content.includes('```') && (
                        <div className="mt-4 p-4 bg-[#080808] border border-[#1a1a1c] box-shadow-inner font-body text-xs text-cyber-gold/70">
                            {/* In a real app we'd parse markdown here */}
                        </div>
                    )}

                    {/* Engine Telemetry Footer */}
                    {isEngine && (
                        <div className="mt-4 pt-4 border-t border-white/5 flex gap-6 text-[8px] font-body text-white/20 tracking-widest uppercase">
                            <span className="flex items-center gap-2"><span className="w-1 h-3 bg-cyber-gold/40" /> RTT: 0.04S</span>
                            <span className="flex items-center gap-2"><span className="w-1 h-3 bg-cyber-gold/40" /> COST: $0.0014</span>
                            <span className="flex items-center gap-2"><span className="w-1 h-3 bg-cyber-gold/40" /> ID: {id.slice(0,6)}</span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
