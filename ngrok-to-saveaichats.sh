#!/bin/bash
# 🌉 NGROK → SAVE-AICHATS BRIDGE
# 
# This script updates save-aichats.com/peacock to redirect to your ngrok URL
# 
# USAGE:
#   1. Start ngrok: ngrok http 3099
#   2. Run: ./ngrok-to-saveaichats.sh
#   3. It updates the redirect page and pushes to GitHub
#   4. Render auto-deploys
#   5. Visit: save-aichats.com/peacock

# === CONFIG ===
SAVE_AICHATS_DIR="/root/save-aichats"      # Where save-aichats repo is on VPS
PEACOCK_PAGE="frontend/public/peacock.html"  # The redirect page
NGROK_API="http://localhost:4040/api/tunnels"

# === COLORS ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🌉 NGROK → SAVE-AICHATS BRIDGE${NC}"
echo "================================"
echo ""

# Check if save-aichats directory exists
if [ ! -d "$SAVE_AICHATS_DIR" ]; then
    echo -e "${RED}✗ Error: $SAVE_AICHATS_DIR not found!${NC}"
    echo "Make sure save-aichats repo is cloned to /root/save-aichats"
    exit 1
fi

# Check if ngrok is running
echo -n "Checking ngrok... "
NGROK_URL=$(curl -s $NGROK_API 2>/dev/null | grep -o '"public_url":"https://[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$NGROK_URL" ]; then
    echo -e "${RED}✗ NOT RUNNING${NC}"
    echo ""
    echo "Start ngrok first:"
    echo "  ngrok http 3099"
    exit 1
fi

echo -e "${GREEN}✓ $NGROK_URL${NC}"

# Update the redirect page
echo -n "Updating redirect page... "
PEACOCK_PATH="$SAVE_AICHATS_DIR/$PEACOCK_PAGE"

# Check if page exists
if [ ! -f "$PEACOCK_PATH" ]; then
    echo -e "${RED}✗ NOT FOUND${NC}"
    echo "Expected: $PEACOCK_PATH"
    exit 1
fi

# Replace the placeholder URL with actual ngrok URL
sed -i "s|https://placeholder-ngrok-url.ngrok-free.app|$NGROK_URL|g" "$PEACOCK_PATH"

echo -e "${GREEN}✓ DONE${NC}"

# Commit and push
echo ""
echo -e "${BLUE}Pushing to GitHub...${NC}"
cd "$SAVE_AICHATS_DIR" || exit 1

git add "$PEACOCK_PAGE"
git commit -m "Update ngrok redirect: $NGROK_URL"

if git push origin master 2>&1; then
    echo -e "${GREEN}✓ Pushed successfully!${NC}"
    echo ""
    echo -e "${GREEN}🦚 Render will auto-deploy in ~1 minute${NC}"
    echo ""
    echo -e "${GREEN}Your bridge is live at:${NC}"
    echo -e "${GREEN}  https://save-aichats.com/peacock${NC}"
    echo -e "${GREEN}  → $NGROK_URL${NC}"
else
    echo -e "${RED}✗ Push failed!${NC}"
    echo "Check your git remote and credentials."
    exit 1
fi
