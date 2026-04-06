#!/bin/bash
# 🦚 Update PEACOCK ENGINE Portal on save-aichats

SAVE_AICHATS_DIR="${SAVE_AICHATS_DIR:-/root/save-aichats}"
PEACOCK_API="${PEACOCK_API:-http://localhost:3099}"

echo "🦚 Updating PEACOCK ENGINE Portal..."

# Get health data from engine
HEALTH=$(curl -s $PEACOCK_API/health 2>/dev/null)

if [ -z "$HEALTH" ]; then
    echo "❌ PEACOCK ENGINE not running on $PEACOCK_API"
    echo "Start it first: sudo systemctl start peacock-engine"
    exit 1
fi

# Extract data
STATUS=$(echo $HEALTH | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
VERSION=$(echo $HEALTH | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
GROQ_KEYS=$(echo $HEALTH | grep -o '"groq":[0-9]*' | grep -o '[0-9]*')
GOOGLE_KEYS=$(echo $HEALTH | grep -o '"google":[0-9]*' | grep -o '[0-9]*')
DEEPSEEK_KEYS=$(echo $HEALTH | grep -o '"deepseek":[0-9]*' | grep -o '[0-9]*')
MISTRAL_KEYS=$(echo $HEALTH | grep -o '"mistral":[0-9]*' | grep -o '[0-9]*')

# Get models count
MODELS=$(curl -s $PEACOCK_API/v1/models 2>/dev/null | grep -c '"id"' || echo "40+")

# Get ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https://[^"]*"' | head -1 | cut -d'"' -f4)

echo "Status: $STATUS"
echo "Version: $VERSION"
echo "Keys: $GROQ_KEYS Groq, $GOOGLE_KEYS Google, $DEEPSEEK_KEYS DeepSeek, $MISTRAL_KEYS Mistral"
echo "Ngrok: $NGROK_URL"

# Create portal HTML
cat > "$SAVE_AICHATS_DIR/frontend/public/peacock.html" << HTML
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
            padding: 3rem 0;
            border-bottom: 1px solid #333;
            margin-bottom: 2rem;
        }
        .logo {
            font-size: 4rem;
            margin-bottom: 1rem;
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
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            max-width: 1200px;
            margin: 0 auto;
        }
        .card {
            background: rgba(255,255,255,0.05);
            border: 1px solid #333;
            border-radius: 12px;
            padding: 1.5rem;
            transition: transform 0.2s, border-color 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
            border-color: #aac7ff;
        }
        .card h3 {
            color: #aac7ff;
            margin-bottom: 1rem;
            font-size: 1.1rem;
        }
        .stat {
            display: flex;
            justify-content: space-between;
            padding: 0.5rem 0;
            border-bottom: 1px solid #333;
        }
        .stat:last-child {
            border-bottom: none;
        }
        .stat-value {
            color: #4ade80;
            font-weight: bold;
        }
        .endpoint {
            background: #1a1a2e;
            padding: 1rem;
            border-radius: 8px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            margin-top: 1rem;
            word-break: break-all;
        }
        .endpoint a {
            color: #4ade80;
            text-decoration: none;
        }
        .endpoint a:hover {
            text-decoration: underline;
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
            <span>$STATUS | V$VERSION</span>
        </div>
    </div>
    
    <div class="grid">
        <div class="card">
            <h3>🔑 API Keys Loaded</h3>
            <div class="stat">
                <span>Groq</span>
                <span class="stat-value">$GROQ_KEYS keys</span>
            </div>
            <div class="stat">
                <span>Google</span>
                <span class="stat-value">$GOOGLE_KEYS keys</span>
            </div>
            <div class="stat">
                <span>DeepSeek</span>
                <span class="stat-value">$DEEPSEEK_KEYS keys</span>
            </div>
            <div class="stat">
                <span>Mistral</span>
                <span class="stat-value">$MISTRAL_KEYS keys</span>
            </div>
        </div>
        
        <div class="card">
            <h3>🤖 Models Available</h3>
            <div class="stat">
                <span>Total Models</span>
                <span class="stat-value">$MODELS+</span>
            </div>
            <div class="stat">
                <span>Gemini Pro</span>
                <span class="stat-value">✓</span>
            </div>
            <div class="stat">
                <span>Llama 4</span>
                <span class="stat-value">✓</span>
            </div>
            <div class="stat">
                <span>Kimi K2</span>
                <span class="stat-value">✓</span>
            </div>
        </div>
        
        <div class="card">
            <h3>🔗 Access Points</h3>
            <div class="endpoint">
                <strong>Direct:</strong><br>
                <a href="$NGROK_URL">$NGROK_URL</a>
            </div>
            <div class="endpoint">
                <strong>Health:</strong><br>
                <a href="$NGROK_URL/health">/health</a>
            </div>
            <div class="endpoint">
                <strong>Chat API:</strong><br>
                <a href="$NGROK_URL/v1/chat">/v1/chat</a>
            </div>
        </div>
        
        <div class="card">
            <h3>⚡ Quick Actions</h3>
            <div class="endpoint">
                <strong>Test Strike:</strong><br>
                curl -X POST $NGROK_URL/v1/chat \\
                -d '{"model":"gemini-2.0-flash-lite","prompt":"Hello"}'
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p>🦚 PEACOCK ENGINE V$VERSION | Multi-Gateway AI Orchestration</p>
        <p style="margin-top: 0.5rem; font-size: 0.85rem;">Redirecting to active tunnel in 5 seconds...</p>
    </div>
    
    <script>
        setTimeout(() => {
            window.location.href = "$NGROK_URL";
        }, 5000);
    </script>
</body>
</html>
HTML

echo "✅ Portal updated!"
echo ""
echo "Now push to GitHub:"
echo "  cd $SAVE_AICHATS_DIR"
echo "  git add frontend/public/peacock.html"
echo "  git commit -m 'Update PEACOCK ENGINE portal'"
echo "  git push origin master"
