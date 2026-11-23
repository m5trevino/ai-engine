/**
 * PEACOCK CHAT LOGIC
 * Manages conversation state and strike interactions.
 */

import { gateway } from './gateway';
import { ui } from './ui_shared';

export const chat = {
    messages: [],
    currentModel: 'models/gemini-2.0-flash-lite-001',
    
    init() {
        this.setupEventListeners();
        this.loadConversations();
    },

    setupEventListeners() {
        const sendBtn = document.getElementById('send-prompt-btn') || document.querySelector('button.gold-glow');
        const input = document.querySelector('textarea');
        
        if (sendBtn) {
            sendBtn.onclick = () => this.sendMessage();
        }

        if (input) {
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }
    },

    async sendMessage() {
        const input = document.querySelector('textarea');
        const prompt = input.value.trim();
        if (!prompt) return;

        // Clear input
        input.value = '';

        // Add user message to UI
        this.appendMessage('OPERATOR', prompt, 'user');

        // Create initial empty AI bubble
        const aiBubbleId = `ai-msg-${Date.now()}`;
        this.appendMessage('PEACOCK_ENGINE', '', 'ai', { id: aiBubbleId });

        const aiBubbleContainer = document.getElementById(aiBubbleId);
        const aiTextEl = aiBubbleContainer ? aiBubbleContainer.querySelector('p') : null;
        let fullContent = "";

        try {
            await gateway.streamStrike(
                {
                    model: this.currentModel,
                    prompt: prompt
                },
                (chunk) => {
                    fullContent += chunk;
                    if (aiTextEl) {
                        aiTextEl.textContent = fullContent;
                        // Auto-scroll as content grows
                        const container = document.getElementById('chat-scroller');
                        if (container) container.scrollTo(0, container.scrollHeight);
                    }
                },
                (metadata) => {
                    console.log("STRIKE_COMPLETE", metadata);
                    if (aiBubbleContainer && metadata.duration_ms) {
                        const metaDiv = document.createElement('div');
                        metaDiv.className = 'mt-2 text-[9px] text-outline font-label uppercase';
                        metaDiv.textContent = `GEN_TIME: ${(metadata.duration_ms / 1000).toFixed(2)}s | TOKENS: ${metadata.usage.total_tokens}`;
                        aiBubbleContainer.querySelector('.bg-surface-container').appendChild(metaDiv);
                    }
                    ui.updateStats();
                }
            );
        } catch (err) {
            console.error("STRIKE_FAILURE", err);
            if (aiTextEl) {
                aiTextEl.textContent = `FAILURE: ${err.message}`;
                aiTextEl.classList.add('text-error');
            }
        }
    },

    appendMessage(role, content, type, meta = {}) {
        const container = document.getElementById('chat-scroller') || document.querySelector('main > div:first-child');
        if (!container) return;

        const time = new Date().toLocaleTimeString();
        const msgDiv = document.createElement('div');
        if (meta.id) msgDiv.id = meta.id;
        
        if (type === 'user') {
            msgDiv.className = 'flex flex-col items-end gap-3 animate-in slide-in-from-right duration-300';
            msgDiv.innerHTML = `
                <div class="bg-surface-container-high p-4 max-w-[85%] border-l border-primary/20">
                    <p class="text-sm leading-relaxed text-on-surface">${content}</p>
                </div>
                <div class="flex items-center gap-2 font-label text-[9px] text-outline uppercase tracking-wider">
                    <span>${role}</span> <span class="text-primary-fixed-dim">${time}</span>
                </div>
            `;
        } else {
            msgDiv.className = 'flex flex-col items-start gap-3 animate-in slide-in-from-left duration-300';
            msgDiv.innerHTML = `
                <div class="flex items-center gap-3 mb-1">
                    <div class="w-6 h-6 bg-primary flex items-center justify-center">
                        <span class="material-symbols-outlined text-on-primary text-sm" style="font-variation-settings: 'FILL' 1;">bolt</span>
                    </div>
                    <span class="font-headline text-xs font-bold tracking-widest text-primary uppercase">${role}</span>
                </div>
                <div class="bg-surface-container p-5 max-w-[90%] border-l border-secondary/20">
                    <p class="text-sm leading-relaxed text-on-surface whitespace-pre-wrap">${content}</p>
                    ${meta.duration_ms ? `<div class="mt-2 text-[9px] text-outline font-label uppercase">GEN_TIME: ${(meta.duration_ms/1000).toFixed(2)}s</div>` : ''}
                </div>
            `;
        }

        container.appendChild(msgDiv);
        container.scrollTo(0, container.scrollHeight);
    },

    async loadConversations() {
        const historyContainer = document.querySelector('aside .flex-1.overflow-y-auto');
        if (!historyContainer) return;

        const convs = await gateway.getConversations();
        // Skip placeholders already in HTML, then prepend new ones if needed.
    }
};

window.addEventListener('DOMContentLoaded', () => chat.init());
