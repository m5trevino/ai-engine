# ✅ PEACOCK ENGINE V3 - IMPLEMENTATION CHECKLIST

> **Master task tracker for system deployment and maintenance**

---

## 📋 HOW TO USE THIS CHECKLIST

- [ ] Unchecked = Not started
- [/] Partial = In progress
- [x] Checked = Complete
- [!] Exclamation = Blocked/Issue

**Color Coding**:
- 🔴 **Critical** - Must complete for basic functionality
- 🟡 **Important** - Needed for production use
- 🟢 **Optional** - Enhancement features

---

## 🔴 PHASE 1: FOUNDATION (Critical)

### 1.1 Server Preparation

- [ ] **Provision VPS**
  - [ ] Ubuntu 22.04 LTS or newer
  - [ ] Minimum 2GB RAM (4GB recommended)
  - [ ] 10GB+ free disk space
  - [ ] Static IP assigned (204.168.184.49)

- [ ] **System Updates**
  - [ ] `sudo apt update && sudo apt upgrade -y`
  - [ ] Set timezone: `timedatectl set-timezone America/Los_Angeles`
  - [ ] Install essential tools: `build-essential curl wget git`

- [ ] **Firewall Configuration**
  - [ ] UFW enabled: `sudo ufw enable`
  - [ ] Allow SSH: `sudo ufw allow 22/tcp`
  - [ ] Allow HTTP: `sudo ufw allow 80/tcp`
  - [ ] Allow HTTPS: `sudo ufw allow 443/tcp`
  - [ ] Allow Syncthing: `sudo ufw allow 8384/tcp` (if remote access needed)

### 1.2 DNS Configuration

- [ ] **Domain Setup**
  - [ ] `chat.save-aichats.com` → VPS IP
  - [ ] `engine.save-aichats.com` → VPS IP
  - [ ] `claw.save-aichats.com` → VPS IP (if needed)
  - [ ] `herbert.save-aichats.com` → VPS IP (if needed)
  - [ ] DNS propagation verified: `dig chat.save-aichats.com`

### 1.3 Repository Setup

- [ ] **Clone Repository**
  - [ ] `git clone https://github.com/m5trevino/ai-engine.git`
  - [ ] `cd ai-engine`
  - [ ] Verify branch: `git branch` (should be main)

- [ ] **Environment File**
  - [ ] `cp .env.example .env`
  - [ ] Add GROQ_KEYS (minimum 1, recommend 16)
  - [ ] Add GOOGLE_KEYS (minimum 1, recommend 3)
  - [ ] Add DEEPSEEK_KEYS (optional)
  - [ ] Add MISTRAL_KEYS (optional)
  - [ ] Set `PORT=3099`
  - [ ] Set `PROXY_ENABLED=false` (or configure proxy)
  - [ ] Set `CHAT_UI_ENABLED=true`

- [ ] **Secure .env File**
  - [ ] `chmod 600 .env`
  - [ ] Verify: `ls -la .env` (should show `-rw-------`)

---

## 🔴 PHASE 2: PYTHON ENVIRONMENT (Critical)

### 2.1 Virtual Environment

- [ ] **Create Venv**
  - [ ] `python3 -m venv .venv`
  - [ ] Verify creation: `ls -la .venv/bin/`

- [ ] **Activate & Install**
  - [ ] `source .venv/bin/activate`
  - [ ] `pip install --upgrade pip`
  - [ ] `pip install -r requirements.txt`

- [ ] **Verify Installation**
  - [ ] `python3 -c "from app.main import app; print('FastAPI OK')"`
  - [ ] `python3 -c "from app.utils.token_counter import PeacockTokenCounter; print('Token Counter OK')"`
  - [ ] `python3 -c "import tiktoken; print('tiktoken OK')"`

### 2.2 Database Initialization

- [ ] **First Run**
  - [ ] `python3 -c "from app.db.database import init_db; init_db()"`
  - [ ] Verify: `ls -la peacock.db`
  - [ ] Test query: `sqlite3 peacock.db ".tables"`

---

## 🔴 PHASE 3: FRONTEND BUILD (Critical)

### 3.1 Node.js Setup

