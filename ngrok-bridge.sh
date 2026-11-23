#!/bin/bash
# 🌉 NGROK BRIDGE - Auto-update redirect on your domain
# 
# This script monitors ngrok and uploads a redirect file to your web host
# whenever the tunnel URL changes. Your domain always points to current ngrok.
#
# USAGE:
#   1. Start ngrok: ngrok http 3099
#   2. Run this: ./ngrok-bridge.sh
#   3. Visit your domain - always redirects to current ngrok URL

# === CONFIG - EDIT THESE ===
FTP_HOST="your-ftp-host.com"          # Your web host FTP server
FTP_USER="your-username"              # FTP username
FTP_PASS="your-password"              # FTP password (or use .netrc)
FTP_PATH="/public_html/"              # Path on server (usually /public_html/ or /htdocs/)
DOMAIN="yourdomain.com"               # Your domain
NGROK_API="http://localhost:4040/api/tunnels"  # Ngrok local API
CHECK_INTERVAL=30                     # Seconds between checks

# === COLORS ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🌉 NGROK BRIDGE${NC}"
echo "=================="
echo ""
echo "Domain: $DOMAIN"
echo "FTP: $FTP_USER@$FTP_HOST"
echo ""

# Store last known URL
LAST_URL=""

# Function to get ngrok URL
get_ngrok_url() {
    curl -s $NGROK_API | grep -o '"public_url":"https://[^"]*"' | head -1 | cut -d'"' -f4
}

# Function to create redirect HTML
create_redirect_html() {
    local url=$1
    cat > /tmp/ngrok-redirect.html << EOF
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0; url=$url">
    <title>Redirecting...</title>
    <style>
        body { font-family: system-ui, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #0f0f0f; color: #fff; }
        .box { text-align: center; padding: 2rem; }
        a { color: #4CAF50; }
    </style>
</head>
<body>
    <div class="box">
        <h2>🦚 Redirecting to PEACOCK ENGINE...</h2>
        <p>If not redirected, <a href="$url">click here</a></p>
        <p><small>Tunnel: $url</small></p>
    </div>
</body>
</html>
EOF
}

# Function to upload via FTP
upload_ftp() {
    local file=$1
    local remote_name=$2
    
    # Try lftp first (more reliable), fallback to ftp
    if command -v lftp &> /dev/null; then
        lftp -u "$FTP_USER,$FTP_PASS" "$FTP_HOST" << EOF
set ssl:verify-certificate no
set ftp:ssl-allow no
cd $FTP_PATH
put $file -o $remote_name
bye
EOF
        return $?
    else
        # Fallback to ftp command
        ftp -n "$FTP_HOST" << EOF
user $FTP_USER $FTP_PASS
cd $FTP_PATH
put $file $remote_name
bye
EOF
        return $?
    fi
}

# Main loop
echo -e "${YELLOW}Waiting for ngrok to start...${NC}"
echo "(Make sure ngrok is running: ngrok http 3099)"
echo ""

while true; do
    # Check if ngrok API is available
    CURRENT_URL=$(get_ngrok_url)
    
    if [ -z "$CURRENT_URL" ]; then
        echo -e "${YELLOW}⏳ Ngrok not running or no tunnel yet...${NC}"
        sleep 5
        continue
    fi
    
    # Check if URL changed
    if [ "$CURRENT_URL" != "$LAST_URL" ]; then
        echo -e "${GREEN}✓ New ngrok URL detected: $CURRENT_URL${NC}"
        
        # Create redirect file
        create_redirect_html "$CURRENT_URL"
        
        # Upload to server
        echo -n "Uploading to $DOMAIN... "
        if upload_ftp "/tmp/ngrok-redirect.html" "index.html"; then
            echo -e "${GREEN}✓ DONE${NC}"
            echo ""
            echo -e "${GREEN}🦚 Your domain is live:${NC}"
            echo -e "${GREEN}   https://$DOMAIN${NC}"
            echo -e "${GREEN}   → $CURRENT_URL${NC}"
            echo ""
            LAST_URL="$CURRENT_URL"
        else
            echo -e "${RED}✗ FTP upload failed!${NC}"
            echo "Check your FTP credentials in the script config."
        fi
    fi
    
    sleep $CHECK_INTERVAL
done
