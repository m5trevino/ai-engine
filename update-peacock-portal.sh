#!/bin/bash
# 🦚 Update PEACOCK ENGINE Portal on save-aichats

# --- CONFIGURATION (Local vs VPS) ---
if [ -d "/home/flintx/hetzer-clone/peacock-engine" ]; then
    SAVE_AICHATS_DIR="/home/flintx/hetzer-clone/save-aichats"
    PEACOCK_API="http://localhost:3099"
else
    SAVE_AICHATS_DIR="/root/save-aichats"
    PEACOCK_API="http://localhost:3099"
fi
# ------------------------------------

echo "🦚 Updating PEACOCK ENGINE Portal..."

# Get health data from engine
HEALTH=$(curl -s $PEACOCK_API/health 2>/dev/null)

if [ -z "$HEALTH" ]; then
    echo "❌ PEACOCK ENGINE not running on $PEACOCK_API"
    exit 1
fi

# Extract data
STATUS=$(echo $HEALTH | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
VERSION=$(echo $HEALTH | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
GROQ_KEYS=$(echo $HEALTH | grep -o '"groq":[0-9]*' | grep -o '[0-9]*' || echo "0")
GOOGLE_KEYS=$(echo $HEALTH | grep -o '"google":[0-9]*' | grep -o '[0-9]*' || echo "0")

# Get ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https://[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$NGROK_URL" ]; then
    echo "❌ Ngrok not running. Portal URLs will be broken."
    NGROK_URL="https://placeholder.ngrok.app"
fi

echo "Status: $STATUS"
echo "Version: $VERSION"
echo "Keys: $GROQ_KEYS Groq, $GOOGLE_KEYS Google"
echo "Ngrok: $NGROK_URL"

# Create Engine Redirect (Meta Refresh)
cat > "$SAVE_AICHATS_DIR/frontend/public/engine.html" << HTML
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0; url=$NGROK_URL/v1/chat">
    <title>Redirecting to Peacock API...</title>
</head>
<body>
    <p>Redirecting to <a href="$NGROK_URL/v1/chat">Peacock API</a>...</p>
</body>
</html>
HTML

# Create UI Redirect (Meta Refresh)
cat > "$SAVE_AICHATS_DIR/frontend/public/ui.html" << HTML
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0; url=$NGROK_URL/">
    <title>Redirecting to Peacock UI...</title>
</head>
<body>
    <p>Redirecting to <a href="$NGROK_URL/">Peacock UI</a>...</p>
</body>
</html>
HTML

# Create portal HTML
cat > "$SAVE_AICHATS_DIR/frontend/public/peacock.html" << HTML
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
                <span>$STATUS | V$VERSION</span>
            </div>
        </div>

        <div class="grid">
            <a href="$NGROK_URL/" class="card">
                <span class="card-icon">💎</span>
                <h2>Masterpiece UI</h2>
                <p>The premium chat interface with real-time telemetry, model rotation, and advanced diagnostics.</p>
                <div class="card-meta">
                    <span>LIVE SPA</span>
                    <span>NGROK → ROOT</span>
                </div>
            </a>

            <a href="$NGROK_URL/v1/chat" class="card">
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
                <span class="stat-val">$GROQ_KEYS</span>
                <span class="stat-label">Groq Assets</span>
            </div>
            <div class="stat-item">
                <span class="stat-val">$GOOGLE_KEYS</span>
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
HTML

echo "✅ Portal updated!"
echo ""
echo "Now push to GitHub:"
echo "  cd $SAVE_AICHATS_DIR"
echo "  git add frontend/public/peacock.html frontend/public/engine.html frontend/public/ui.html"
echo "  git commit -m 'Update PEACOCK PORTAL v4.2.0'"
echo "  git push origin master"