- [ ] **Install Node.js 20+**
  - [ ] `curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -`
  - [ ] `sudo apt install -y nodejs`
  - [ ] Verify: `node --version` (should be v20.x.x)
  - [ ] Verify: `npm --version`

### 3.2 UI Build

- [ ] **Install Dependencies**
  - [ ] `cd ui`
  - [ ] `npm install`
  - [ ] Verify node_modules: `ls node_modules | head`

- [ ] **Production Build**
  - [ ] `npm run build`
  - [ ] Verify output: `ls -la ../app/static/`
  - [ ] Confirm files:
    - [ ] `../app/static/index.html`
    - [ ] `../app/static/assets/index-*.js`
    - [ ] `../app/static/assets/index-*.css`

- [ ] **Build Verification**
  - [ ] No build errors in output
  - [ ] File sizes reasonable (>100KB for JS)

---

## 🔴 PHASE 4: SYSTEMD SERVICE (Critical)

### 4.1 Service File Creation

- [ ] **Create Service File**
  - [ ] File: `/etc/systemd/system/peacock-engine.service`
  - [ ] User: root
  - [ ] WorkingDirectory: /root/ai-engine
  - [ ] ExecStart points to venv uvicorn
  - [ ] Restart=always configured
  - [ ] EnvironmentFile points to .env

- [ ] **Service File Content Check**
  ```bash
  # Verify these lines exist:
  grep -E "(WorkingDirectory|ExecStart|EnvironmentFile|Restart)" \
    /etc/systemd/system/peacock-engine.service
  ```

### 4.2 Service Activation

- [ ] **Reload Systemd**
  - [ ] `sudo systemctl daemon-reload`

- [ ] **Enable Service**
  - [ ] `sudo systemctl enable peacock-engine`
  - [ ] Verify: `systemctl is-enabled peacock-engine`

- [ ] **Start Service**
  - [ ] `sudo systemctl start peacock-engine`
  - [ ] Check status: `sudo systemctl status peacock-engine`
  - [ ] Verify active: output shows "active (running)"

### 4.3 Service Verification

- [ ] **Health Check**
  - [ ] `curl http://localhost:3099/health`
  - [ ] Should return JSON with status "ONLINE"

- [ ] **Log Verification**
  - [ ] `sudo journalctl -u peacock-engine -n 20`
  - [ ] Look for "PEACOCK ENGINE V3 BOOT SEQUENCE"
  - [ ] Verify key pools loaded: "Groq Pool: X keys"

- [ ] **Auto-Restart Test**
  - [ ] `sudo pkill -f uvicorn`
  - [ ] Wait 5 seconds
  - [ ] `sudo systemctl status peacock-engine` (should be running)

---

## 🔴 PHASE 5: CADDY REVERSE PROXY (Critical)

### 5.1 Caddy Installation

- [ ] **Install Caddy**
  - [ ] `sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https`
  - [ ] `curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg`
  - [ ] `curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list`
  - [ ] `sudo apt update && sudo apt install caddy`

- [ ] **Verify Installation**
  - [ ] `caddy version`
  - [ ] `sudo systemctl status caddy`

### 5.2 Caddyfile Configuration

- [ ] **Setup Log Directory**
  - [ ] `sudo bash /root/ai-engine/deploy/setup-caddy-infra.sh`
  - [ ] Verify: `ls -la /var/log/caddy/`

- [ ] **Deploy Caddyfile**
  - [ ] `sudo cp /root/ai-engine/deploy/Caddyfile /etc/caddy/Caddyfile`
  - [ ] Edit if needed for correct domains
  - [ ] Validate: `sudo caddy validate --config /etc/caddy/Caddyfile`

- [ ] **Reload Caddy**
  - [ ] `sudo caddy reload --config /etc/caddy/Caddyfile`
  - [ ] Or: `sudo systemctl reload caddy`

### 5.3 HTTPS Verification

- [ ] **Certificate Generation**
  - [ ] Check Caddy logs: `sudo journalctl -u caddy -n 50`
  - [ ] Look for "certificate obtained successfully"

