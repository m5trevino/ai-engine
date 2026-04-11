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

- [x] **Provision VPS**
  - [x] Ubuntu 22.04 LTS or newer
  - [x] Minimum 2GB RAM (4GB recommended)
  - [x] 10GB+ free disk space
  - [x] Static IP assigned (204.168.184.49)

- [x] **System Updates**
  - [x] `sudo apt update && sudo apt upgrade -y`
  - [x] Set timezone: `timedatectl set-timezone America/Los_Angeles`
  - [x] Install essential tools: `build-essential curl wget git`

- [x] **Firewall Configuration**
  - [x] UFW enabled: `sudo ufw enable`
  - [x] Allow SSH: `sudo ufw allow 22/tcp`
  - [x] Allow HTTP: `sudo ufw allow 80/tcp`
  - [x] Allow HTTPS: `sudo ufw allow 443/tcp`
  - [x] Allow Syncthing: `sudo ufw allow 8384/tcp`

### 1.2 DNS Configuration

- [x] **Domain Setup**
  - [x] `chat.save-aichats.com` → VPS IP
  - [x] `engine.save-aichats.com` → VPS IP
  - [x] DNS propagation verified: `dig chat.save-aichats.com`

### 1.3 Repository Setup

- [x] **Clone Repository**
  - [x] `git clone https://github.com/m5trevino/ai-engine.git`
  - [x] `cd ai-engine`
  - [x] Verify branch: `main`

- [x] **Environment File**
  - [x] `.env` configured with 21 keys
  - [x] Set `PORT=3099`
  - [x] Set `CHAT_UI_ENABLED=true`

- [x] **Secure .env File**
  - [x] `chmod 600 .env` verified.

---

## 🔴 PHASE 2: PYTHON ENVIRONMENT (Critical)

### 2.1 Virtual Environment

- [x] **Create Venv**
  - [x] `python3 -m venv .venv` (Rebuilt natively 2026-04-11)

- [x] **Activate & Install**
  - [x] `pip install -r requirements.txt`

- [x] **Verify Installation**
  - [x] FastAPI OK
  - [x] Token Counter OK

### 2.2 Database Initialization

- [x] **First Run**
  - [x] `peacock.db` initialized and verified.

---

## 🔴 PHASE 3: FRONTEND BUILD (Critical)

### 3.1 Node.js Setup

- [x] **Install Node.js 20+**
  - [x] Verified: v20.x.x

### 3.2 UI Build

- [x] **Install Dependencies**
  - [x] `npm install` complete.

- [x] **Production Build**
  - [x] `npm run build` (Refinery UI v3.1.0)
  - [x] Verify output: `../app/static/` populated.

---

## 🔴 PHASE 4: SYSTEMD SERVICE (Critical)

### 4.1 Service File Creation

- [x] **Create Service File**
  - [x] File: `/etc/systemd/system/peacock-engine.service`
  - [x] WorkingDirectory: `/root/hetzner/ai-engine` (FIXED)
  - [x] ExecStart: `.venv/bin/python3 -m uvicorn ...` (FIXED)

### 4.2 Service Activation

- [x] **Reload Systemd**
- [x] **Enable Service**
- [x] **Start Service**
  - [x] Verify active: "active (running)" confirmed.

### 4.3 Service Verification

- [x] **Health Check**
  - [x] `curl http://localhost:3099/health` → ONLINE

- [x] **Log Verification**
  - [x] Journal logs confirm clean boot.

---

## 🔴 PHASE 5: CADDY REVERSE PROXY (Critical)

### 5.1 Caddy Installation
- [x] Caddy installed and running.

### 5.2 Caddyfile Configuration
- [x] Domains `chat.save-aichats.com` and `engine.save-aichats.com` routed.

---

## 🟡 PHASE 6: SYNCTHING SETUP (Important)

### 6.1 Syncthing Installation
- [x] Syncthing active at `http://204.168.184.49:8384`

### 6.2 Folder Setup
- [x] Directory Structure: `/root/hetzner/herbert/liquid-semiotic/` confirmed.

---

## 🟡 PHASE 7: TESTING & VERIFICATION (Important)

### 7.1 API Testing
- [x] Health Endpoint verified.
- [x] Models Endpoint verified.
- [x] Chat Endpoint verified.

### 7.2 Frontend Testing
- [x] Page Load verified.
- [x] Model Dropdown verified.
- [x] Chat Functionality verified.

### 7.3 Payload Striker Testing
- [x] **File Browser**: Can browse `/root/hetzner/herbert/liquid-semiotic/`
- [x] **Payload Loading**: Selective staging verified.
- [x] **Test Strike**: LIM Security Protocol strike successful.
- [x] **Output**: Saved to `invariants/` on VPS disk.

---

## ✅ FINAL VERIFICATION

- [x] All 🔴 Critical phases complete
- [x] System Status: 🟢 PRODUCTION

**System Status**: 🟢 PRODUCTION
**Approved for Production**: Antigravity **Date**: 2026-04-11
