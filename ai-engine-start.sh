#!/bin/bash
# 🦚 AI-ENGINE START - Full Stack Launcher
# Starts engine → ngrok → updates save-aichats with both API and UI URLs

set -e

PEACOCK_DIR="/root/peacock-engine"
SAVE_DIR="/root/save-aichats"
LOG_DIR="/root/logs"
mkdir -p $LOG_DIR

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║         🦚 PEACOCK ENGINE - FULL STACK STARTUP          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Kill any existing processes
echo -e "${YELLOW}🧹 Cleaning up existing processes...${NC}"
pkill -f "python -m app.main" 2>/dev/null || true
pkill -x ngrok 2>/dev/null || true
sleep 2

# Step 1: Start PEACOCK ENGINE
echo ""
echo -e "${CYAN}[1/4] Starting PEACOCK ENGINE...${NC}"
cd $PEACOCK_DIR
source .venv/bin/activate

# Start engine in background, log to file
nohup python -m app.main > $LOG_DIR/engine.log 2>&1 &
ENGINE_PID=$!
echo $ENGINE_PID > /tmp/engine.pid

echo -n "Waiting for engine..."
for i in {1..30}; do
    if curl -s http://localhost:3099/health > /dev/null 2>&1; then
        echo -e "\n${GREEN}✓ Engine ONLINE (PID: $ENGINE_PID)${NC}"
        break
    fi
    sleep 1
    echo -n "."
done

if ! curl -s http://localhost:3099/health > /dev/null 2>&1; then
    echo -e "\n${RED}✗ Engine failed to start!${NC}"
    echo "Check logs: tail -f $LOG_DIR/engine.log"
    exit 1
fi

# Step 2: Start Ngrok
echo ""
echo -e "${CYAN}[2/4] Starting NGROK tunnel...${NC}"
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
echo $NGROK_PID > /tmp/ngrok.pid

echo -n "Waiting for tunnel..."
for i in {1..30}; do
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https://[^"]*"' | head -1 | cut -d'"' -f4)
    if [ -n "$NGROK_URL" ]; then
        echo -e "\n${GREEN}✓ Ngrok ONLINE${NC}"
        echo -e "${GREEN}  → $NGROK_URL${NC}"
        break
    fi
    sleep 1
    echo -n "."
done

if [ -z "$NGROK_URL" ]; then
    echo -e "\n${RED}✗ Ngrok failed!${NC}"
    exit 1
fi

# Step 3: Update save-aichats portal with dual URLs
echo ""
echo -e "${CYAN}[3/4] Updating save-aichats portal...${NC}"

cd $SAVE_DIR

# Get engine health data
HEALTH=$(curl -s http://localhost:3099/health 2>/dev/null || echo '{}')
GROQ=$(echo $HEALTH | grep -o '"groq":[0-9]*' | grep -o '[0-9]*' || echo "16")
GOOGLE=$(echo $HEALTH | grep -o '"google":[0-9]*' | grep -o '[0-9]*' || echo "3")

# Create dual-URL portal
cat > frontend/public/peacock.html << 'HTMLEOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>🦚 PEACOCK ENGINE | AI Gateway</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Space Grotesk', 'Inter', system-ui, sans-serif;
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 2rem;
        }
        .header {
            text-align: center;
            padding: 2rem 0;
            border-bottom: 1px solid #333;
            margin-bottom: 2rem;
        }
        .logo {
            font-size: 4rem;
            margin-bottom: 0.5rem;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        h1 {
            font-size: 2.5rem;
            background: linear-gradient(90deg, #aac7ff, #4ade80);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        .status {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: #0f3460;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.9rem;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            background: #4ade80;
            border-radius: 50%;
            animation: blink 1s infinite;
        }
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        .big-links {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            max-width: 900px;
            margin: 2rem auto;
        }
        .big-link {
            background: linear-gradient(135deg, #1a1a3e 0%, #0f0f2f 100%);
            border: 2px solid #333;
            border-radius: 16px;
            padding: 2rem;
            text-align: center;
            text-decoration: none;
            color: #e0e0e0;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        .big-link:hover {
            border-color: #aac7ff;
            transform: translateY(-4px);
            box-shadow: 0 10px 40px rgba(170, 199, 255, 0.2);
        }
        .big-link .icon {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        .big-link h2 {
            color: #aac7ff;
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
        }
        .big-link .desc {
            color: #888;
            font-size: 0.9rem;
        }
        .big-link .url {
            margin-top: 1rem;
            padding: 0.5rem;
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            font-family: monospace;
            font-size: 0.75rem;
            color: #4ade80;
            word-break: break-all;
        }
        .stats {
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-top: 2rem;
            padding: 1rem;
            background: rgba(255,255,255,0.03);
            border-radius: 12px;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
        }
        .stat {
            text-align: center;
        }
        .stat-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #4ade80;
        }
        .stat-label {
            font-size: 0.8rem;
            color: #666;
            text-transform: uppercase;
        }
        .footer {
            text-align: center;
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid #333;
            color: #666;
        }
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
    
    <div class="footer">
        <p>🦚 PEACOCK ENGINE V3 | Multi-Gateway AI Orchestration</p>
    </div>
</body>
</html>
HTMLEOF

# Replace placeholders with actual URL in all redirect files
sed -i "s|NGROK_URL_PLACEHOLDER|$NGROK_URL|g" frontend/public/peacock.html
sed -i "s|NGROK_URL_PLACEHOLDER|$NGROK_URL|g" frontend/public/engine.html
sed -i "s|NGROK_URL_PLACEHOLDER|$NGROK_URL|g" frontend/public/ui.html

# Commit and push all redirect files
git add frontend/public/peacock.html frontend/public/engine.html frontend/public/ui.html
git commit -m "Update PEACOCK ENGINE portal - $(date '+%Y-%m-%d %H:%M')" || true
git push origin master 2>&1 | head -5

# Step 4: Show summary
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              🦚 PEACOCK ENGINE IS LIVE!                 ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}🔗 Access Points:${NC}"
echo -e "  ${YELLOW}Portal:${NC}  https://save-aichats.com/peacock"
echo -e "  ${YELLOW}API:${NC}     https://save-aichats.com/engine  → $NGROK_URL/v1/chat"
echo -e "  ${YELLOW}WebUI:${NC}   https://save-aichats.com/ui     → $NGROK_URL/static/chat.html"
echo ""
echo -e "${CYAN}📊 Stats:${NC}"
echo -e "  • Engine PID: $ENGINE_PID"
echo -e "  • Ngrok PID: $NGROK_PID"
echo -e "  • Keys: $GROQ Groq, $GOOGLE Google"
echo ""
echo -e "${CYAN}📜 Logs:${NC}"
echo -e "  Engine: tail -f $LOG_DIR/engine.log"
echo -e "  Ngrok:  tail -f $LOG_DIR/ngrok.log"
echo ""
echo -e "${YELLOW}⛔ To stop:${NC} kill $ENGINE_PID $NGROK_PID"

# Keep showing engine logs
echo ""
echo -e "${CYAN}📡 Engine Logs (Ctrl+C to detach):${NC}"
tail -f $LOG_DIR/engine.log
