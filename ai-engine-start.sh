# 🦚 AI-ENGINE START - Full Stack Launcher
# Starts engine → ngrok → updates save-aichats with both API and UI URLs

# --- CONFIGURATION (Local vs VPS) ---
if [ -d "/home/flintx/hetzer-clone/peacock-engine" ]; then
    PEACOCK_DIR="/home/flintx/hetzer-clone/peacock-engine"
    SAVE_DIR="/home/flintx/hetzer-clone/save-aichats"
    LOG_DIR="/home/flintx/logs"
else
    PEACOCK_DIR="/root/peacock-engine"
    SAVE_DIR="/root/save-aichats"
    LOG_DIR="/root/logs"
fi
# ------------------------------------

set -e
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
echo "║      🦚 PEACOCK ENGINE - MASTERPIECE V4 STARTUP        ║"
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

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

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

if [ ! -d "$SAVE_DIR" ]; then
    echo -e "${RED}✗ Error: $SAVE_DIR not found!${NC}"
    exit 1
fi

cd $SAVE_DIR

# Get engine health data
HEALTH=$(curl -s http://localhost:3099/health 2>/dev/null || echo '{}')
GROQ=$(echo $HEALTH | grep -o '"groq":[0-9]*' | grep -o '[0-9]*' || echo "16")
GOOGLE=$(echo $HEALTH | grep -o '"google":[0-9]*' | grep -o '[0-9]*' || echo "3")

# Ensure directories exist
mkdir -p frontend/public

# Create Engine Redirect (Meta Refresh)
cat > frontend/public/engine.html << 'HTMLEOF'
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0; url=NGROK_URL_PLACEHOLDER/v1/chat">
    <title>Redirecting to Peacock API...</title>
</head>
<body>
    <p>Redirecting to <a href="NGROK_URL_PLACEHOLDER/v1/chat">Peacock API</a>...</p>
</body>
</html>
HTMLEOF

# Create UI Redirect (Meta Refresh)
cat > frontend/public/ui.html << 'HTMLEOF'
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0; url=NGROK_URL_PLACEHOLDER/">
    <title>Redirecting to Peacock UI...</title>
</head>
<body>
    <p>Redirecting to <a href="NGROK_URL_PLACEHOLDER/">Peacock UI</a>...</p>
</body>
</html>
HTMLEOF

# Create dual-URL portal
cat > frontend/public/peacock.html << 'HTMLEOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>🦚 PEACOCK ENGINE | Operational Portal</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Space+Grotesk:wght@300;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #030305;
            --surface: #0a0a0f;
            --accent: #aac7ff;
            --accent-glow: rgba(170, 199, 255, 0.4);
            --success: #4ade80;
            --text-main: #e0e0e0;
            --text-dim: #888;
            --border: rgba(255, 255, 255, 0.1);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg);
            background-image: 
                radial-gradient(circle at 20% 30%, rgba(170, 199, 255, 0.05) 0%, transparent 50%),
                radial-gradient(circle at 80% 70%, rgba(74, 222, 128, 0.03) 0%, transparent 50%);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 4rem 2rem;
        }
        .container { width: 100%; max-width: 1000px; }
        .header {
            text-align: center;
            margin-bottom: 4rem;
        }
        .logo-wrap {
            position: relative;
            display: inline-block;
            margin-bottom: 1.5rem;
        }
        .logo {
            font-size: 5rem;
            filter: drop-shadow(0 0 20px var(--accent-glow));
            animation: float 4s ease-in-out infinite;
        }
        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }
        h1 {
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 800;
            font-size: 3.5rem;
            letter-spacing: -1px;
            background: linear-gradient(135deg, var(--text-main) 30%, var(--accent) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
        }
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.75rem;
            background: rgba(255,255,255,0.03);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border);
            padding: 0.6rem 1.25rem;
            border-radius: 100px;
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--accent);
        }
        .status-dot {
            width: 8px;
            height: 8px;
            background: var(--success);
            border-radius: 50%;
            box-shadow: 0 0 10px var(--success);
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.5); opacity: 0.5; }
            100% { transform: scale(1); opacity: 1; }
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 2rem;
            margin-bottom: 4rem;
        }
        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 2.5rem;
            text-decoration: none;
            color: inherit;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            position: relative;
            overflow: hidden;
        }
        .card:hover {
            transform: translateY(-8px);
            border-color: var(--accent);
            box-shadow: 0 20px 40px rgba(0,0,0,0.4), 0 0 0 1px var(--accent);
        }
        .card::after {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 2px;
            background: linear-gradient(90deg, transparent, var(--accent), transparent);
            opacity: 0;
            transition: 0.4s;
        }
        .card:hover::after { opacity: 1; }
        .card-icon {
            font-size: 3rem;
            margin-bottom: 1.5rem;
            display: block;
        }
        .card h2 {
            font-size: 1.75rem;
            margin-bottom: 0.75rem;
            color: var(--accent);
        }
        .card p {
            color: var(--text-dim);
            line-height: 1.6;
            font-size: 0.95rem;
        }
        .card-meta {
            margin-top: 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-family: 'Space Grotesk', monospace;
            font-size: 0.8rem;
            color: var(--success);
        }
        .card-meta span {
            background: rgba(0,0,0,0.5);
            padding: 0.4rem 0.8rem;
            border-radius: 8px;
        }
        .stats-bar {
            display: flex;
            justify-content: center;
            gap: 3rem;
            padding: 2rem;
            background: rgba(255,255,255,0.02);
            border-radius: 20px;
            border: 1px solid var(--border);
        }
        .stat-item { text-align: center; }
        .stat-val {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--success);
            display: block;
        }
        .stat-label {
            font-size: 0.75rem;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 0.25rem;
        }
        .footer {
            margin-top: auto;
            text-align: center;
            color: var(--text-dim);
            font-size: 0.85rem;
            padding: 4rem 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo-wrap"><span class="logo">🦚</span></div>
            <h1>PEACOCK ENGINE</h1>
            <div class="status-badge">
                <span class="status-dot"></span>
                <span>SYSTEM ONLINE | V4.2.0-STABLE</span>
            </div>
        </div>

        <div class="grid">
            <a href="NGROK_URL_PLACEHOLDER/" class="card">
                <span class="card-icon">💎</span>
                <h2>Masterpiece UI</h2>
                <p>The premium chat interface with real-time telemetry, model rotation, and advanced diagnostics.</p>
                <div class="card-meta">
                    <span>LIVE SPA</span>
                    <span>NGROK → ROOT</span>
                </div>
            </a>

            <a href="NGROK_URL_PLACEHOLDER/v1/chat" class="card">
                <span class="card-icon">⚡</span>
                <h2>Direct API</h2>
                <p>High-performance unified gateway for programmatic integration and agentic tool-calling.</p>
                <div class="card-meta">
                    <span>REST / JSON</span>
                    <span>/v1/chat</span>
                </div>
            </a>
        </div>

        <div class="stats-bar">
            <div class="stat-item">
                <span class="stat-val">16</span>
                <span class="stat-label">Groq Assets</span>
            </div>
            <div class="stat-item">
                <span class="stat-val">3</span>
                <span class="stat-label">Google Assets</span>
            </div>
            <div class="stat-item">
                <span class="stat-val">ACTIVE</span>
                <span class="stat-label">Telemetry</span>
            </div>
        </div>

        <div class="footer">
            <p>&copy; 2026 TREVINO SYNDICATE | POCKET-FIRST AI ARCHITECTURE</p>
        </div>
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
git commit -m "Update PEACOCK PORTAL v4.2.0 - $(date '+%Y-%m-%d %H:%M')" || true
git push origin master 2>&1 | head -5

# Step 4: Show summary
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           🦚 PEACOCK MASTERPIECE IS LIVE!               ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}🔗 Access Points:${NC}"
echo -e "  ${YELLOW}Portal:${NC}  https://save-aichats.com/peacock"
echo -e "  ${YELLOW}API:${NC}     https://save-aichats.com/engine  → $NGROK_URL/v1/chat"
echo -e "  ${YELLOW}WebUI:${NC}   https://save-aichats.com/ui      → $NGROK_URL/"
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
