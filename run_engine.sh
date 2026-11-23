#!/bin/bash

PORT=3099
USE_PROXY=true

# Parse Arguments
for arg in "$@"; do
    case $arg in
        --no-proxy)
            USE_PROXY=false
            shift
            ;;
        --proxy=*)
            export ALL_PROXY="${arg#*=}"
            USE_PROXY=true
            shift
            ;;
    esac
done

if [ "$USE_PROXY" = false ]; then
    echo " [🚫] DISABLING PROXIES (Overriding .env)..."
    export ALL_PROXY=""
    export LOCAL_PROXY=""
    export PROXY_URL=""
    export PROXY_ENABLED="false"
    unset http_proxy
    unset https_proxy
    unset HTTP_PROXY
    unset HTTPS_PROXY
elif [ -n "$ALL_PROXY" ]; then
    echo " [🌐] PROXY DETECTED: $ALL_PROXY"
fi

echo " [⚙️] PEACOCK ENGINE INIT..."
echo " [🔍] Scanning Port $PORT..."

# Find and Kill Process on Port
PID=$(lsof -ti:$PORT)

if [ -n "$PID" ]; then
    echo " [⚠️] FOUND STALE INSTANCE (PID: $PID). TERMINATING..."
    kill -9 $PID
    echo " [💀] TARGET DESTROYED."
else
    echo " [✅] PORT CLEAN."
fi

# Activate Venv
echo " [🔋] ACTIVATING VENV..."
if [ -f ".venv/bin/activate" ]; then
    . .venv/bin/activate
else
    echo " [❌] VENV NOT FOUND!"
    exit 1
fi

# Start Engine
echo " [🚀] IGNITION."
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
