#!/bin/bash
# PEACOCK ENGINE - Caddy Infrastructure Setup
# Creates log directories and sets permissions for the 4-subdomain cluster.

LOG_DIR="/var/log/caddy"
CADDY_USER="caddy"

echo "┍━──━──━──━──━──━──┑◆┍──━──━──━──━──━┑"
echo "   CADDY INFRASTRUCTURE SETUP"
echo "┕━──━──━──━──━──━──┑◆┍──━──━──━──━──━┙"

# Check for root
if [ "$EUID" -ne 0 ]; then
  echo "[!] Please run as root (sudo)"
  exit 1
fi

# Create log directory
if [ ! -d "$LOG_DIR" ]; then
    echo "[+] Creating $LOG_DIR..."
    mkdir -p "$LOG_DIR"
else
    echo "[✓] Log directory exists."
fi

# Ensure log files exist so Caddy doesn't complain
touch "$LOG_DIR/chat-access.log"
touch "$LOG_DIR/engine-access.log"
touch "$LOG_DIR/claw-access.log"
touch "$LOG_DIR/herbert-access.log"

# Set permissions
echo "[+] Setting permissions for $CADDY_USER..."
chown -R $CADDY_USER:$CADDY_USER "$LOG_DIR"
chmod -R 755 "$LOG_DIR"

echo "[✓] INFRASTRUCTURE_READY."
echo "[ℹ️] To apply the config, run: sudo caddy reload --config deploy/Caddyfile"
