import React from 'react';
import { MessageBubble, MessageProps } from './MessageBubble';

export const ChatKernel: React.FC<{ 
    messages: MessageProps[], 
    onSendMessage: (content: string) => void 
}> = ({ messages, onSendMessage }) => {
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const [input, setInput] = React.useState('');

  React.useEffect(() => {
    if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = () => {
    if (!input.trim()) return;
    onSendMessage(input);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full relative overflow-hidden bg-chrome-dark font-body">
        {/* System Banner */}
        <div className="h-10 border-b border-white/5 flex items-center justify-center bg-chrome-dark z-20">
            <div className="px-4 py-1 hw-panel-recessed flex items-center gap-2">
                <p className="font-body text-[10px] text-white/40 tracking-widest uppercase">
                    Encrypted Session Initialized • Thread_ID: 0XF4A2
                </p>
            </div>
        </div>

        {/* Transmission Stream (Message List) */}
        <div 
            ref={scrollRef}
            className="flex-1 overflow-y-auto p-6 space-y-8 scroll-smooth"
        >
            {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center opacity-[0.03] pointer-events-none">
                     <span className="material-symbols-outlined text-[120px]">memory</span>
                    <span className="font-headline text-5xl tracking-[1em] ml-[1em] uppercase">Synchronizing</span>
                </div>
            ) : (
                <div className="space-y-8">
                    {messages.map((msg) => (
                        <MessageBubble key={msg.id} {...msg} />
                    ))}
                </div>
            )}
        </div>

        {/* Input Area */}
        <footer className="p-6 bg-chrome-dark border-t border-white/5">
            <div className="max-w-4xl mx-auto">
                <div className="hw-panel-recessed group transition-all duration-300">
                    <div className="flex items-end gap-3 p-3">
                        <button className="flex-shrink-0 p-2 text-white/40 hover:text-cyber-gold transition-colors">
                            <span className="material-symbols-outlined">attach_file</span>
                        </button>
                        <textarea 
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            className="flex-1 bg-transparent border-none focus:ring-0 font-body text-sm text-white placeholder:text-white/30 resize-none py-2" 
                            placeholder="ENTER COMMAND OR QUERY..." 
                            rows={1}
                        />
                        <button 
                            onClick={handleSend}
                            className="hw-button-gold w-10 h-10 flex items-center justify-center"
                        >
                            <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>send</span>
                        </button>
                    </div>
                </div>
            </div>
        </footer>
    </div>
  );
};
