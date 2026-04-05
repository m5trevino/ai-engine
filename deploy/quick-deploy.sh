#!/bin/bash
# PEACOCK ENGINE - Quick Deploy Script
# One-command deployment for Hetzner VPS
# Usage: curl -sSL https://raw.githubusercontent.com/yourusername/ai-handler/main/deploy/quick-deploy.sh | sudo bash

set -e

REPO_URL="${REPO_URL:-https://github.com/yourusername/ai-handler.git}"
DOMAIN="${DOMAIN:-}"

echo "🦚 PEACOCK ENGINE - Quick Deploy"
echo "================================="
echo ""

# Check root
if [[ $EUID -ne 0 ]]; then
    echo "❌ This script must be run as root"
    exit 1
fi

# Get domain if not set
if [[ -z "$DOMAIN" ]]; then
    read -p "Enter your domain (e.g., peacock.yourdomain.com): " DOMAIN
fi

if [[ -z "$DOMAIN" ]]; then
    echo "❌ Domain is required"
    exit 1
fi

echo "📋 Configuration:"
echo "   Domain: $DOMAIN"
echo "   Repo: $REPO_URL"
echo ""

# Step 1: Install dependencies
echo "📦 Installing dependencies..."
apt-get update -qq
apt-get install -y -qq git curl wget python3 python3-venv python3-pip ufw fail2ban debian-keyring debian-archive-keyring apt-transport-https lsof

# Step 2: Install Caddy
echo "🌐 Installing Caddy..."
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' 2>/dev/null | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' 2>/dev/null | tee /etc/apt/sources.list.d/caddy-stable.list > /dev/null
apt-get update -qq && apt-get install -y -qq caddy

# Step 3: Create user
echo "👤 Creating peacock user..."
useradd -r -s /bin/false -d /opt/peacock-engine -m peacock 2>/dev/null || echo "User already exists"

# Step 4: Clone repo
echo "📥 Cloning repository..."
if [[ -d /opt/peacock-engine/.git ]]; then
    echo "   Repository exists, pulling latest..."
    cd /opt/peacock-engine && git pull
else
    rm -rf /opt/peacock-engine
    git clone "$REPO_URL" /opt/peacock-engine
fi
chown -R peacock:peacock /opt/peacock-engine

# Step 5: Setup environment
echo "⚙️ Setting up environment..."
if [[ ! -f /opt/peacock-engine/.env ]]; then
    cp /opt/peacock-engine/deploy/.env.production.template /opt/peacock-engine/.env
    echo "   ⚠️ Created .env from template. EDIT THIS FILE with your API keys!"
fi

# Step 6: Install app
echo "🚀 Installing application..."
su -s /bin/bash peacock -c "
cd /opt/peacock-engine
python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
mkdir -p vault/successful vault/failed logs
"

# Step 7: Setup systemd
echo "🔧 Configuring systemd..."
cp /opt/peacock-engine/deploy/peacock-engine.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable peacock-engine

# Step 8: Setup Caddy
echo "🔒 Configuring Caddy..."
sed "s/peacock.yourdomain.com/$DOMAIN/g" /opt/peacock-engine/deploy/Caddyfile > /etc/caddy/Caddyfile
mkdir -p /var/log/caddy
caddy validate --config /etc/caddy/Caddyfile > /dev/null 2>&1 && echo "   ✓ Caddy config valid"

# Step 9: Firewall
echo "🛡️ Configuring firewall..."
ufw default deny incoming -q
ufw default allow outgoing -q
ufw allow ssh -q
ufw allow http -q
ufw allow https -q
ufw --force enable

# Step 10: Fail2ban
echo "🚫 Configuring fail2ban..."
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
EOF
systemctl restart fail2ban

# Step 11: Start services
echo "▶️ Starting services..."
systemctl start peacock-engine
sleep 2
systemctl reload caddy

# Check status
echo ""
echo "📊 Status Check:"
if systemctl is-active --quiet peacock-engine; then
    echo "   ✅ PEACOCK ENGINE: RUNNING"
else
    echo "   ❌ PEACOCK ENGINE: FAILED"
fi

if systemctl is-active --quiet caddy; then
    echo "   ✅ Caddy: RUNNING"
else
    echo "   ❌ Caddy: FAILED"
fi

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "🔗 Your API: https://$DOMAIN"
echo ""
echo "⚠️ IMPORTANT: Edit your .env file to add API keys:"
echo "   sudo nano /opt/peacock-engine/.env"
echo ""
echo "🔄 Then restart the service:"
echo "   sudo systemctl restart peacock-engine"
echo ""
echo "📖 View logs:"
echo "   sudo journalctl -u peacock-engine -f"
