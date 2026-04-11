# Neural Link Restoration: Dynamic API Resolution

The "LOADING MODELS..." hang occurs because the WebUI is still trying to talk to `http://localhost:3099` instead of the production VPS. The browser blocks this due to "Mixed Content" (HTTPS vs HTTP) and local-loopback restrictions. This plan will anchor the UI to the actual domain.

## User Review Required

> [!IMPORTANT]
> **Dynamic Routing**: I am switching the UI to use relative paths. This means it will automatically detect whether it's on your local rig or the VPS, fixing the "Neural Link" failure instantly.

## Proposed Changes

### [UI API Hardening]

#### [MODIFY] [api.ts](file:///home/flintx/peacock-engine/ui/src/lib/api.ts)
- **Liquidate `localhost`**: Remove the hardcoded `http://localhost:3099` base URL.
- **Dynamic REST Base**: Set `API_BASE` to an empty string `""` for production, allowing relative routing.
- **Production WebSocket Logic**: 
    - Implement a protocol detector (`wss:` vs `ws:`) based on `window.location.protocol`.
    - Construct the WebSocket URL using `window.location.host` instead of a hardcoded string.

## Open Questions

- None. This is a standard requirement for transitioning from local dev to a production domain.

## Verification Plan

### Automated Tests
- Build verification: `npm run build` should pass.
- Inspect `dist/assets/index-*.js` to ensure `localhost` is absent.

### Manual Verification
- Refresh `https://chat.save-aichats.com/`.
- Open the model menu and verify it displays: 16 Groq models, 3 Google models, etc.
