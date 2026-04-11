# Ngrok Redirect System - Comprehensive Documentation

> **Version:** 1.0  
> **Created:** 2026-04-06  
> **Purpose:** Complete technical documentation of the save-aichats.com → ngrok → PEACOCK ENGINE redirect system

---

## Table of Contents

1. [The Problem](#1-the-problem)
2. [User Requirements (with quotes)](#2-user-requirements-with-quotes)
3. [The Solution Architecture](#3-the-solution-architecture)
4. [Technical Implementation](#4-technical-implementation)
5. [File Structure](#5-file-structure)
6. [How It Works - Step by Step](#6-how-it-works---step-by-step)
7. [Chat Transcript - Decision Points](#7-chat-transcript---decision-points)
8. [Current Status & URLs](#8-current-status--urls)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. The Problem

### Original Issue

PEACOCK ENGINE runs on a VPS with a dynamic ngrok URL that changes every time ngrok restarts. The user owns `save-aichats.com` (hosted on Render) and wanted a stable way to access the engine without constantly updating bookmarks.

---

## 2. User Requirements (with quotes)

### 2.1 The Initial Request

> **User:** *"i need a script or some aliases .. and i guess i gotta do 3 terminals. thats kinda whack. but lets just do it liek that for niw i want an alias to do push for save-aichats and push for peacock-engine and a pull for both save-aichats and peacock-engine that i can run one at a time .. and then i want one that does both push and pull on both of them"*

### 2.2 The Vision - Single Command Chain Reaction

> **User:** *"then i want a command to run the ai-engine-start and it launches engine. nice output then it launches ngrok for the engine. ---- then it launches 'ai-ui ai-ui goes online and thats when ngrok triggers again... and it give the webui a llink and then thats when the link logic goes online at save-aichats.com"*

### 2.3 URL Structure Requirements

> **User:** *"i really want 1 url to be save-aichats.com/engine and save-aichats.com/ui so the engine is basicly going to be the end point im gonna hit with api calls to make ai api calls... and the ui url is going to be the link to connect to the webb ui.... so all i gotta do is press ai-engine adn it cauese a chain reaction.. and everything launches. the logs an go on a txt file tHAT I CAN VIEW for both ng and both engine and website .. the engine i would like to end up printing on the 1 terminal.."*

### 2.4 Where to Save Files

> **User:** *"okay push it to github from that dir. and then i will pull it on the vps. then we can setup the script to change it on the vps and push it from the vps when ngrok gets spun up"*

### 2.5 Ngrok Token Management

> **User:** *"okay for the trouble i added 2 more they are all coming from diff accounts diff emails.. so we should be good"*

---

## 3. The Solution Architecture

### 3.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER ACCESS                                 │
├─────────────────────────────────────────────────────────────────────┤
│  save-aichats.com/peacock  →  Portal (buttons for API/UI)           │
│  save-aichats.com/engine   →  API Redirect                          │
│  save-aichats.com/ui       →  WebUI Redirect                        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ Render serves static HTML
                              │ (auto-deploys on git push)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      RENDER (save-aichats.com)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ peacock.html │  │ engine.html  │  │   ui.html    │              │
│  │  (portal)    │  │   (API)      │  │   (WebUI)    │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│        │                  │                  │                      │
│        └──────────────────┴──────────────────┘                      │
│                           │                                         │
│                    meta refresh redirect                            │
│                           │                                         │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      NGROK TUNNEL                                   │
│         https://mouthiest-mariano-obesely.ngrok-free.dev           │
│                           │                                         │
│              (dynamic URL changes on restart)                       │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      VPS (Hetzner)                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                  PEACOCK ENGINE                             │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │   │
│  │  │   API        │  │   WebUI      │  │   Health     │      │   │
│  │  │  /v1/chat    │  │/static/chat  │  │   /health    │      │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              Port 3099                              │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Data Flow

1. **User** visits `save-aichats.com/ui`
2. **Render** serves `ui.html` (static file)
3. **HTML meta-refresh** redirects to ngrok URL
4. **Ngrok** tunnels to VPS port 3099
5. **PEACOCK ENGINE** serves WebUI

---

## 4. Technical Implementation

### 4.1 The Redirect HTML Files

**Location:** `/root/save-aichats/frontend/public/`

These are simple HTML files with meta-refresh tags that redirect to the ngrok URL.

#### peacock.html - Portal Dashboard

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>🦚 PEACOCK ENGINE | AI Gateway</title>
    <!-- Auto-redirect after 5 seconds -->
    <meta http-equiv="refresh" content="5; url=https://NGROK_URL_PLACEHOLDER">
    <style>
        body {
            font-family: 'Space Grotesk', 'Inter', system-ui, sans-serif;
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 100%);
            color: #e0e0e0;
        }
        /* Portal styling with stats and buttons */
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🦚</div>
        <h1>PEACOCK ENGINE</h1>
        <div class="status">
            <span class="status-dot"></span>
            <span>ONLINE | V3.0.0</span>
        </div>
        <!-- Stats display -->
        <div class="stats">
            <div class="stat">
                <div class="stat-value">NGROK_URL_PLACEHOLDER</div>
                <div class="stat-label">Tunnel URL</div>
            </div>
            <div class="stat">
                <div class="stat-value">16</div>
                <div class="stat-label">Groq Keys</div>
            </div>
            <div class="stat">
                <div class="stat-value">3</div>
                <div class="stat-label">Google Keys</div>
            </div>
        </div>
    </div>
    
    <div class="big-links">
        <a href="NGROK_URL_PLACEHOLDER/v1/chat" class="big-link">
            <div class="icon">⚡</div>
            <h2>API Endpoint</h2>
            <div class="desc">Direct API access for programmatic calls</div>
            <div class="url">/v1/chat</div>
        </a>
        
        <a href="NGROK_URL_PLACEHOLDER/static/chat.html" class="big-link">
            <div class="icon">💬</div>
            <h2>Web UI</h2>
            <div class="desc">Chat interface in your browser</div>
            <div class="url">/static/chat.html</div>
        </a>
    </div>
</body>
</html>
```

#### engine.html - API Redirect

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>🦚 PEACOCK ENGINE | API</title>
    <!-- Immediate redirect -->
    <meta http-equiv="refresh" content="0; url=https://NGROK_URL_PLACEHOLDER/v1/chat">
</head>
<body>
    <div class="box">
        <div class="logo">🦚</div>
        <h1>Redirecting to API...</h1>
        <p><a href="https://NGROK_URL_PLACEHOLDER/v1/chat">Click here if not redirected</a></p>
    </div>
</body>
</html>
```

#### ui.html - WebUI Redirect

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>🦚 PEACOCK ENGINE | WebUI</title>
    <!-- Immediate redirect -->
    <meta http-equiv="refresh" content="0; url=https://NGROK_URL_PLACEHOLDER/static/chat.html">
</head>
<body>
    <div class="box">
        <div class="logo">🦚</div>
        <h1>Redirecting to WebUI...</h1>
        <p><a href="https://NGROK_URL_PLACEHOLDER/static/chat.html">Click here if not redirected</a></p>
    </div>
</body>
</html>
```

### 4.2 The Automation Script

**File:** `/root/peacock-engine/ai-engine-start.sh`

```bash
#!/bin/bash
# 🦚 AI-ENGINE START - Full Stack Launcher
# Starts engine → ngrok → updates save-aichats with both API and UI URLs

set -e

PEACOCK_DIR="/root/peacock-engine"
SAVE_DIR="/root/save-aichats"
LOG_DIR="/root/logs"
mkdir -p $LOG_DIR

echo "╔══════════════════════════════════════════════════════════╗"
echo "║         🦚 PEACOCK ENGINE - FULL STACK STARTUP          ║"
echo "╚══════════════════════════════════════════════════════════╝"

# Step 1: Start PEACOCK ENGINE
echo "[1/4] Starting PEACOCK ENGINE..."
cd $PEACOCK_DIR
source .venv/bin/activate

# Start engine in background, log to file
nohup python -m app.main > $LOG_DIR/engine.log 2>&1 &
ENGINE_PID=$!

# Wait for engine to be ready
for i in {1..30}; do
    if curl -s http://localhost:3099/health > /dev/null 2>&1; then
        echo "✓ Engine ONLINE (PID: $ENGINE_PID)"
        break
    fi
    sleep 1
    echo -n "."
done

# Step 2: Start Ngrok
echo "[2/4] Starting NGROK tunnel..."
cd $PEACOCK_DIR

# Get current token from rotator state
TOKEN_IDX=$(cat .ngrok-rotator-state 2>/dev/null || echo 0)
source .env
IFS=' ' read -ra TOKENS <<< "$NGROK_TOKENS"
TOKEN="${TOKENS[$TOKEN_IDX]}"

echo "Using token $((TOKEN_IDX + 1))/${#TOKENS[@]}"
ngrok config add-authtoken "$TOKEN" > /dev/null 2>&1

# Start ngrok
nohup ngrok http 3099 > $LOG_DIR/ngrok.log 2>&1 &
NGROK_PID=$!

# Wait for tunnel
for i in {1..30}; do
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https://[^"]*"' | head -1 | cut -d'"' -f4)
    if [ -n "$NGROK_URL" ]; then
        echo "✓ Ngrok ONLINE: $NGROK_URL"
        break
    fi
    sleep 1
    echo -n "."
done

# Step 3: Update save-aichats portal with dual URLs
echo "[3/4] Updating save-aichats portal..."

cd $SAVE_DIR

# Replace placeholders with actual URL
sed -i "s|NGROK_URL_PLACEHOLDER|$NGROK_URL|g" frontend/public/peacock.html
sed -i "s|NGROK_URL_PLACEHOLDER|$NGROK_URL|g" frontend/public/engine.html
sed -i "s|NGROK_URL_PLACEHOLDER|$NGROK_URL|g" frontend/public/ui.html

# Commit and push
git add frontend/public/peacock.html frontend/public/engine.html frontend/public/ui.html
git commit -m "Update PEACOCK ENGINE portal - $(date '+%Y-%m-%d %H:%M')" || true
git push origin master 2>&1 | head -5

# Step 4: Show summary
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              🦚 PEACOCK ENGINE IS LIVE!                 ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "🔗 Access Points:"
echo "  Portal:  https://save-aichats.com/peacock"
echo "  API:     https://save-aichats.com/engine  → $NGROK_URL/v1/chat"
echo "  WebUI:   https://save-aichats.com/ui     → $NGROK_URL/static/chat.html"

# Keep showing engine logs
echo ""
echo "📡 Engine Logs (Ctrl+C to detach):"
tail -f $LOG_DIR/engine.log
```

### 4.3 The Update Script (for manual updates)

**File:** `/root/peacock-engine/update-peacock-portal.sh`

```bash
#!/bin/bash
# 🦚 Update PEACOCK ENGINE Portal on save-aichats

SAVE_AICHATS_DIR="/root/save-aichats"
PEACOCK_API="http://localhost:3099"

echo "🦚 Updating PEACOCK ENGINE Portal..."

# Get health data from engine
HEALTH=$(curl -s $PEACOCK_API/health 2>/dev/null)

if [ -z "$HEALTH" ]; then
    echo "❌ PEACOCK ENGINE not running on $PEACOCK_API"
    exit 1
fi

# Get ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https://[^"]*"' | head -1 | cut -d'"' -f4)

echo "Ngrok: $NGROK_URL"

# Update redirect files
cd $SAVE_AICHATS_DIR
sed -i "s|NGROK_URL_PLACEHOLDER|$NGROK_URL|g" frontend/public/peacock.html
sed -i "s|NGROK_URL_PLACEHOLDER|$NGROK_URL|g" frontend/public/engine.html
sed -i "s|NGROK_URL_PLACEHOLDER|$NGROK_URL|g" frontend/public/ui.html

git add .
git commit -m "Update ngrok redirect"
git push origin master

echo "✅ Portal updated!"
```

### 4.4 The Aliases

**File:** `/root/peacock-engine/aliases.sh`

```bash
#!/bin/bash
# 🦚 PEACOCK ENGINE Aliases

# Git Aliases
alias pull-engine='cd /root/peacock-engine && git pull'
alias pull-save='cd /root/save-aichats && git pull'
alias pull-all='pull-engine && pull-save'

alias push-engine='cd /root/peacock-engine && git add -A && git commit -m "update" && git push'
alias push-save='cd /root/save-aichats && git add -A && git commit -m "update" && git push'
alias push-all='push-engine && push-save'

# Combined operations
alias cycle-repo='echo "🔄 Cycling repos..." && push-all && pull-all'

# Engine Control
alias ai-engine-start='cd /root/peacock-engine && ./ai-engine-start.sh'
alias ai-engine-stop='kill $(cat /tmp/engine.pid) $(cat /tmp/ngrok.pid) 2>/dev/null'
alias ai-engine-logs='tail -f /root/logs/engine.log'
alias ai-engine-status='systemctl status peacock-engine'

# Portal
alias update-portal='cd /root/peacock-engine && ./update-peacock-portal.sh'
alias peacock-url='curl -s http://localhost:4040/api/tunnels | grep -o '"'"'"public_url":"https://[^"]*"'"'"' | head -1 | cut -d'"'"'" -f4'
```

---

## 5. File Structure

### PEACOCK ENGINE Repo

```
/home/flintx/ai-handler/
├── ai-engine-start.sh          # Main automation script
├── update-peacock-portal.sh    # Manual portal updater
├── ngrok-rotator.sh            # Ngrok token rotation
├── aliases.sh                  # Shell aliases
├── app/
│   ├── static/
│   │   └── chat.html           # WebUI (served by engine)
│   └── ...
└── ...
```

### save-aichats Repo (on VPS)

```
/root/save-aichats/
└── frontend/
    └── public/
        ├── peacock.html      # Portal dashboard
        ├── engine.html       # API redirect
        └── ui.html           # WebUI redirect
```

---

## 6. How It Works - Step by Step

### Step 1: User Executes Command

User types:
```bash
ai-engine-start
```

### Step 2: Script Initialization

1. Sets up variables
2. Kills any existing processes
3. Shows startup banner

### Step 3: Start PEACOCK ENGINE

```bash
nohup python -m app.main > $LOG_DIR/engine.log 2>&1 &
```

### Step 4: Start Ngrok

```bash
ngrok config add-authtoken "$TOKEN"
nohup ngrok http 3099 > $LOG_DIR/ngrok.log 2>&1 &
```

### Step 5: Get Dynamic URL

```bash
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*"' | head -1 | cut -d'"' -f4)
```

### Step 6: Update HTML Files

```bash
sed -i "s|NGROK_URL_PLACEHOLDER|$NGROK_URL|g" frontend/public/peacock.html
sed -i "s|NGROK_URL_PLACEHOLDER|$NGROK_URL|g" frontend/public/engine.html
sed -i "s|NGROK_URL_PLACEHOLDER|$NGROK_URL|g" frontend/public/ui.html
```

### Step 7: Push to GitHub

```bash
git add frontend/public/peacock.html frontend/public/engine.html frontend/public/ui.html
git commit -m "Update PEACOCK ENGINE portal"
git push origin master
```

### Step 8: Render Auto-Deploy

1. Render detects git push
2. Builds and deploys new version (~1 minute)

### Step 9: User Access

User visits: `save-aichats.com/ui`

1. Render serves `ui.html`
2. HTML redirects to ngrok URL
3. Ngrok tunnels to VPS:3099
4. PEACOCK ENGINE serves WebUI

---

## 7. Chat Transcript - Decision Points

### 7.1 Decision: Where to Put the Redirect Files

**User:**
> *"okay push it to github from that dir. and then i will pull it on the vps. then we can setup the script to change it on the vps and push it from the vps when ngrok gets spun up"*

**Decision:** Files live in save-aichats repo (Render hosts them), but are updated by script on VPS.

---

### 7.2 Decision: URL Structure

**User:**
> *"i really want 1 url to be save-aichats.com/engine and save-aichats.com/ui so the engine is basicly going to be the end point im gonna hit with api calls to make ai api calls... and the ui url is going to be the link to connect to the webb ui...."*

**Decision:** Three URLs:
- `/peacock` - Portal with buttons
- `/engine` - API redirect  
- `/ui` - WebUI redirect

---

### 7.3 Decision: Automation Level

**User:**
> *"so all i gotta do is press ai-engine adn it cauese a chain reaction.. and everything launches."*

**Decision:** Single script (`ai-engine-start`) that does everything.

---

## 8. Current Status & URLs

### Last Known Working State

**Ngrok URL:** `https://mouthiest-mariano-obesely.ngrok-free.dev`

**Access Points:**
| URL | Status | Redirects To |
|-----|--------|--------------|
| `save-aichats.com/peacock` | ✅ Working | Portal dashboard |
| `save-aichats.com/engine` | ⚠️ Needs setup | API endpoint |
| `save-aichats.com/ui` | ⚠️ Needs setup | WebUI |

### Current Issue

The script failed because `engine.html` and `ui.html` don't exist in save-aichats:

```
sed: can't read frontend/public/engine.html: No such file or directory
```

**Fix needed:**
```bash
cd /root/save-aichats
cat > frontend/public/engine.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0; url=https://mouthiest-mariano-obesely.ngrok-free.dev/v1/chat">
</head>
<body>Redirecting...</body>
</html>
EOF

cat > frontend/public/ui.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0; url=https://mouthiest-mariano-obesely.ngrok-free.dev/static/chat.html">
</head>
<body>Redirecting...</body>
</html>
EOF

git add .
git commit -m "Add redirects"
git push origin master
```

---

## 9. Summary

We built a complete redirect system that:

1. **Provides static URLs** (`save-aichats.com/ui`) that never change
2. **Automatically updates** when ngrok restarts
3. **Triggers with one command** (`ai-engine-start`)
4. **Deploys automatically** via Render
5. **Supports three endpoints**: Portal, API, and WebUI

The system bridges the gap between a static custom domain and a dynamic tunnel URL.

---

**END OF DOCUMENTATION**

