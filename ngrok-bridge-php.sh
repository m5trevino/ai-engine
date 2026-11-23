#!/bin/bash
# 🌉 NGROK BRIDGE (PHP Version)
# 
# This version uploads a PHP redirect script once, then just updates
# a tiny text file with the current ngrok URL. Much faster uploads!
#
# USAGE:
#   1. Edit CONFIG section below
#   2. Run: ./ngrok-bridge-php.sh --init    (uploads PHP file once)
#   3. Run: ./ngrok-bridge-php.sh           (updates URL when ngrok starts)

# === CONFIG - EDIT THESE ===
FTP_HOST="your-ftp-host.com"          # Your web host FTP server
FTP_USER="your-username"              # FTP username  
FTP_PASS="your-password"              # FTP password
FTP_PATH="/public_html/"              # Path on server
DOMAIN="yourdomain.com"               # Your domain
NGROK_API="http://localhost:4040/api/tunnels"
CHECK_INTERVAL=30

# === PHP REDIRECT SCRIPT (uploaded once) ===
PHP_SCRIPT='<?php
// PEACOCK ENGINE Ngrok Bridge
$url_file = "ngrok-url.txt";
if (file_exists($url_file)) {
    $url = trim(file_get_contents($url_file));
    if (!empty($url) && filter_var($url, FILTER_VALIDATE_URL)) {
        header("Location: " . $url);
        exit;
    }
}
?>
<!DOCTYPE html>
<html>
<head><title>PEACOCK ENGINE</title><style>
body{font-family:system-ui,sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#0f0f0f;color:#fff;text-align:center}
.box{padding:2rem}.error{color:#ff4444}code{background:#333;padding:0.2rem 0.5rem;border-radius:4px}
</style></head>
<body>
<div class="box">
<h1>🦚 PEACOCK ENGINE</h1>
<p class="error">Tunnel not active</p>
<p>Start ngrok and run the bridge script</p>
<p><code>ngrok http 3099</code></p>
</div>
</body>
</html>'

# === COLORS ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🌉 NGROK BRIDGE (PHP Version)${NC}"
echo "==============================="
echo ""

# Function to upload via FTP
upload_ftp() {
    local content=$1
    local remote_name=$2
    local temp_file=$(mktemp)
    echo "$content" > "$temp_file"
    
    if command -v lftp &> /dev/null; then
        lftp -u "$FTP_USER,$FTP_PASS" "$FTP_HOST" << EOF 2>/dev/null
set ssl:verify-certificate no
set ftp:ssl-allow no
cd $FTP_PATH
put $temp_file -o $remote_name
bye
EOF
    else
        ftp -n "$FTP_HOST" 2>/dev/null << EOF
user $FTP_USER $FTP_PASS
cd $FTP_PATH
put $temp_file $remote_name
bye
EOF
    fi
    local result=$?
    rm "$temp_file"
    return $result
}

# Initialize mode - upload PHP redirect file
if [ "$1" == "--init" ]; then
    echo "Uploading PHP redirect script..."
    if upload_ftp "$PHP_SCRIPT" "index.php"; then
        echo -e "${GREEN}✓ PHP redirect uploaded${NC}"
        echo ""
        echo "Now run without --init to start monitoring ngrok"
    else
        echo -e "${RED}✗ Upload failed - check FTP settings${NC}"
    fi
    exit 0
fi

# Main monitoring mode
echo "Domain: $DOMAIN"
echo "FTP: $FTP_USER@$FTP_HOST"
echo ""
echo -e "${YELLOW}Waiting for ngrok...${NC}"
echo "(Run with --init first if you haven't uploaded the PHP file)"
echo ""

LAST_URL=""

while true; do
    CURRENT_URL=$(curl -s $NGROK_API 2>/dev/null | grep -o '"public_url":"https://[^"]*"' | head -1 | cut -d'"' -f4)
    
    if [ -z "$CURRENT_URL" ]; then
        echo -ne "\r${YELLOW}⏳ Waiting for ngrok tunnel...${NC}   "
        sleep 5
        continue
    fi
    
    # Clear the waiting message
    echo -ne "\r\033[K"
    
    if [ "$CURRENT_URL" != "$LAST_URL" ]; then
        echo -e "${GREEN}✓ Ngrok URL: $CURRENT_URL${NC}"
        echo -n "Updating redirect... "
        
        # Just upload the tiny URL file
        if upload_ftp "$CURRENT_URL" "ngrok-url.txt"; then
            echo -e "${GREEN}✓ DONE${NC}"
            echo ""
            echo -e "${GREEN}🦚 Live at: https://$DOMAIN${NC}"
            echo ""
            LAST_URL="$CURRENT_URL"
        else
            echo -e "${RED}✗ Failed${NC}"
        fi
    fi
    
    sleep $CHECK_INTERVAL
done
