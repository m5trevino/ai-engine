#!/bin/bash
# PEACOCK ENGINE - Application Installation Script
# Run as peacock user after setup-server.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PEACOCK_DIR="/opt/peacock-engine"

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
    echo "║           🦚 PEACOCK ENGINE - App Installation               ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check if running as correct user
check_user() {
    if [[ "$USER" != "peacock" ]]; then
        log_error "This script must be run as peacock user"
        exit 1
    fi
}

# Check if we're in the right directory
check_directory() {
    if [[ "$(pwd)" != "$PEACOCK_DIR" ]]; then
        log_error "Must be run from $PEACOCK_DIR"
        exit 1
    fi
}

# Create virtual environment
setup_venv() {
    log_info "Setting up Python virtual environment..."
    if [[ -d ".venv" ]]; then
        log_warn "Virtual environment already exists"
    else
        python3 -m venv .venv
        log_success "Virtual environment created"
    fi
}

# Install Python dependencies
install_deps() {
    log_info "Installing Python dependencies..."
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    log_success "Dependencies installed"
}

# Create necessary directories
create_dirs() {
    log_info "Creating necessary directories..."
    mkdir -p vault/successful
    mkdir -p vault/failed
    mkdir -p logs
    log_success "Directories created"
}

# Test the application
test_app() {
    log_info "Testing application..."
    source .venv/bin/activate
    
    # Quick Python syntax check
    python -m py_compile app/main.py
    log_success "Python syntax OK"
    
    # Check if we can import main modules
    python -c "from app.main import app; print('FastAPI app imports successfully')"
    log_success "Application imports OK"
}

# Install systemd service
install_service() {
    log_info "Installing systemd service..."
    
    # Service file needs to be copied by root
    sudo cp deploy/peacock-engine.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable peacock-engine
    
    log_success "Systemd service installed"
}

# Install Caddy config
install_caddy() {
    log_info "Installing Caddy configuration..."
    
    # Get domain from user
    read -p "Enter your domain (e.g., peacock.yourdomain.com): " DOMAIN
    
    # Update Caddyfile with domain
    sed "s/peacock.yourdomain.com/$DOMAIN/g" deploy/Caddyfile | sudo tee /etc/caddy/Caddyfile > /dev/null
    
    # Create log directory
    sudo mkdir -p /var/log/caddy
    
    # Validate and reload Caddy
    sudo caddy validate --config /etc/caddy/Caddyfile
    sudo systemctl reload caddy
    
    log_success "Caddy configured for $DOMAIN"
}

# Start the service
start_service() {
    log_info "Starting PEACOCK ENGINE..."
    sudo systemctl start peacock-engine
    sleep 2
    
    if sudo systemctl is-active --quiet peacock-engine; then
        log_success "PEACOCK ENGINE is running!"
        sudo systemctl status peacock-engine --no-pager
    else
        log_error "Failed to start PEACOCK ENGINE"
        sudo systemctl status peacock-engine --no-pager
        exit 1
    fi
}

# Main function
main() {
    print_banner
    check_user
    check_directory
    
    log_info "Starting PEACOCK ENGINE installation..."
    
    setup_venv
    install_deps
    create_dirs
    test_app
    install_service
    install_caddy
    start_service
    
    echo ""
    log_success "PEACOCK ENGINE installation complete!"
    echo ""
    log_info "Your API is available at:"
    echo "  - HTTP:  http://$DOMAIN"
    echo "  - HTTPS: https://$DOMAIN (auto-SSL enabled)"
    echo ""
    log_info "Health check: curl https://$DOMAIN/health"
    log_info "API docs:     curl https://$DOMAIN/v1/docs/endpoints"
    echo ""
    log_info "Useful commands:"
    echo "  sudo systemctl status peacock-engine  # Check service status"
    echo "  sudo journalctl -u peacock-engine -f  # View logs"
    echo "  sudo systemctl restart peacock-engine # Restart service"
}

main "$@"
