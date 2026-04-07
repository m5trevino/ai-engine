/**
 * PEACOCK CHAT - Frontend Logic
 */

// State
let currentConversationId = null;
let models = {};
let keys = {};
let isSending = false;

// DOM Elements
const modelSelect = document.getElementById('modelSelect');
const keySelect = document.getElementById('keySelect');
const tempSlider = document.getElementById('tempSlider');
const tempValue = document.getElementById('tempValue');
const formatSelect = document.getElementById('formatSelect');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const messagesContainer = document.getElementById('messages');
const conversationList = document.getElementById('conversationList');
const statusText = document.getElementById('statusText');
const tokenInfo = document.getElementById('tokenInfo');
const newChatBtn = document.getElementById('newChatBtn');
const historyBtn = document.getElementById('historyBtn');
const sidebar = document.getElementById('sidebar');

// Initialize
async function init() {
    await loadModels();
    await loadKeys();
    await loadConversations();
    setupEventListeners();
    
    // Start new conversation by default
    startNewChat();
}

// Load models from API
async function loadModels() {
    try {
        const response = await fetch('/v1/chat/models');
        models = await response.json();
        
        // Populate model select
        modelSelect.innerHTML = '<option value="">Select model...</option>';
        
        for (const [gateway, gatewayModels] of Object.entries(models)) {
            const optgroup = document.createElement('optgroup');
            optgroup.label = gateway.toUpperCase();
            
            gatewayModels.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = `${model.id} (${model.tier})`;
                optgroup.appendChild(option);
            });
            
            modelSelect.appendChild(optgroup);
        }
        
        // Select first model as default
        if (modelSelect.options.length > 1) {
            modelSelect.selectedIndex = 1;
        }
    } catch (error) {
        console.error('Failed to load models:', error);
        statusText.textContent = 'Error loading models';
    }
}

// Load keys from API
async function loadKeys() {
    try {
        const response = await fetch('/v1/keys');
        keys = await response.json();
        updateKeySelect();
    } catch (error) {
        console.error('Failed to load keys:', error);
    }
}

// Update key select based on selected model's gateway
function updateKeySelect() {
    const selectedModel = modelSelect.value;
    if (!selectedModel) return;
    
    // Find gateway for selected model
    let gateway = null;
    for (const [gw, gwModels] of Object.entries(models)) {
        if (gwModels.some(m => m.id === selectedModel)) {
            gateway = gw;
            break;
        }
    }
    
    // Populate key select
    keySelect.innerHTML = '<option value="">Auto-rotate</option>';
    
    if (gateway && keys[gateway]) {
        keys[gateway].keys.forEach(key => {
            const option = document.createElement('option');
            option.value = key;
            option.textContent = key;
            keySelect.appendChild(option);
        });
    }
}

// Load conversations
async function loadConversations() {
    try {
        const response = await fetch('/chat/api/conversations');
        const conversations = await response.json();
        
        conversationList.innerHTML = '';
        
        if (conversations.length === 0) {
            conversationList.innerHTML = '<div class="loading">No conversations yet</div>';
            return;
        }
        
        conversations.forEach(conv => {
            const item = document.createElement('div');
            item.className = 'conversation-item';
            item.dataset.id = conv.id;
            item.innerHTML = `
                <div class="title">${conv.title || 'Untitled'}</div>
                <div class="meta">${conv.model_id} • ${formatDate(conv.updated_at)}</div>
            `;
            item.onclick = () => loadConversation(conv.id);
            conversationList.appendChild(item);
        });
    } catch (error) {
        console.error('Failed to load conversations:', error);
        conversationList.innerHTML = '<div class="loading">Error loading conversations</div>';
    }
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
}

// Start new chat
function startNewChat() {
    currentConversationId = null;
    messagesContainer.innerHTML = `
        <div class="welcome-message">
            <h2>Welcome to PEACOCK CHAT</h2>
            <p>Select a model and start chatting. All conversations are automatically saved.</p>
        </div>
    `;
    messageInput.value = '';
    
    // Clear active state from conversation list
    document.querySelectorAll('.conversation-item').forEach(item => {
        item.classList.remove('active');
    });
}

