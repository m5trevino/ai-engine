# Model Registry Shadow Liquidation

The UI remains stuck on "LOADING MODELS..." because of a routing collision in the backend. A legacy `MODELS_ALIAS` route is hijacking requests to `/v1/chat/models` and returning a flat list of models, while the "Masterpiece" UI strictly expects a gateway-grouped object. This plan will restore the correct data flow.

## User Review Required

> [!IMPORTANT]
> **Routing Collision**: Your backend had two different "Source of Truth" definitions for models competing for the same URL. I am decommissioning the legacy one to allow the grouped architecture to take lead.

## Proposed Changes

### [Backend Routing Hardening]

#### [MODIFY] [main.py](file:///home/flintx/peacock-engine/app/main.py)
- **Liquidate Shadow Route**: Remove or comment out line 78 (`app.include_router(models_router, prefix="/v1/chat/models", ...)`).
- This allows the `chat_router` (included on line 73) to correctly handle `/v1/chat/models` with the grouped data structure expected by the React UI.

## Open Questions

- None. The shadowing is the clear cause of the component render failure.

## Verification Plan

### Automated Tests
- `curl http://localhost:3099/v1/chat/models` should now return an Object (`{ "google": [...], "groq": [...] }`) instead of a List (`[...]`).

### Manual Verification
- Refresh `https://chat.save-aichats.com/`. 
- Open the model menu; it should immediately populate with the grouped categories.
