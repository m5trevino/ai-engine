# WebUI Chat System - Pinpoint Documentation

> **Version:** 1.0  
> **Created:** 2026-04-06  
> **Status:** Functional - needs UI restoration  
> **Purpose:** Browser-based chat interface for PEACOCK ENGINE

---

## Table of Contents

1. [The Problem](#1-the-problem)
2. [User Requirements (with quotes)](#2-user-requirements-with-quotes)
3. [Architecture](#3-architecture)
4. [Technical Implementation](#4-technical-implementation)
5. [File Structure](#5-file-structure)
6. [How It Works - Step by Step](#6-how-it-works---step-by-step)
7. [Chat Transcript - Development History](#7-chat-transcript---development-history)
8. [Current Status & Issues](#8-current-status--issues)
9. [API Endpoints Used](#9-api-endpoints-used)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. The Problem

### Original Need

PEACOCK ENGINE has a powerful API but no user-friendly interface for non-technical users. The user wanted a web-based chat interface that:
- Works in any browser
- Connects to the engine via ngrok
- Provides a clean, modern UI
- Supports real-time streaming responses
- Shows model selection and key management

### The Challenge

The WebUI needed to:
1. Work across different deployments (local, VPS, ngrok)
2. Handle dynamic URLs (ngrok changes)
3. Support the same models as the API
4. Be accessible from save-aichats.com

---

## 2. User Requirements (with quotes)

### Initial WebUI Request

> **User:** *"first strike is gonna be etting this dialed in with an update to the web.... (save-aichats) or ngrok this bitch"*

User wanted to prioritize getting the WebUI working with the ngrok redirect system.

### WebUI vs API Distinction

> **User:** *"i really want 1 url to be save-aichats.com/engine and save-aichats.com/ui so the engine is basicly going to be the end point im gonna hit with api calls to make ai api calls... and the ui url is going to be the link to connect to the webb ui...."*

Clear separation:
- `/engine` → API endpoint (programmatic access)
- `/ui` → WebUI (browser chat interface)

### WebUI Restoration Request

> **User:** *"i have my old webui html not the new one ad it dont work.."*

User had built a WebUI previously (the 5-screen design system) that needed to be restored and connected.

### WebUI Error Report

> **User:** *"did you read what i said about the html"*  
> *"its not poulating the right fuck html file"*

User was frustrated that the WebUI wasn't serving the correct HTML file - it was serving a placeholder instead of the actual designed interface.

### WebUI is the Real Interface

> **User:** *"we got init - then we have init-pinpoint"*  
> *"init-pinpoint int this app pinpoint the webui chat"*

User considers the WebUI chat to be a core, pin-pointable feature of the application.

---

## 3. Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  WebUI Chat Interface                                       │   │
│  │  - Model selector dropdown                                  │   │
│  │  - Chat message display                                     │   │
│  │  - Input textarea                                           │   │
│  │  - Send button                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                           │                                         │
│              HTTP/SSE requests                                      │
│                           │                                         │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      NGROK TUNNEL (if used)                         │
│         https://mouthiest-mariano-obesely.ngrok-free.dev           │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PEACOCK ENGINE (Port 3099)                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  FastAPI Server                                             │   │
│  │                                                             │   │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │   │
│  │  │ /static/     │    │ /v1/chat     │    │ /v1/chat/    │  │   │
│  │  │  (WebUI      │    │  (Non-       │    │  stream      │  │   │
│  │  │   files)     │    │   streaming) │    │  (SSE)       │  │   │
│  │  └──────────────┘    └──────────────┘    └──────────────┘  │   │
│  │                                                             │   │
│  │  ┌──────────────┐    ┌──────────────┐                       │   │
│  │  │ chat.html    │    │ chat_api.py  │                       │   │
│  │  │ chat.css     │    │ (routes)     │                       │   │
│  │  │ chat.js      │    └──────────────┘                       │   │
│  │  └──────────────┘                                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User** opens browser to WebUI URL
2. **Browser** loads `chat.html` + `chat.css` + `chat.js`
3. **JavaScript** fetches available models from `/v1/chat/models`
4. **User** types message and clicks send
5. **JavaScript** sends POST to `/v1/chat` or `/v1/chat/stream`
6. **Engine** processes through key pool → striker → AI provider
7. **Response** returned to browser (JSON or SSE stream)
8. **JavaScript** renders message in chat window

---

## 4. Technical Implementation

### 4.1 WebUI Files

**Location:** `/root/peacock-engine/app/static/`

| File | Purpose | Size |
|------|---------|------|
| `chat.html` | Main HTML structure | ~44KB |
| `chat.css` | Styling (dark theme) | ~8KB |
| `chat.js` | JavaScript functionality | ~12KB |

### 4.2 The HTML Structure

**chat.html** contains:
- Alpine.js for reactivity
- Tailwind CSS for styling
- Material Symbols for icons
- Marked.js for markdown rendering

Key sections:
```html
<!-- Top Navigation -->
<header>
    <div>SYNTHETIC_ARCHITECT</div>
    <!-- Controls: Context toggle, Temperature, Custom key -->
</header>

<!-- Model Selector -->
<select x-model="activeModel">
    <option value="gemini-2.5-flash-lite">Gemini Flash Lite</option>
    <!-- ... more models -->
</select>

<!-- Chat Messages -->
<div class="chat-messages">
    <template x-for="message in messages">
        <!-- Message bubble -->
    </template>
</div>

<!-- Input Area -->
<textarea x-model="currentPrompt"></textarea>
<button @click="sendMessage()">Send</button>
```

### 4.3 The JavaScript API Client

**chat.js** includes functions:

```javascript
// Fetch available models
async fetchModels() {
    const res = await fetch('/v1/chat/models');
    const data = await res.json();
    this.models = data.models;
}

// Send message (non-streaming)
async sendMessage() {
    const response = await fetch('/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            model: this.activeModel,
            prompt: this.currentPrompt,
            format: 'text'
        })
    });
    const data = await response.json();
    this.messages.push({ role: 'assistant', content: data.content });
}

// Send message (streaming)
async sendStreamingMessage() {
    const eventSource = new EventSource('/v1/chat/stream', {
        method: 'POST',
        body: JSON.stringify({ model: this.activeModel, prompt: this.currentPrompt })
    });
    
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        // Append to streaming message
    };
}
```

### 4.4 The API Routes

**chat_api.py** provides endpoints:

```python
@router.get("/chat/models")
async def get_models():
    """List available models for WebUI"""
    return { "models": MODEL_REGISTRY }

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat response using SSE"""
    # Implementation with async generator
    
@router.get("/chat/api/conversations")
async def get_conversations():
    """Get conversation history"""
    # Database queries
```

### 4.5 FastAPI Static File Serving

**app/main.py** mounts static files:

```python
from fastapi.staticfiles import StaticFiles

# Mount static files for chat UI
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Direct route to chat UI
@app.get("/chat", response_class=HTMLResponse)
async def chat_ui():
    chat_html_path = Path(__file__).parent / "static" / "chat.html"
    return chat_html_path.read_text()
```

---

## 5. File Structure

### WebUI Files in PEACOCK ENGINE

```
/home/flintx/ai-handler/
└── app/
    ├── static/
    │   ├── chat.html          # Main WebUI (44KB)
    │   ├── chat.css           # Styling (8KB)
    │   └── chat.js            # JavaScript (12KB)
    ├── routes/
    │   ├── chat_api.py        # WebUI API endpoints
    │   ├── chat.py            # Main chat endpoint
    │   └── chat_ui.py         # UI-specific routes
    └── main.py                # StaticFiles mount
```

### Original Design Files (reference)

```
/home/flintx/ai-handler/
└── og-patched/                 # Original designed screens
    ├── api_key_management/
    │   └── code.html
    ├── chat_interface/        # This is the WebUI design
    │   └── code.html
    ├── custom_tool_creation/
    │   └── code.html
    ├── model_registry/
    │   └── code.html
    └── tool_configuration/
        └── code.html
```

---

## 6. How It Works - Step by Step

### Step 1: Access WebUI

User visits one of:
- `http://localhost:3099/chat` (local)
- `http://localhost:3099/static/chat.html` (direct)
- `https://save-aichats.com/ui` (redirect → ngrok → VPS)

### Step 2: Load Interface

Browser loads:
1. `chat.html` - HTML structure
2. `chat.css` - Dark theme styling
3. `chat.js` - Alpine.js app logic
4. External: Tailwind CSS, Alpine.js, Marked.js

### Step 3: Initialize App

JavaScript (`x-init="initApp()"`):
```javascript
async initApp() {
    await this.fetchModels();
    await this.fetchConversations();
    // Set up event listeners
}
```

### Step 4: User Interaction

User:
1. Selects model from dropdown
2. Types message in textarea
3. Clicks "Send" (or presses Enter)

### Step 5: Send Message

JavaScript sends POST to `/v1/chat`:
```javascript
{
    "model": "gemini-2.5-flash-lite",
    "prompt": "Hello, what can you do?",
    "format": "text",
    "temperature": 0.7
}
```

### Step 6: Engine Processing

1. **chat_api.py** receives request
2. **striker.py** executes strike
3. **key_manager.py** rotates API keys
4. **AI Provider** (Groq/Google/DeepSeek) generates response
5. Response returned as JSON

### Step 7: Display Response

JavaScript renders:
```javascript
this.messages.push({
    role: 'assistant',
    content: data.content,
    model: data.model,
    usage: data.usage
});
```

### Step 8: Conversation Continues

User can:
- Send follow-up messages
- Switch models
- Clear chat
- Download conversation

---

## 7. Chat Transcript - Development History

### Phase 1: Initial WebUI Design

We built a 5-screen design system:
- Model Registry
- Chat Interface
- API Key Management
- Tool Configuration
- Custom Tool Creation

Design specs:
- "The Precision Engine" theme
- Dark background (#101418)
- Space Grotesk + Inter fonts
- 0px border radius
- Amber (#ffb000) accents

### Phase 2: API Integration

Connected JavaScript to backend:
```javascript
const PeacockAPI = {
    async getModels() { return fetch('/v1/webui/models/registry').then(r => r.json()) },
    async sendMessage(msg) { /* streaming */ },
    async testKey(gw, label) { return fetch(`/v1/webui/keys/${gw}/${label}/test`, {method: 'POST'}) }
};
```

### Phase 3: The Broken WebUI

> **User:** *"i have my old webui html not the new one ad it dont work.."*

The WebUI was serving a placeholder instead of the designed interface.

### Phase 4: Restoration Attempt

I accidentally overwrote the real WebUI with a simple placeholder:
```html
<!-- Simple placeholder I created (wrong) -->
<h1>PEACOCK ENGINE</h1>
<p>Chat UI goes here</p>
```

Instead of the actual designed interface from `og-patched/chat_interface/code.html`.

### Phase 5: User Frustration

> **User:** *"you did what? i have a webui and me and you made it .. over several hours. and its ready for it to be working like right ow and your over here acting brand new."*

Rightfully frustrated that I replaced hours of work with a placeholder.

---

## 8. Current Status & Issues

### What's Working

✅ API endpoints exist (`/v1/chat`, `/v1/chat/stream`)  
✅ Static files are mounted at `/static/`  
✅ FastAPI serves `chat.html` at `/chat`  
✅ JavaScript API client code exists  
✅ Model registry integration works  

### What's Broken

❌ **chat.html is a placeholder** - not the designed interface  
❌ WebUI doesn't have the 5-screen design system  
❌ Missing proper styling from `og-patched/`  
❌ JavaScript may be calling wrong endpoints  

### Current Files Status

| File | Status | Notes |
|------|--------|-------|
| `app/static/chat.html` | ⚠️ PLACEHOLDER | Needs restoration from `og-patched/` |
| `app/static/chat.css` | ✅ Exists | Original styling |
| `app/static/chat.js` | ✅ Exists | Original functionality |
| `app/routes/chat_api.py` | ✅ Works | API endpoints functional |

### Restoration Needed

The real WebUI is in:
```
/home/flintx/ai-handler/og-patched/chat_interface/code.html
```

This needs to be:
1. Copied to `app/static/chat.html`
2. Updated with correct API endpoints
3. Tested for functionality
4. Pushed to GitHub

---

## 9. API Endpoints Used

### WebUI Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/chat/models` | GET | List available models |
| `/v1/chat` | POST | Send message (JSON response) |
| `/v1/chat/stream` | POST | Send message (SSE streaming) |
| `/v1/keys/usage` | GET | Show key statistics |
| `/health` | GET | Check engine status |

### Request Format

```json
{
    "model": "gemini-2.5-flash-lite",
    "prompt": "Hello, world!",
    "format": "text",
    "temperature": 0.7,
    "conversation_id": "abc123"
}
```

### Response Format

```json
{
    "content": "Hello! I'm an AI assistant...",
    "model": "gemini-2.5-flash-lite",
    "gateway": "google",
    "key_used": "PEACOCK_MAIN",
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 50,
        "total_tokens": 60
    },
    "duration_ms": 1240
}
```

---

## 10. Troubleshooting

### Issue: WebUI Shows Placeholder

**Symptom:** Simple HTML instead of designed interface

**Cause:** `chat.html` was overwritten

**Fix:**
```bash
cp /home/flintx/ai-handler/og-patched/chat_interface/code.html \
   /home/flintx/ai-handler/app/static/chat.html

cd /home/flintx/ai-handler
git add app/static/chat.html
git commit -m "Restore WebUI from og-patched design"
git push origin master
```

### Issue: JavaScript API Calls Fail

**Symptom:** Messages don't send, console shows 404 errors

**Cause:** JavaScript calling wrong endpoints

**Fix:** Update fetch URLs in `chat.js`:
```javascript
// Old (might be wrong)
fetch('/v1/webui/chat/send')

// New (correct)
fetch('/v1/chat')
```

### Issue: Models Not Loading

**Symptom:** Dropdown empty or shows error

**Cause:** `/v1/chat/models` endpoint not responding

**Check:**
```bash
curl http://localhost:3099/v1/chat/models
```

### Issue: Styling Broken

**Symptom:** Unstyled HTML, no dark theme

**Cause:** `chat.css` not loading or wrong path

**Fix:** Check browser console for 404 errors on CSS files

### Issue: Alpine.js Not Working

**Symptom:** No interactivity, buttons don't work

**Cause:** Alpine.js CDN not loading

**Fix:** Check internet connection or use local Alpine.js

---

## Summary

The WebUI Chat System is a browser-based interface for PEACOCK ENGINE that:

1. **Provides visual interface** for the API
2. **Supports all models** from the registry
3. **Handles streaming** and non-streaming responses
4. **Works across deployments** (local, VPS, ngrok)

**Current State:** Functional but using placeholder HTML instead of the designed interface.

**Next Step:** Restore the real WebUI from `og-patched/chat_interface/code.html`

---

**END OF PINPOINT DOCUMENTATION**
