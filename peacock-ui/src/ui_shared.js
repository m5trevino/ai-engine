/**
 * PEACOCK UI SHARED LOGIC
 * Manages consistent elements across all 5 pages.
 */

import { gateway } from './gateway';

export const ui = {
    /**
     * Initializes common elements: Stats, Live Wire, and Navigation.
     */
    async init() {
        console.log("PEACOCK_ENGINE: INITIALIZING_NEURAL_UPLINK...");
        this.updateStats();
        this.startLiveWire();
        this.setupNavigation();
    },

    /**
     * Updates bottom status bar and right sidebar stats.
     */
    async updateStats() {
        try {
            const usage = await gateway.getKeys();
            const totalCost = usage?.total_cost || 0;
            const totalTokens = usage?.total_tokens || 0;

            // Mapping to IDs in the HTML files
            const costEls = document.querySelectorAll('#billing-total, #session-cost');
            const tokenEls = document.querySelectorAll('#session-tokens, #loaded-tokens');

            costEls.forEach(el => el.textContent = `$${totalCost.toFixed(2)}`);
            tokenEls.forEach(el => el.textContent = this.formatNumber(totalTokens));
        } catch (err) {
            console.warn("STATS_FETCH_FAILURE", err);
        }
    },

    startLiveWire() {
        const terminal = document.getElementById('live-wire-terminal') || document.querySelector('.technical-live-wire');
        if (!terminal) return;

        // For now, simulating if the endpoint isn't ready
        const log = (msg, type = 'info') => {
            const div = document.createElement('div');
            div.className = 'flex gap-2 opacity-80 animate-pulse';
            const time = new Date().toLocaleTimeString();
            const colorClass = type === 'error' ? 'text-error' : (type === 'success' ? 'text-[#00C851]' : 'text-outline');
            div.innerHTML = `<span class="${colorClass}">[${time}]</span> <span class="text-on-surface uppercase font-['JetBrains_Mono']">${msg}</span>`;
            terminal.prepend(div);
            if (terminal.children.length > 20) terminal.lastChild.remove();
        };

        log("SYSTEM_HANDSHAKE_ESTABLISHED", 'success');
        log("LISTENING_ON_PRIMARY_MESH", 'info');
    },

    /**
     * Helper to format numbers with commas.
     */
    formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    },

    /**
     * Logic for navbar/sidebar active states and triggers.
     */
    setupNavigation() {
        // Wire "FIRE IT UP" audit button
        const auditBtns = document.querySelectorAll('#fire-it-up-btn, .gold-glow-audit');
        auditBtns.forEach(btn => {
            btn.onclick = async () => {
                console.log("PEACOCK_ENGINE: INITIATING_FLEET_AUDIT...");
                try {
                    const res = await gateway.audit();
                    alert(`AUDIT_COMPLETE: ${res.message}`);
                } catch (err) {
                    alert(`AUDIT_FAILURE: ${err.message}`);
                }
            };
        });

        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('nav a, aside nav a');
        navLinks.forEach(link => {
            if (link.getAttribute('href') && currentPath.includes(link.getAttribute('href'))) {
                link.classList.add('active-nav-link'); // We'll add styles for this
            }
        });
    }
};

// Auto-init on DOM load
window.addEventListener('DOMContentLoaded', () => ui.init());
