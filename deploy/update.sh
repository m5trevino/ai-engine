#!/bin/bash
# PEACOCK ENGINE - Quick Update Script
# Run as peacock user to update and restart the service

set -e

cd /opt/peacock-engine

echo "🦚 PEACOCK ENGINE Update Script"
echo "================================"

# Pull latest changes
echo "📥 Pulling latest changes..."
git pull

# Activate venv and update dependencies
echo "📦 Updating dependencies..."
source .venv/bin/activate
pip install -r requirements.txt

# Test the application
echo "🧪 Testing application..."
python -m py_compile app/main.py
python -c "from app.main import app; print('✓ Import OK')"

# Restart service
echo "🔄 Restarting service..."
sudo systemctl restart peacock-engine

# Wait and check status
sleep 2
if sudo systemctl is-active --quiet peacock-engine; then
    echo ""
    echo "✅ PEACOCK ENGINE updated and running!"
    echo ""
    echo "Health check:"
    curl -s http://localhost:3099/health | python -m json.tool
else
    echo ""
    echo "❌ Service failed to start. Check logs:"
    echo "   sudo journalctl -u peacock-engine -n 50"
    exit 1
fi
