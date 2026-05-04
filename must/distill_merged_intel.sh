# --- DATA CONTENT START ---
#!/bin/bash
# ===============================================================
# 🦚 PEACOCK ENGINE V4: MERGED CONTENT DISTILLER
# Purpose: Transform a massive merged dump into a concise blueprint.
# Target: /home/flintx/hetzner/ai-engine/master-info/striker/merged_content.txt
# ===============================================================

TARGET="/home/flintx/hetzner/ai-engine/master-info/striker/merged_content.txt"
OUTPUT="/home/flintx/hetzner/regroup/striker_master_blueprint.txt"

if [ ! -f "$TARGET" ]; then
    echo -e "\033[1;31m❌ Error: Target file not found at $TARGET\033[0m"
    exit 1
fi

echo -e "\033[1;34m🔍 Distilling Merged Intel into Master Blueprint...\033[0m"

# The Surgical Strike:
# 1. Remove the ASCII box borders and "File:" labels.
# 2. Remove the "Note: This is purely..." disclaimers.
# 3. Remove common markdown fluff like "Table of Contents" or "Executive Summary" headers if they repeat.
# 4. Remove duplicate lines (crucial for merged files).
# 5. Remove empty lines.

grep -vE "^(╭━─━─━─|╰━─━─━─|--- File:|┎━─━─━─|┖━─━─━─|┍──━──━──|┕──━──━──|╔═══━━━───|╚═══━━━───|█▀▀ █▀▀|█▄█ ██▄|░█░█░█▀▀|░▀▀▀░▀▀▀|# --- DATA CONTENT|# =================|# SYNDICATE ASSET:|Note: _This is purely|## Table of Contents|# PEACOCK ENGINE -|# 🦚 PEACOCK ENGINE|# 💀 PEACOCK ENGINE|# 🦅 PEACOCK ENGINE)" "$TARGET" | \
sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | \
awk '!visited[$0]++' | \
sed '/^$/d' > "$OUTPUT"

LINE_COUNT_OLD=$(wc -l < "$TARGET")
LINE_COUNT_NEW=$(wc -l < "$OUTPUT")
SAVED=$((LINE_COUNT_OLD - LINE_COUNT_NEW))

echo -e "\033[1;92m🎯 Master Blueprint Created: $OUTPUT\033[0m"
echo -e "\033[1;37m📑 Original Lines: $LINE_COUNT_OLD\033[0m"
echo -e "\033[1;37m📄 Concise Lines: $LINE_COUNT_NEW\033[0m"
echo -e "\033[1;32m✨ Noise Removed: $SAVED lines of clutter liquidated.\033[0m"
# --- DATA CONTENT END ---
