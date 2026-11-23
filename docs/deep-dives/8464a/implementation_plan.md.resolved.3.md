# Plan - Force Alignment & Final Hardening (ai-engine.git)

## Goal

Resolve divergent repository history and apply backend/frontend hardening to ensure the VPS deployment is bulletproof and type-safe.

## User Review Required

> [!IMPORTANT]
> I have recalibrated the remote to `https://github.com/m5trevino/ai-engine.git`.
> I am applying the hardening fixes to the production path: `ui/masterpiece-ui-reference/vite/src/App.tsx`.
> I am force-pushing these updates to `origin/main` to ensure your VPS can sync the "Sand-Hill" quality code immediately.

## Proposed Changes

### [Component] Backend Core (Hardening)

#### [MODIFY] [logger.py](file:///home/flintx/peacock-engine/app/utils/logger.py)

- Add `HighSignalLogger.error()` method to prevent "AttributeError" crashes during token counting or gateway failures.

### [Component] Frontend WebUI (Type Safety)

#### [MODIFY] [App.tsx](file:///home/flintx/peacock-engine/ui/masterpiece-ui-reference/vite/src/App.tsx)

- Refactor `ApiKeyCard` and `ModelRow` to include explicit prop interfaces with `key?: React.Key`.
- This clears the persistent TypeScript assignment errors in the mapping loops.

## Verification Plan

### Automated Tests

- Run `backend_check.py` to verify the logger and counter integrity on the production branch.
- Audit git logs to ensure the hardening fixes are successfully pushed to `ai-engine.git`.

### Manual Verification

- Verify that your VPS (`root@ubuntu-8gb-hel1-1`) sees the new commits after `git pull`.
- Confirm the UI in "Mission Control" displays telemetry without console errors.
