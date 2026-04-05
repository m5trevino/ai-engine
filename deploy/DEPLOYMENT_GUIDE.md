# PEACOCK ENGINE - Hetzner VPS Deployment Guide

Complete guide for deploying PEACOCK ENGINE on a Hetzner VPS for production use.

## Prerequisites

- A Hetzner Cloud account
- A domain name (pointed to your VPS IP)
- Your API keys for AI providers (Groq, Google, DeepSeek, Mistral)

## Step 1: Create VPS

1. Log into [Hetzner Cloud Console](https://console.hetzner.cloud/)
2. Create a new project (or use existing)
3. Add a server:
   - **Location**: Choose closest to your users
   - **Image**: Ubuntu 24.04 LTS (recommended)
   - **Type**: CPX11 or higher (2 vCPUs, 4GB RAM minimum)
   - **Networking**: IPv4 enabled
   - **SSH Key**: Add your SSH public key
   - **Name**: `peacock-engine`

4. Note the server IP address

## Step 2: DNS Configuration

Point your domain to the VPS:

```
Type: A
Name: peacock (or subdomain)
Value: <your-vps-ip>
TTL: 3600
```

Wait for DNS propagation (can take up to 24 hours, usually faster).

## Step 3: Server Setup

SSH into your VPS as root:

```bash
ssh root@<your-vps-ip>
```

Clone the repository and run setup:

```bash
# Install git
cd /opt
git clone https://github.com/yourusername/ai-handler.git peacock-engine
cd peacock-engine

# Run server setup (as root)
bash deploy/setup-server.sh
```

This will:
- Update system packages
- Install Python, Caddy, and dependencies
- Create `peacock` user
- Configure firewall (UFW)
- Setup fail2ban for security

## Step 4: Configure Environment

Switch to peacock user:

```bash
su - peacock
cd /opt/peacock-engine
```

Copy the environment template:

```bash
cp deploy/.env.production.template .env
nano .env  # or use your preferred editor
```

Edit the `.env` file with your actual API keys:

```env
# Required: Add at least one AI provider key
GROQ_KEYS="your_groq_key_here"
GOOGLE_KEYS="your_google_key_here"
DEEPSEEK_KEYS="your_deepseek_key_here"
MISTRAL_KEYS="your_mistral_key_here"

# Optional: Performance mode
PEACOCK_PERF_MODE=balanced

# Optional: Enable features
CHAT_UI_ENABLED=false
PEACOCK_DEBUG=false
```

Save and exit (Ctrl+O, Enter, Ctrl+X in nano).

## Step 5: Install Application

Still as `peacock` user:

```bash
cd /opt/peacock-engine
bash deploy/install-app.sh
```

This will:
- Create Python virtual environment
- Install dependencies
- Test the application
- Install systemd service
- Configure Caddy reverse proxy
- Start the service

## Step 6: Verify Deployment

Check service status:

```bash
sudo systemctl status peacock-engine
```

View logs:

```bash
sudo journalctl -u peacock-engine -f
```

Test the API:

```bash
# Health check
curl https://yourdomain.com/health

# List models
curl https://yourdomain.com/v1/chat/models

# Test chat
curl -X POST https://yourdomain.com/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.0-flash-lite",
    "prompt": "Hello, are you working?"
  }'
```

## Step 7: Security Hardening (Optional but Recommended)

### Disable root SSH login

```bash
sudo nano /etc/ssh/sshd_config
```

Set:
```
PermitRootLogin no
PasswordAuthentication no
```

Restart SSH:
```bash
sudo systemctl restart sshd
```

### Setup automated security updates

```bash
sudo apt-get install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Enable automatic backups

Consider setting up:
- Hetzner snapshots
- Database backup to S3
- Log rotation

## Maintenance Commands

### Restart service

```bash
sudo systemctl restart peacock-engine
```

### View logs

```bash
# Real-time logs
sudo journalctl -u peacock-engine -f

# Last 100 lines
sudo journalctl -u peacock-engine -n 100

# Logs since last boot
sudo journalctl -u peacock-engine -b
```

### Update application

```bash
# As peacock user
cd /opt/peacock-engine
git pull
source .venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl restart peacock-engine
```

### Check Caddy logs

```bash
sudo tail -f /var/log/caddy/peacock-access.log
```

### Firewall management

```bash
# Check status
sudo ufw status verbose

# Allow specific IP
sudo ufw allow from 1.2.3.4

# Block IP
sudo ufw deny from 1.2.3.4
```

## Troubleshooting

### Service won't start

```bash
# Check for syntax errors
sudo -u peacock /opt/peacock-engine/.venv/bin/python -m py_compile app/main.py

# Check environment variables
sudo -u peacock cat /opt/peacock-engine/.env

# Check detailed logs
sudo journalctl -u peacock-engine --no-pager -n 50
```

### 502 Bad Gateway

```bash
# Check if service is running
sudo systemctl is-active peacock-engine

# Check if listening on correct port
sudo ss -tlnp | grep 3099

# Check Caddy configuration
sudo caddy validate --config /etc/caddy/Caddyfile
```

### SSL certificate issues

```bash
# Force certificate renewal
sudo caddy reload --config /etc/caddy/Caddyfile

# Check certificate status
sudo caddy list-modules | grep tls
```

### High memory usage

```bash
# Monitor resources
htop

# Check for memory leaks
sudo journalctl -u peacock-engine | grep -i "memory\|killed"
```

## API Usage Examples

### Health Check

```bash
curl https://yourdomain.com/health
```

### List Models

```bash
curl https://yourdomain.com/v1/chat/models
```

### Simple Chat

```bash
curl -X POST https://yourdomain.com/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.0-flash-lite",
    "prompt": "Explain quantum computing",
    "format": "text"
  }'
```

### With File Context

```bash
curl -X POST https://yourdomain.com/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.1-8b-instant",
    "prompt": "Review this code",
    "files": ["/path/to/file.py"],
    "format": "text"
  }'
```

### Structured Output (JSON)

```bash
curl -X POST https://yourdomain.com/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.0-flash-lite",
    "prompt": "Extract name and age from: John is 25",
    "format": "json"
  }'
```

## Monitoring

### Setup basic monitoring

```bash
# Install netdata (optional)
bash <(curl -Ss https://my-netdata.io/kickstart.sh)
```

### Health check endpoint

Add to your monitoring:

```bash
# Check every minute
curl -f https://yourdomain.com/health || alert
```

## Support

For issues specific to:
- **PEACOCK ENGINE**: Check logs with `sudo journalctl -u peacock-engine -f`
- **Caddy**: Check `/var/log/caddy/` and run `sudo caddy validate`
- **System**: Check `dmesg` and system logs

---

**🦚 Your PEACOCK ENGINE is now production-ready!**