- [ ] **HTTPS Test**
  - [ ] `curl -I https://chat.save-aichats.com/health`
  - [ ] Should return HTTP/2 200
  - [ ] Should show `strict-transport-security` header

---

## 🟡 PHASE 6: SYNCTHING SETUP (Important)

### 6.1 Syncthing Installation

- [ ] **Install**
  - [ ] `sudo apt install syncthing`
  - [ ] `sudo systemctl enable syncthing@root`
  - [ ] `sudo systemctl start syncthing@root`

- [ ] **Configure Web UI**
  - [ ] Edit: `~/.config/syncthing/config.xml`
  - [ ] Set GUI address to `0.0.0.0:8384` (for remote access)
  - [ ] Restart: `sudo systemctl restart syncthing@root`

### 6.2 Folder Setup

- [ ] **Create Directory Structure**
  - [ ] `mkdir -p /root/herbert/liquid-semiotic/{english,invariants,legos,semiotic-mold}`

- [ ] **Configure Sync Folders**
  - [ ] Access web UI: http://204.168.184.49:8384
  - [ ] Set device name: "VPS-Shell"
  - [ ] Check "Introducer" checkbox
  - [ ] Add folder: `liquid-english` → `/root/herbert/liquid-semiotic/english`
  - [ ] Add folder: `liquid-invariants` → `/root/herbert/liquid-semiotic/invariants`
  - [ ] Add folder: `liquid-legos` → `/root/herbert/liquid-semiotic/legos`
  - [ ] Add folder: `liquid-mold` → `/root/herbert/liquid-semiotic/semiotic-mold`

### 6.3 Local Machine Pairing

- [ ] **Local Syncthing Setup**
  - [ ] Install Syncthing on local machine
  - [ ] Access local UI: http://localhost:8384
  - [ ] Add device: VPS device ID
  - [ ] Accept pairing on VPS side

- [ ] **Verify Sync**
  - [ ] Create test file locally
  - [ ] Verify appears on VPS
  - [ ] Delete test file

---

## 🟡 PHASE 7: TESTING & VERIFICATION (Important)

### 7.1 API Testing

- [ ] **Health Endpoint**
  - [ ] `curl https://chat.save-aichats.com/health | jq`
  - [ ] Verify: status = "ONLINE"
  - [ ] Verify: all key pools show >0 keys

- [ ] **Models Endpoint**
  - [ ] `curl https://engine.save-aichats.com/v1/models | jq`
  - [ ] Verify: JSON structure with gateways
  - [ ] Verify: multiple models listed per gateway

- [ ] **Chat Endpoint**
  - [ ] Test basic chat:
    ```bash
    curl -X POST https://engine.save-aichats.com/v1/chat \
      -H "Content-Type: application/json" \
      -d '{"model": "gemini-2.5-flash", "prompt": "Hello"}'
    ```
  - [ ] Verify: Response contains content
  - [ ] Verify: Usage tokens reported

- [ ] **Streaming Endpoint**
  - [ ] Test SSE:
    ```bash
    curl -N https://engine.save-aichats.com/v1/chat/stream \
      -H "Content-Type: application/json" \
      -d '{"model": "gemini-2.5-flash", "prompt": "Hi"}'
    ```
  - [ ] Verify: Chunks stream in real-time

- [ ] **WebSocket Test**
  - [ ] Use browser console or wscat
  - [ ] Connect to `wss://chat.save-aichats.com/v1/chat/ws/ws`
  - [ ] Send config message
  - [ ] Send prompt message
  - [ ] Verify: Receive streaming content

### 7.2 Frontend Testing

- [ ] **Page Load**
  - [ ] Open https://chat.save-aichats.com
  - [ ] Verify: No 404 errors
  - [ ] Verify: CSS/JS loads (check DevTools Network)

- [ ] **Model Dropdown**
  - [ ] Verify: Models populate from API
  - [ ] Verify: Grouped by gateway
  - [ ] Verify: All expected models present

- [ ] **Key Usage Display**
  - [ ] Verify: API key usage stats load
  - [ ] Verify: Key names display correctly

- [ ] **Chat Functionality**
  - [ ] Type message
  - [ ] Send message
  - [ ] Verify: Response received
  - [ ] Verify: Real-time streaming (if enabled)

