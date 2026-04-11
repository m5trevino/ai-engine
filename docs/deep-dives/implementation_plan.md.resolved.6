# UI Routing & Deployment Fix

The "Not Found" error at `https://chat.save-aichats.com/` is caused by a path mismatch in `app/main.py` and a missing production build (`dist/`) on the VPS. This plan will anchor the routing and generate the missing assets.

## User Review Required

> [!IMPORTANT]
> **Build Requirement**: To fix this, we MUST run `npm run build` in the `ui/` directory on the VPS. This generates the `dist/` folder that FastAPI needs to serve the site.

## Proposed Changes

### [Backend Routing Alignment]

#### [MODIFY] [main.py](file:///home/flintx/peacock-engine/app/main.py)
- Update the static file mounting logic to look for `ui/dist` instead of the legacy `peacock-ui/dist`.
- Implement a fallback sequence to ensure the UI mounts regardless of which folder is used for the build.

### [Production Asset Generation]

#### [EXECUTE] [Terminal](bash)
- Run `cd ui && npm run build` (locally and on VPS) to generate the production assets.

## Open Questions

- None. The 404 is a direct result of the `dist` folder missing from the mount check in `main.py:56`.

## Verification Plan

### Automated Tests
- Verify path existence: `ls ui/dist/index.html` after build.
- Verify FastAPI health: `curl http://localhost:3099/health`.

### Manual Verification
- Refresh `https://chat.save-aichats.com/` and verify the UI loads.