// Load conversation
async function loadConversation(convId) {
    try {
        const response = await fetch(`/chat/api/conversations/${convId}/messages`);
        const data = await response.json();
        
        currentConversationId = convId;
        
        // Set model and key
        if (data.conversation) {
            modelSelect.value = data.conversation.model_id;
            updateKeySelect();
            if (data.conversation.key_account) {
                keySelect.value = data.conversation.key_account;
            }
        }
        
        // Display messages
        messagesContainer.innerHTML = '';
        data.messages.forEach(msg => {
            appendMessage(msg.role, msg.content, {
                tokens: msg.tokens_used,
                model: msg.model_id,
                key: msg.key_account
            });
        });
        
        // Update active state
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.id === convId) {
                item.classList.add('active');
            }
        });
        
        scrollToBottom();
    } catch (error) {
        console.error('Failed to load conversation:', error);
    }
}

// Append message to UI
function appendMessage(role, content, meta = {}) {
    const welcomeMsg = messagesContainer.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const avatar = role === 'user' ? '👤' : '🦚';
    
    let metaText = '';
    if (meta.tokens) {
        metaText += `${meta.tokens} tokens`;
    }
    if (meta.model) {
        metaText += metaText ? ` • ${meta.model}` : meta.model;
    }
    if (meta.key) {
        metaText += metaText ? ` • ${meta.key}` : meta.key;
    }
    
    // Escape HTML in content
    const escapedContent = escapeHtml(content);
    
    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div>
            <div class="message-content">${formatContent(escapedContent)}</div>
            ${metaText ? `<div class="message-meta">${metaText}</div>` : ''}
        </div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Format content (handle code blocks, etc)
function formatContent(content) {
    // Handle code blocks
    content = content.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre><code>${code.trim()}</code></pre>`;
    });
    
    // Handle inline code
    content = content.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Handle newlines
    content = content.replace(/\n/g, '<br>');
    
    return content;
}

// Scroll to bottom
function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Show typing indicator
function showTyping() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message assistant typing';
    typingDiv.id = 'typingIndicator';
    typingDiv.innerHTML = `
        <div class="message-avatar">🦚</div>
        <div class="message-content">
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    messagesContainer.appendChild(typingDiv);
    scrollToBottom();
}

// Hide typing indicator
function hideTyping() {
    const typing = document.getElementById('typingIndicator');
    if (typing) typing.remove();
}

// Send message
async function sendMessage() {
    if (isSending) return;
    
    const message = messageInput.value.trim();
    if (!message) return;
    
    const model = modelSelect.value;
    if (!model) {
        alert('Please select a model');
        return;
    }
    
    isSending = true;
    sendBtn.disabled = true;
    statusText.textContent = 'Sending...';
    
    // Add user message to UI
    appendMessage('user', message);
    messageInput.value = '';
    
    // Show typing indicator
    showTyping();
    
    try {
        const payload = {
            model: model,
            prompt: message,
            format: formatSelect.value,
            temp: parseInt(tempSlider.value) / 100
        };
        
        // Add specific key if selected
        if (keySelect.value) {
            payload.key = keySelect.value;
        }
        
        const response = await fetch('/v1/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        hideTyping();
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Request failed');
        }
        
        const data = await response.json();
        
        // Add assistant message to UI
        const content = typeof data.content === 'object' 
            ? JSON.stringify(data.content, null, 2) 
            : data.content;
        
        appendMessage('assistant', content, {
            tokens: data.usage?.total_tokens,
            model: data.model,
            key: data.key_used
        });
        
        // Update token info
        if (data.usage) {
            tokenInfo.textContent = `${data.usage.total_tokens} tokens (${data.duration_ms}ms)`;
        }
        
        // Save to conversation (the backend handles this)
        await loadConversations();
        
        statusText.textContent = 'Ready';
    } catch (error) {
        hideTyping();
        console.error('Failed to send message:', error);
        appendMessage('assistant', `Error: ${error.message}`, { model: 'system' });
        statusText.textContent = 'Error';
    } finally {
        isSending = false;
        sendBtn.disabled = false;
    }
}

// Setup event listeners
function setupEventListeners() {
    // Send button
    sendBtn.addEventListener('click', sendMessage);
    
    // Enter key (Shift+Enter to send)
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Temperature slider
    tempSlider.addEventListener('input', () => {
        tempValue.textContent = (tempSlider.value / 100).toFixed(1);
    });
    
    // Model change
    modelSelect.addEventListener('change', updateKeySelect);
    
    // New chat button
    newChatBtn.addEventListener('click', startNewChat);
    
    // History button (toggle sidebar on mobile)
    historyBtn.addEventListener('click', () => {
        sidebar.style.display = sidebar.style.display === 'none' ? 'block' : 'none';
    });
}

// Start
init();