### 7.3 Payload Striker Testing

- [ ] **File Browser**
  - [ ] Navigate to Payload Striker tab
  - [ ] Verify: File system API accessible
  - [ ] Verify: Can browse `/root/herbert/liquid-semiotic/`

- [ ] **Payload Loading**
  - [ ] Select prompt
  - [ ] Load payload files
  - [ ] Verify: Files appear in loaded section

- [ ] **Test Strike**
  - [ ] Configure strike (1 file, fast model)
  - [ ] Execute strike
  - [ ] Verify: Response received
  - [ ] Verify: Output saved to invariants/

---

## 🟡 PHASE 8: MONITORING & LOGGING (Important)

### 8.1 Log Rotation

- [ ] **Caddy Logs**
  - [ ] Verify: `/var/log/caddy/` exists
  - [ ] Verify: Log files being written
  - [ ] Configure logrotate if needed

- [ ] **Journal Logs**
  - [ ] `sudo journalctl --disk-usage`
  - [ ] Verify: Not consuming excessive disk

### 8.2 Health Monitoring Script

- [ ] **Create Monitoring Script**
  - [ ] File: `/root/ai-engine/scripts/health_check.sh`
  - [ ] Test: `bash /root/ai-engine/scripts/health_check.sh`

- [ ] **Optional: Cron Job**
  - [ ] `crontab -e`
  - [ ] Add: `*/15 * * * * /root/ai-engine/scripts/health_check.sh`

---

## 🟢 PHASE 9: OPTIMIZATION (Optional)

### 9.1 Performance Tuning

- [ ] **Increase Uvicorn Workers**
  - [ ] Edit: `/etc/systemd/system/peacock-engine.service`
  - [ ] Change: `--workers 2` to `--workers 4`
  - [ ] Restart service

- [ ] **Enable uvloop**
  - [ ] `pip install uvloop`
  - [ ] Add `--loop uvloop` to service ExecStart

- [ ] **Database Optimization**
  - [ ] `sqlite3 peacock.db "VACUUM;"`
  - [ ] `sqlite3 peacock.db "PRAGMA optimize;"`

### 9.2 Security Hardening

- [ ] **Fail2ban**
  - [ ] `sudo apt install fail2ban`
  - [ ] Configure for SSH and Caddy

- [ ] **Automatic Updates**
  - [ ] `sudo apt install unattended-upgrades`
  - [ ] Configure security updates only

### 9.3 Backup Configuration

- [ ] **Database Backup**
  - [ ] Script: `/root/ai-engine/scripts/backup_db.sh`
  - [ ] Cron: Daily backup to `/backup/`

- [ ] **Configuration Backup**
  - [ ] Backup `.env` to secure location
  - [ ] Document all API keys offline

---

## ✅ FINAL VERIFICATION

### Pre-Launch Checklist

- [ ] All 🔴 Critical phases complete
- [ ] All API endpoints responding
- [ ] HTTPS certificates valid
- [ ] WebSocket connections working
- [ ] Syncthing folders syncing
- [ ] Systemd auto-restart tested
- [ ] Logs rotating properly

### Launch Sign-Off

| Component | Status | Verified By | Date |
|-----------|--------|-------------|------|
| FastAPI Backend | | | |
| React Frontend | | | |
| Caddy Proxy | | | |
| Systemd Service | | | |
| Syncthing Sync | | | |
| API Keys Valid | | | |
| SSL/TLS Working | | | |

**System Status**: 🔴 NOT READY / 🟡 TESTING / 🟢 PRODUCTION

**Approved for Production**: _______________ **Date**: _______________

---

## 🔄 POST-LAUNCH TASKS

### Daily

- [ ] Check service status
- [ ] Review error logs
- [ ] Verify Syncthing sync status

### Weekly

- [ ] Review token usage/costs
- [ ] Check disk space
- [ ] Update local repo with changes

### Monthly

- [ ] Rotate API keys (if needed)
- [ ] Review and archive old logs
- [ ] Performance benchmark
- [ ] Security audit

---

*"Check twice, deploy once."*
