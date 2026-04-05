# 🦚 PEACOCK ENGINE - Production Deployment

This directory contains everything needed to deploy PEACOCK ENGINE on a Hetzner VPS (or any Ubuntu server) for production use.

## Quick Start (One Command)

```bash
curl -sSL https://raw.githubusercontent.com/yourusername/ai-handler/main/deploy/quick-deploy.sh | sudo bash
```

Or manually:

```bash
# On your VPS as root
git clone https://github.com/yourusername/ai-handler.git /opt/peacock-engine
cd /opt/peacock-engine
bash deploy/setup-server.sh       # Run as root
su - peacock -s /bin/bash
cd /opt/peacock-engine
bash deploy/install-app.sh        # Run as peacock user
```

## What's Included

| File | Purpose |
|------|---------|
| `setup-server.sh` | Server preparation (root) - installs deps, Caddy, firewall |
| `install-app.sh` | App installation (peacock user) - venv, deps, service |
| `quick-deploy.sh` | One-command full deployment |
| `update.sh` | Quick update script for pulling changes |
| `backup.sh` | Backup database and vault files |
| `peacock-engine.service` | Systemd service definition |
| `Caddyfile` | Caddy reverse proxy config with auto-SSL |
| `Dockerfile` | Docker image definition |
| `docker-compose.yml` | Docker Compose stack |
| `.env.production.template` | Environment variable template |
| `DEPLOYMENT_GUIDE.md` | Full deployment documentation |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       INTERNET                              │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Caddy Reverse Proxy (Auto SSL)                             │
│  - Domain: peacock.yourdomain.com                           │
│  - Rate limiting                                            │
│  - Security headers                                         │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP (localhost)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  PEACOCK ENGINE (Systemd Service)                           │
│  - Port: 3099                                               │
│  - User: peacock (limited privileges)                       │
│  - Workers: 2                                               │
│  - Auto-restart on failure                                  │
└─────────────────────────────────────────────────────────────┘
```

## Security Features

- ✅ **UFW Firewall** - Blocks all ports except 22, 80, 443
- ✅ **Fail2ban** - Protects against brute force SSH attacks
- ✅ **Caddy Auto-SSL** - Automatic HTTPS certificates via Let's Encrypt
- ✅ **Security Headers** - HSTS, XSS protection, CSP
- ✅ **Non-root User** - Service runs as unprivileged `peacock` user
- ✅ **Systemd Hardening** - Read-only filesystem, no new privileges
- ✅ **PrivateTmp** - Isolated temp directories

## Recommended VPS Specs

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 1 vCPU | 2 vCPUs |
| **RAM** | 2 GB | 4 GB |
| **Disk** | 20 GB SSD | 40 GB SSD |
| **OS** | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |

## Deployment Methods

### Method 1: Quick Deploy (Recommended)

```bash
# Set your domain
export DOMAIN=peacock.yourdomain.com

# Run deploy
curl -sSL https://raw.githubusercontent.com/yourusername/ai-handler/main/deploy/quick-deploy.sh | sudo bash
```

### Method 2: Step-by-Step

```bash
# 1. Server setup (as root)
ssh root@your-vps-ip
cd /opt
git clone https://github.com/yourusername/ai-handler.git peacock-engine
cd peacock-engine
bash deploy/setup-server.sh

# 2. App setup (as peacock)
su - peacock -s /bin/bash
cd /opt/peacock-engine
cp deploy/.env.production.template .env
# Edit .env with your API keys
nano .env
bash deploy/install-app.sh
```

### Method 3: Docker

```bash
cd /opt/peacock-engine/deploy

# Copy and edit environment
cp ../.env.production.template ../.env
nano ../.env

# Run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f peacock-engine
```

## Post-Deployment

### Check Status

```bash
# Service status
sudo systemctl status peacock-engine

# View logs
sudo journalctl -u peacock-engine -f

# Health check
curl https://yourdomain.com/health
```

### Update Application

```bash
su - peacock -s /bin/bash
cd /opt/peacock-engine
bash deploy/update.sh
```

### Backup Data

```bash
su - peacock -s /bin/bash
cd /opt/peacock-engine
bash deploy/backup.sh
```

## Troubleshooting

### Service Won't Start

```bash
# Check Python syntax
sudo -u peacock /opt/peacock-engine/.venv/bin/python -m py_compile app/main.py

# Check environment
sudo -u peacock cat /opt/peacock-engine/.env

# View detailed logs
sudo journalctl -u peacock-engine -n 100 --no-pager
```

### 502 Bad Gateway

```bash
# Check if service is listening
sudo ss -tlnp | grep 3099

# Check Caddy
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl status caddy
```

### SSL Issues

```bash
# Force certificate renewal
sudo caddy reload --config /etc/caddy/Caddyfile

# Check Caddy logs
sudo journalctl -u caddy -f
```

## Environment Variables

See `.env.production.template` for all available options. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_KEYS` | Yes* | Groq API keys |
| `GOOGLE_KEYS` | Yes* | Google Gemini API keys |
| `DEEPSEEK_KEYS` | Yes* | DeepSeek API keys |
| `MISTRAL_KEYS` | Yes* | Mistral API keys |
| `PEACOCK_PERF_MODE` | No | `stealth`/`balanced`/`apex` |
| `CHAT_UI_ENABLED` | No | Enable web UI (`true`/`false`) |

*At least one AI provider key is required

## API Endpoints

Once deployed:

| Endpoint | URL |
|----------|-----|
| Health | `https://yourdomain.com/health` |
| Root | `https://yourdomain.com/` |
| Chat API | `https://yourdomain.com/v1/chat` |
| Models | `https://yourdomain.com/v1/chat/models` |
| Docs | `https://yourdomain.com/v1/docs/endpoints` |

## Support

- **PEACOCK ENGINE Issues**: Check `sudo journalctl -u peacock-engine -f`
- **Caddy Issues**: Check `sudo journalctl -u caddy -f`
- **System Issues**: Check `dmesg` and `/var/log/syslog`

---

**Ready for production! 🦚**
