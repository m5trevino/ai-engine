# 🦚 PEACOCK ENGINE V3 - QUICK REFERENCE CARD

> **Laminate this and keep it next to your terminal**

---

## 🚨 Emergency Commands

```bash
# FULL SYSTEM RESTART
sudo systemctl restart peacock-engine && sudo systemctl restart caddy && echo "✅ SYSTEM RESTARTED"

# CHECK ALL SERVICES
sudo systemctl status peacock-engine caddy --no-pager

# VIEW LIVE LOGS
sudo journalctl -u peacock-engine -f -n 50

# DISK SPACE EMERGENCY
df -h && sudo apt autoremove && sudo apt autoclean

# KILL STUCK PROCESS
sudo pkill -f uvicorn && sleep 2 && sudo systemctl start peacock-engine
```

---

## 🔗 Essential URLs

| Service | Production | Local Dev |
|---------|------------|-----------|
| **Chat UI** | https://chat.save-aichats.com | http://localhost:3000 |
| **API Engine** | https://engine.save-aichats.com | http://localhost:3099 |
| **Health Check** | `/health` | `/health` |
| **Models List** | `/v1/models` | `/v1/models` |
| **WebSocket** | `wss://chat.save-aichats.com/v1/chat/ws/ws` | `ws://localhost:3099/v1/chat/ws/ws` |
| **Syncthing VPS** | http://204.168.184.49:8384 | http://localhost:8384 |

---

## 📂 Critical File Paths

```
# PROJECT ROOT
/root/ai-engine/                          # VPS
~/Projects/ai-engine/                     # Local

# CONFIGURATION
/root/ai-engine/.env                      # API KEYS (NEVER COMMIT)
/root/ai-engine/app/config.py             # Model registry
/root/ai-engine/app/main.py               # FastAPI entry

# FRONTEND
/root/ai-engine/ui/src/                   # React source
/root/ai-engine/ui/vite.config.ts         # Build config
/root/ai-engine/app/static/               # Built output

# BACKEND
/root/ai-engine/app/routes/               # API endpoints
/root/ai-engine/app/core/                 # Striker & KeyManager
/root/ai-engine/app/utils/                # Token counters

# DATA
/root/ai-engine/peacock.db                # SQLite database
/root/ai-engine/vault/                    # Strike logs
/root/herbert/liquid-semiotic/            # Syncthing payloads

# INFRASTRUCTURE
/etc/systemd/system/peacock-engine.service # Systemd config
/etc/caddy/Caddyfile                      # Reverse proxy
/var/log/caddy/                           # Caddy logs
```

---

## 🔄 Daily Operations

### Morning Health Check (Run on VPS)

```bash
#!/bin/bash
echo "=== PEACOCK HEALTH CHECK ==="
echo "1. Service Status:"
sudo systemctl is-active peacock-engine caddy
echo ""
echo "2. Memory Usage:"
free -h | grep Mem
echo ""
echo "3. Disk Space:"
df -h / | tail -1
echo ""
echo "4. API Response:"
curl -s https://chat.save-aichats.com/health | jq -r '.status'
echo ""
echo "5. Key Pool Status:"
curl -s https://chat.save-aichats.com/health | jq '.integrity'
echo ""
echo "6. Recent Errors:"
sudo journalctl -u peacock-engine --since "24 hours ago" -p err --no-pager | wc -l
echo "   errors in last 24h"
```

### Quick Code Update

```bash
# ONE-LINER UPDATE
cd ~/ai-engine && git pull origin main && sudo systemctl restart peacock-engine && echo "✅ UPDATED"

# WITH UI REBUILD
cd ~/ai-engine && git pull origin main && cd ui && npm run build && cd .. && sudo systemctl restart peacock-engine && echo "✅ UPDATED WITH UI"
```

---

## 🛠️ Common Tasks

### Add New API Key

