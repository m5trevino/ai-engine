#!/bin/bash
# 🦚 PEACOCK ENGINE START - Caddy Production Version
# Starts engine → updates save-aichats portal via Caddy domain

set -e

# Detect roots
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PEACOCK_DIR="$SCRIPT_DIR"
HETZNER_ROOT="$(dirname "$PEACOCK_DIR")"
LOG_DIR="$HETZNER_ROOT/logs"
mkdir -p $LOG_DIR

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║         🦚 PEACOCK ENGINE - PRODUCTION START           ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Kill any existing engine processes
echo -e "${YELLOW}🧹 Cleaning up existing engine processes...${NC}"
pkill -f "python -m app.main" 2>/dev/null || true
sleep 2

# Step 1: Start PEACOCK ENGINE
echo ""
echo -e "${CYAN}[1/2] Starting PEACOCK ENGINE (Port 3099)...${NC}"
cd $PEACOCK_DIR
source .venv/bin/activate

# Start engine in background, log to file
nohup $PEACOCK_DIR/.venv/bin/python -m app.main > $LOG_DIR/engine.log 2>&1 &
ENGINE_PID=$!
echo $ENGINE_PID > /tmp/engine.pid

echo -n "Waiting for engine..."
for i in {1..30}; do
    if curl -s http://localhost:3099/health > /dev/null 2>&1; then
        echo -e "\n${GREEN}✓ Engine ONLINE (PID: $ENGINE_PID)${NC}"
        break
    fi
    sleep 1
    echo -n "."
done

if ! curl -s http://localhost:3099/health > /dev/null 2>&1; then
    echo -e "\n${RED}✗ Engine failed to start!${NC}"
    echo "Check logs: tail -f $LOG_DIR/engine.log"
    exit 1
fi

# Step 2: Update save-aichats portal
echo ""
echo -e "${CYAN}[2/2] Updating save-aichats portal...${NC}"

if [ -f "$PEACOCK_DIR/update-peacock-portal.sh" ]; then
    echo -e "${BLUE}📡 Triggering portal synchronization...${NC}"
    bash "$PEACOCK_DIR/update-peacock-portal.sh"
    echo -e "${GREEN}✓ Portal updated via Caddy endpoints.${NC}"
else
    echo -e "${YELLOW}! update-peacock-portal.sh not found, skipping portal sync${NC}"
fi

echo ""
echo -e "${GREEN}🦚 PEACOCK ENGINE MISSION READY${NC}"
echo "=================================="
echo ""
echo -e "${YELLOW}API: https://engine.save-aichats.com${NC}"
echo -e "${YELLOW}UI:  https://chat.save-aichats.com${NC}"
echo ""
echo -e "${CYAN}📜 Logs:${NC}"
echo -e "  Engine: tail -f $LOG_DIR/engine.log"
echo ""
echo -e "${YELLOW}⛔ To stop:${NC} kill $ENGINE_PID"
echo ""
