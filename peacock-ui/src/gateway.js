/**
 * PEACOCK GATEWAY SDK
 * Unified interface for frontend-to-backend communication.
 */

const API_BASE = '/v1';

export const gateway = {
    /**
     * Executes a chat strike.
     * @param {Object} payload { model, prompt, temp, files, etc }
     */
    async strike(payload) {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error(`STRIKE_FAILURE: ${response.statusText}`);
        return await response.json();
    },

    /**
     * Executes a streaming chat strike.
     * @param {Object} payload { model, prompt, temp... }
     * @param {Function} onChunk Callback for each content chunk.
     * @param {Function} onMetadata Callback for the final metadata packet.
     */
    async streamStrike(payload, onChunk, onMetadata) {
        const response = await fetch(`${API_BASE}/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error(`STREAM_STRIKE_FAILURE: ${response.statusText}`);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            
            // Process SSE-style data lines
            const lines = buffer.split('\n\n');
            buffer = lines.pop(); // Keep partial line in buffer

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const jsonStr = line.replace('data: ', '');
                    try {
                        const packet = JSON.parse(jsonStr);
                        if (packet.type === 'content') {
                            onChunk(packet.content);
                        } else if (packet.type === 'metadata') {
                            onMetadata(packet);
                        } else if (packet.type === 'error') {
                            throw new Error(packet.content);
                        }
                    } catch (e) {
                        console.warn("MALFORMED_SSE_PACKET", e);
                    }
                }
            }
        }
    },

    /**
     * Lists all available models from registry.
     */
    async getModels() {
        const response = await fetch(`${API_BASE}/models`);
        return await response.json();
    },

    /**
     * Lists and audits all keys in the arsenal.
     */
    async getKeys() {
        const response = await fetch(`${API_BASE}/keys`);
        return await response.json();
    },

    /**
     * Retrieves conversation history or specific conversation.
     */
    async getConversations() {
        // Mocking for now, will wire to SQLite later
        return [
            { id: 'SYSTEM_OPTIMIZATION_V3', summary: 'Optimization strategy', tokens: '4.2k', time: '2m ago' },
            { id: 'DATABASE_MESH_REPAIR', summary: 'Repair ops', tokens: '12k', time: '1h ago' }
        ];
    },

    /**
     * Live Wire SSE Stream
     */
    streamTelemetry(onUpdate) {
        const eventSource = new EventSource(`${API_BASE}/telemetry/stream`);
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            onUpdate(data);
        };
        return eventSource;
    }
};