```bash
# 1. Edit .env
nano /root/ai-engine/.env

# 2. Add to appropriate variable
# GROQ_KEYS="EXISTING:keys,NEWLABEL:newkey"
# GOOGLE_KEYS="EXISTING:keys,NEWLABEL:newkey"

# 3. Restart service
sudo systemctl restart peacock-engine

# 4. Verify
sudo journalctl -u peacock-engine -n 20 | grep -i "keys loaded"
```

### Check Token Count

```bash
# Via Python
cd /root/ai-engine
source .venv/bin/activate
python3 -c "
from app.utils.token_counter import PeacockTokenCounter
count = PeacockTokenCounter.count_prompt_tokens('gemini-2.5-pro', 'Hello world', [])
print(f'Tokens: {count}')
"
```

### View Strike Logs

```bash
# Today's strikes
ls -lt /root/ai-engine/vault/successful/ | head -10

# Failed strikes
ls -lt /root/ai-engine/vault/failed/ | head -10

# Specific strike
cat /root/ai-engine/vault/successful/PEA-XXXX.txt
```

---

## 🔍 Troubleshooting Matrix

| Symptom | Diagnose | Fix |
|---------|----------|-----|
| **502 Bad Gateway** | `curl localhost:3099/health` | `sudo systemctl restart peacock-engine` |
| **404 on API** | Check route order in main.py | API routes must be before StaticFiles |
| **CORS errors** | Browser console | Caddy headers or CORSMiddleware |
| **WebSocket fails** | Check `wss://` vs `ws://` | Use `wss://` for HTTPS sites |
| **Models not loading** | `curl /v1/models` | Check MODEL_REGISTRY in config.py |
| **Build fails** | `npm run build` output | `cd ui && rm -rf node_modules && npm install` |
| **Key exhausted** | Check logs for 429 errors | Add more keys to .env |
| **Out of disk** | `df -h` | Clean logs: `sudo rm /var/log/caddy/*.log.*` |
| **High memory** | `top` or `htop` | Restart service: `sudo systemctl restart peacock-engine` |
| **Syncthing conflict** | Web UI shows conflicts | Resolve in Syncthing UI or pick winner |

---

## 📊 Monitoring Dashboard (One-Liners)

```bash
# LIVE REQUESTS
sudo tail -f /var/log/caddy/chat-access.log | grep -v "health"

# ERROR RATE
sudo journalctl -u peacock-engine --since "1 hour ago" | grep -c "ERROR"

# TOKEN USAGE (last hour)
sqlite3 /root/ai-engine/peacock.db "SELECT SUM(tokens_used) FROM messages WHERE created_at > datetime('now', '-1 hour');"

# ACTIVE KEYS
curl -s https://chat.save-aichats.com/health | jq '.integrity'

# UPTIME
sudo systemctl show peacock-engine --property=ActiveEnterTimestamp
```

---

## 🔐 Security Checklist

```bash
# VERIFY FILE PERMISSIONS
ls -la /root/ai-engine/.env          # Should be: -rw------- (600)
ls -la /root/ai-engine/peacock.db    # Should be: -rw-r--r-- (644)

# CHECK FOR EXPOSED KEYS
grep -r "gsk_" /root/ai-engine/ --include="*.py" --include="*.ts" --include="*.js" | grep -v ".env"
grep -r "AIza" /root/ai-engine/ --include="*.py" --include="*.ts" --include="*.js" | grep -v ".env"
# Should return NOTHING

# VERIFY HTTPS
openssl s_client -connect chat.save-aichats.com:443 -servername chat.save-aichats.com </dev/null 2>/dev/null | openssl x509 -noout -dates

# CHECK OPEN PORTS
sudo ss -tlnp | grep -E "(3099|443|8384)"
```

---

## 🚀 Performance Tuning

