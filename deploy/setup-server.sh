#!/bin/bash
# PEACOCK ENGINE - Hetzner VPS Production Setup Script
# Run as root on fresh Ubuntu 22.04/24.04 LTS

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PEACOCK_USER="peacock"
PEACOCK_DIR="/opt/peacock-engine"
DOMAIN=""

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║           🦚 PEACOCK ENGINE - VPS Setup Script               ║"
    echo "║              Production Deployment for Hetzner               ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Get domain from user
get_domain() {
    echo ""
    read -p "Enter your domain (e.g., peacock.yourdomain.com): " DOMAIN
    if [[ -z "$DOMAIN" ]]; then
        log_error "Domain is required"
        exit 1
    fi
    log_info "Domain set to: $DOMAIN"
}

# Update system
update_system() {
    log_info "Updating system packages..."
    apt-get update
    apt-get upgrade -y
    log_success "System updated"
}

# Install dependencies
install_dependencies() {
    log_info "Installing dependencies..."
    apt-get install -y \
        python3 \
        python3-venv \
        python3-pip \
        git \
        curl \
        wget \
        ufw \
        fail2ban \
        htop \
        ncdu \
        lsof
    log_success "Dependencies installed"
}

# Install Caddy
install_caddy() {
    log_info "Installing Caddy web server..."
    apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
    apt-get update
    apt-get install -y caddy
    log_success "Caddy installed"
}

# Create peacock user
create_user() {
    log_info "Creating peacock user..."
    if id "$PEACOCK_USER" &>/dev/null; then
        log_warn "User $PEACOCK_USER already exists"
    else
        useradd -r -s /bin/false -d "$PEACOCK_DIR" -m "$PEACOCK_USER"
        log_success "User $PEACOCK_USER created"
    fi
}

# Setup firewall
setup_firewall() {
    log_info "Configuring firewall..."
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow ssh
    ufw allow http
    ufw allow https
    ufw --force enable
    log_success "Firewall configured"
}

# Setup fail2ban
setup_fail2ban() {
    log_info "Configuring fail2ban..."
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
    log_success "Fail2ban configured"
}

# Main setup function
main() {
    print_banner
    check_root
    get_domain
    
    log_info "Starting PEACOCK ENGINE setup..."
    
    update_system
    install_dependencies
    install_caddy
    create_user
    setup_firewall
    setup_fail2ban
    
    log_success "Server preparation complete!"
    echo ""
    log_info "Next steps:"
    echo "  1. Clone your PEACOCK ENGINE repository to $PEACOCK_DIR"
    echo "  2. Run: chown -R $PEACOCK_USER:$PEACOCK_USER $PEACOCK_DIR"
    echo "  3. Copy deploy/.env.production to $PEACOCK_DIR/.env and configure"
    echo "  4. Run: su -s /bin/bash $PEACOCK_USER -c '$PEACOCK_DIR/deploy/install-app.sh'"
    echo "  5. Update Caddyfile domain and restart Caddy"
    echo ""
    log_info "Your server is ready for PEACOCK ENGINE deployment!"
}

main "$@"
