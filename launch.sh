#!/bin/bash
PORT=3099
if [ -d ".venv" ]; then
    source .venv/bin/activate
    UVICORN_BIN="./.venv/bin/uvicorn"
    echo -e "\033[32m[✓]\033[0m Virtual Environment active."
else
    echo -e "\033[31m[✗]\033[0m ERROR: .venv not found."
    exit 1
fi
echo -e "\033[1;32m[🚀] IGNITION.\033[0m Running on port $PORT..."
nohup "$UVICORN_BIN" app.main:app --host 0.0.0.0 --port $PORT > server.log 2>&1 &
echo -e "\033[32m[✓] ENGINE RUNNING IN BACKGROUND (PID: $!)\033[0m"
