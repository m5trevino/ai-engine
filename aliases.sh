#!/bin/bash
# 🦚 PEACOCK ENGINE Aliases
# Add to ~/.bashrc: source /root/peacock-engine/aliases.sh

# Git Aliases - Individual
alias pull-engine='cd /root/peacock-engine && git pull && echo "✓ peacock-engine pulled"'
alias pull-save='cd /root/save-aichats && git pull && echo "✓ save-aichats pulled"'
alias pull-all='pull-engine && pull-save'

alias push-engine='cd /root/peacock-engine && git add -A && git commit -m "update: $(date +%Y-%m-%d-%H:%M)" && git push && echo "✓ peacock-engine pushed"'
alias push-save='cd /root/save-aichats && git add -A && git commit -m "update: $(date +%Y-%m-%d-%H:%M)" && git push && echo "✓ save-aichats pushed"'
alias push-all='push-engine && push-save'

# Combined git operations
alias cycle-repo='echo "🔄 Cycling repos..." && push-all && echo "" && pull-all'

# Engine Control
alias ai-engine-start='cd /root/hetzner/ai-engine && bash ai-engine-start.sh'
alias ai-engine-stop='kill $(cat /tmp/engine.pid 2>/dev/null) 2>/dev/null && echo "🛑 Engine stopped" || echo "Already stopped"'
alias ai-engine-status='echo "Engine: $(pgrep -f "python -m app.main" > /dev/null && echo "✓ Running" || echo "✗ Stopped")" && echo "Proxy:  (Caddy Systemd Managed)"'
alias ai-engine-logs='tail -f /root/hetzner/logs/engine.log'

# Display help
echo -e "\033[0;34m🦚 PEACOCK ENGINE ALIASES LOADED\033[0m"
echo "  ai-engine-start   - Production ignition (engine + portal sync)"
echo "  ai-engine-stop    - Cease engine operations"
echo "  ai-engine-status  - Check engine health"
echo "  ai-engine-logs    - Watch production stream"

# Portal update
alias update-portal='cd /root/peacock-engine && ./update-peacock-portal.sh && cd /root/save-aichats && git add . && git commit -m "portal update" && git push'

# Show all aliases
alias peacock-help='echo "🦚 PEACOCK ENGINE Aliases"
echo "========================="
echo ""
echo "Git Operations:"
echo "  pull-engine    - Pull peacock-engine"
echo "  pull-save      - Pull save-aichats"
echo "  pull-all       - Pull both"
echo "  push-engine    - Push peacock-engine"
echo "  push-save      - Push save-aichats"
echo "  push-all       - Push both"
echo "  cycle-repo     - Push all, then pull all"
echo ""
echo "Engine Control:"
echo "  ai-engine-start   - Full startup (engine + ngrok + portal)"
echo "  ai-engine-stop    - Stop all"
echo "  ai-engine-logs    - View engine logs"
echo "  ai-engine-status  - Check status"
echo ""
echo "Ngrok:"
echo "  ngrok-status   - Show token status"
echo "  ngrok-next     - Rotate to next token"
echo "  ngrok-logs     - View ngrok logs"
echo ""
echo "Quick:"
echo "  peacock-api    - Show health JSON"
echo "  peacock-url    - Show current ngrok URL"
echo "  update-portal  - Update and push portal"'

echo "🦚 PEACOCK aliases loaded! Type 'peacock-help' for commands"