```bash
# INCREASE WORKERS (edit service file)
sudo systemctl edit --full peacock-engine
# Change: --workers 2 → --workers 4

# ENABLE UVLOOP (faster event loop)
pip install uvloop
# Add to service: --loop uvloop

# HTTP/2 PUSH (Caddy)
# Already enabled by default in Caddy

# DATABASE OPTIMIZATION
sqlite3 /root/ai-engine/peacock.db "VACUUM;"
sqlite3 /root/ai-engine/peacock.db "PRAGMA optimize;"
```

---

## 📝 API Quick Examples

### Curl Examples

```bash
# Health Check
curl https://chat.save-aichats.com/health

# List Models
curl https://engine.save-aichats.com/v1/models | jq

# Simple Chat
curl -X POST https://engine.save-aichats.com/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"model": "gemini-2.5-flash", "prompt": "Hello"}'

# Chat with File Context
curl -X POST https://engine.save-aichats.com/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.3-70b-versatile",
    "prompt": "Explain this code",
    "files": ["/root/herbert/liquid-semiotic/english/example.py"]
  }'

# Streaming (SSE)
curl -N https://engine.save-aichats.com/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"model": "gemini-2.5-pro", "prompt": "Write a poem"}'

# Browse Filesystem
curl "https://engine.save-aichats.com/v1/fs/browse?path=/root/herbert"
```

### WebSocket Client (Browser Console)

```javascript
// Connect
const ws = new WebSocket('wss://chat.save-aichats.com/v1/chat/ws/ws');

// Send config
ws.send(JSON.stringify({
  type: "config",
  model: "gemini-2.5-pro",
  temp: 0.7
}));

// Send prompt
ws.send(JSON.stringify({
  type: "prompt",
  content: "Hello AI"
}));

// Receive
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

---

## 🆘 Recovery Procedures

### Scenario 1: Complete System Failure

```bash
# 1. SSH to VPS
ssh -i ~/.ssh/hetzner root@204.168.184.49

# 2. Check what's running
sudo systemctl list-units --failed

# 3. Restart everything
sudo systemctl restart peacock-engine caddy

# 4. Check logs
sudo journalctl -u peacock-engine -n 50

# 5. Verify
./launch.sh  # Or use systemd
```

### Scenario 2: Database Corruption

```bash
# 1. Stop service
sudo systemctl stop peacock-engine

# 2. Backup corrupted db
cp /root/ai-engine/peacock.db /root/ai-engine/peacock.db.corrupt.$(date +%s)

# 3. Try repair
sqlite3 /root/ai-engine/peacock.db ".recover" | sqlite3 /root/ai-engine/peacock.db.recovered

# 4. If recovery works
mv /root/ai-engine/peacock.db.recovered /root/ai-engine/peacock.db

# 5. Restart
sudo systemctl start peacock-engine

# 6. If all fails, start fresh
rm /root/ai-engine/peacock.db
sudo systemctl start peacock-engine  # Will recreate
```

### Scenario 3: Syncthing Conflict

```bash
# On VPS
# 1. Check status
curl -s http://localhost:8384/rest/db/status?folder=liquid-english | jq

# 2. If stuck, restart syncthing
sudo systemctl restart syncthing@root

# 3. Force rescan
# Via web UI: http://204.168.184.49:8384 → Folder → Rescan
```

---

## 📞 Support Resources

| Resource | Command/URL |
|----------|-------------|
| **System Status** | `curl https://chat.save-aichats.com/health` |
| **Live Logs** | `sudo journalctl -u peacock-engine -f` |
| **Caddy Logs** | `sudo tail -f /var/log/caddy/chat-access.log` |
| **Database Query** | `sqlite3 /root/ai-engine/peacock.db ".tables"` |
| **Git Status** | `cd ~/ai-engine && git status` |
| **Vite Build** | `cd ~/ai-engine/ui && npm run build` |
| **Python Test** | `cd ~/ai-engine && python3 -c "from app.main import app; print('OK')"` |

---

*Keep this reference handy. Speed is safety.*
