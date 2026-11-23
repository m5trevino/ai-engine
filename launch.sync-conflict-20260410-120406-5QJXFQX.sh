#!/bin/bash
# 🦚 PEACOCK ENGINE V3 - LAUNCHER
# High-performance AI Orchestrator Boot Script

PORT=3099
TUNNEL=false
QUIET=false
LOG_FILE="server.log"

# Print Header
echo -e "\033[1;36m┎━─━─━─━─━─━─━─━─━─━─━─━─━─━─━┒\033[0m"
echo -e "\033[1;36m  🦚 AI-ENGINE V3 BOOT\033[0m"
echo -e "\033[1;36m┖━─━─━─━─━─━─━─━─━─━─━─━─━─━─━┚\033[0m"

# Parse Arguments
for arg in "$@"; do
    case $arg in
        --tunnel)
            TUNNEL=true
            shift
            ;;
        --port=*)
            PORT="${arg#*=}"
            shift
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        --help)
            echo "Usage: ./launch.sh [OPTIONS]"
            echo "  --tunnel    Enable MetroPCS TUN0 SOCKS5 Proxy"
            echo "  --port=N    Set custom port (default: 3099)"
            echo "  --quiet     Run in quiet mode (output to server.log)"
            exit 0
            ;;
    esac
done

# 1. Environment Check
if [ -f ".env" ]; then
    echo -e "\033[32m[✓]\033[0m Environment detected (.env)"
else
    echo -e "\033[33m[⚠]\033[0m No .env found. Using system environment."
fi

# 2. Port Cleanup
PID=$(lsof -ti:$PORT)
if [ -n "$PID" ]; then
    echo -e "\033[33m[!]\033[0m Port $PORT occupied by PID $PID. Clearing path..."
    kill -9 $PID
    echo -e "\033[32m[✓]\033[0m Path cleared."
fi

# 3. Tunnel Configuration
if [ "$TUNNEL" = true ]; then
    export PEACOCK_TUNNEL="true"
    echo -e "\033[1;34m[🛰️]\033[0m TUNNEL MODE ACTIVE (SOCKS5: 127.0.0.1:1081)"
else
    export PEACOCK_TUNNEL="false"
fi

# 4. Venv Activation
if [ -d ".venv" ]; then
    source .venv/bin/activate
    UVICORN_BIN="./.venv/bin/uvicorn"
    echo -e "\033[32m[✓]\033[0m Virtual Environment active."
else
    echo -e "\033[31m[✗]\033[0m ERROR: .venv not found. Run 'python3 -m venv .venv' first."
    exit 1
fi

# 5. Ignition
echo -e "\033[1;32m[🚀] IGNITION.\033[0m Running on port $PORT..."

if [ "$QUIET" = true ]; then
    echo -e "\033[37m[STAY STEALTHY] Logging to $LOG_FILE\033[0m"
    nohup "$UVICORN_BIN" app.main:app --host 0.0.0.0 --port $PORT > "$LOG_FILE" 2>&1 &
    echo -e "\033[32m[✓] ENGINE RUNNING IN BACKGROUND (PID: $!)\033[0m"
else
    "$UVICORN_BIN" app.main:app --host 0.0.0.0 --port $PORT
fi
