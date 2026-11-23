# API Shadowing & Route Order Correction

The 404 errors for `/v1/chat/models` and `/v1/keys/usage` are caused by the **Routing Order** in `main.py`. Because the WebUI is mounted at the root (`/`) before the API routers are registered, it "eats" the incoming requests and fails to find matching static files. This plan will correctly prioritize the API.

## User Review Required

> [!IMPORTANT]
> **Route Prioritization**: We are moving all UI and SPA logic to the absolute bottom of the application. This ensures that FastAPI checks every single API route first before falling back to the UI.

## Proposed Changes

### [Backend Routing Architecture]

#### [MODIFY] [main.py](file:///home/flintx/peacock-engine/app/main.py)
- **Relocate UI Mounting**: Move the `StaticFiles` mounting (lines 54-61) to the bottom of the file, after all `app.include_router` calls.
- **Relocate Startup Segment**: Move the `CLIFormatter` startup logs to ensure they run correctly with the new order.
- **Clean Aliases**: Remove the redundant `/v1/keys/usage` alias (line 80) since the main `/v1/keys` router already includes the `/usage` endpoint.

## Open Questions

- None. Route order is a common FastAPI pitfall; moving the "Catch-All" to the end is the architectural standard.

## Verification Plan

### Automated Tests
- `curl -I http://localhost:3099/v1/chat/models` should return `200 OK`.
- `curl -I http://localhost:3099/v1/keys/usage` should return `200 OK`.
- `curl -I http://localhost:3099/` should still return the UI.

### Manual Verification
- Refresh `https://chat.save-aichats.com/`. 
- Verify the model list AND the key telemetry now populate correctly.
