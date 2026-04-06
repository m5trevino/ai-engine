#!/bin/bash
# 🌉 NGROK ROTATOR - Auto-rotate auth tokens to avoid rate limits
# 
# This script rotates between multiple ngrok auth tokens and tracks usage.
# When one token hits limits, it automatically switches to the next.
#
# USAGE:
#   ./ngrok-rotator.sh start    - Start ngrok with rotation
#   ./ngrok-rotator.sh status   - Show current token & uptime
#   ./ngrok-rotator.sh next     - Manually switch to next token
#   ./ngrok-rotator.sh logs     - Show token usage history

set -e

# === CONFIG ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_FILE="$SCRIPT_DIR/.ngrok-rotator-state"
LOG_FILE="$SCRIPT_DIR/ngrok-rotation.log"
TOKENS=(
    "cr_2zWWZOntNCK55Drl38IZqWz7IJU"
    "cr_3BxpsaJNAd8hs62krAlkqILRB9S"
    "cr_3Bxq5YK4iOEhnnl8HwePU4PUta1"
    "cr_3BxqIJFhMeLc6Q3cL4xy7Ow4maq"
)
PORT=3099

# === COLORS ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# === FUNCTIONS ===

get_current_index() {
    if [ -f "$STATE_FILE" ]; then
        cat "$STATE_FILE"
    else
        echo 0
    fi
}

set_current_index() {
    echo "$1" > "$STATE_FILE"
}

get_current_token() {
    local idx=$(get_current_index)
    echo "${TOKENS[$idx]}"
}

log_rotation() {
    local token=$1
    local action=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] Token ${token:0:10}... - $action" >> "$LOG_FILE"
}

show_status() {
    local idx=$(get_current_index)
    local token=$(get_current_token)
    
    echo -e "${BLUE}🌉 NGROK ROTATOR STATUS${NC}"
    echo "======================="
    echo ""
    echo "Total tokens: ${#TOKENS[@]}"
    echo "Current token index: $((idx + 1)) of ${#TOKENS[@]}"
    echo "Current token: ${token:0:15}..."
    echo ""
    
    if pgrep -x "ngrok" > /dev/null; then
        echo -e "${GREEN}● Ngrok is RUNNING${NC}"
        local url=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*"' | head -1 | cut -d'"' -f4)
        if [ -n "$url" ]; then
            echo "URL: $url"
        fi
    else
        echo -e "${RED}○ Ngrok is STOPPED${NC}"
    fi
    echo ""
    
    # Show token usage history
    if [ -f "$LOG_FILE" ]; then
        echo "Recent rotations:"
        tail -5 "$LOG_FILE" | sed 's/^/  /'
    fi
}

rotate_to_next() {
    local current_idx=$(get_current_index)
    local next_idx=$(((current_idx + 1) % ${#TOKENS[@]}))
    
    log_rotation "${TOKENS[$current_idx]}" "ROTATED_OUT"
    set_current_index $next_idx
    log_rotation "${TOKENS[$next_idx]}" "ROTATED_IN"
    
    echo -e "${YELLOW}→ Rotated to token $((next_idx + 1)) of ${#TOKENS[@]}${NC}"
}

start_ngrok() {
    local idx=$(get_current_index)
    local token="${TOKENS[$idx]}"
    
    echo -e "${BLUE}🚀 Starting ngrok with token $((idx + 1))/${#TOKENS[@]}${NC}"
    echo "Token: ${token:0:15}..."
    echo ""
    
    # Kill any existing ngrok
    pkill -x ngrok 2>/dev/null || true
    sleep 1
    
    # Configure ngrok with current token (show output for debugging)
    echo "Configuring ngrok..."
    ngrok config add-authtoken "$token"
    
    log_rotation "$token" "STARTED"
    
    # Start ngrok in background
    ngrok http $PORT > /tmp/ngrok.log 2>&1 &
    NGROK_PID=$!
    
    # Wait for tunnel
    echo -n "Waiting for tunnel..."
    for i in {1..30}; do
        sleep 1
        local url=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https://[^"]*"' | head -1 | cut -d'"' -f4)
        if [ -n "$url" ]; then
            echo -e "\n${GREEN}✓ Tunnel active!${NC}"
            echo -e "${GREEN}URL: $url${NC}"
            echo ""
            echo "Monitor with: tail -f /tmp/ngrok.log"
            echo "Stop with: kill $NGROK_PID"
            return 0
        fi
        echo -n "."
    done
    
    echo -e "\n${RED}✗ Failed to start tunnel${NC}"
    kill $NGROK_PID 2>/dev/null || true
    return 1
}

show_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo -e "${BLUE}📊 TOKEN USAGE HISTORY${NC}"
        echo "======================"
        cat "$LOG_FILE"
    else
        echo "No logs yet."
    fi
}

# === MAIN ===

case "${1:-status}" in
    start)
        start_ngrok
        ;;
    status)
        show_status
        ;;
    next)
        rotate_to_next
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "Usage: $0 {start|status|next|logs}"
        echo ""
        echo "Commands:"
        echo "  start   - Start ngrok with current token"
        echo "  status  - Show current token and tunnel status"
        echo "  next    - Rotate to next token"
        echo "  logs    - Show token usage history"
        exit 1
        ;;
esac
