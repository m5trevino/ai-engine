# SPA Catch-All Routing Fix

The 404 Not Found errors for paths like `/chat` occur because FastAPI attempts to find a server-side route for those paths. Since this is a React SPA, we need to instruct FastAPI to serve `index.html` for any unmatched GET requests, allowing the React Router to handle the navigation.

## User Review Required

> [!NOTE]
> **SPA Behavior**: With this change, any URL that doesn't match an API route or a static file will serve the UI. This is standard for modern web apps like the Peacock Engine.

## Proposed Changes

### [Backend Routing Hardening]

#### [MODIFY] [main.py](file:///home/flintx/peacock-engine/app/main.py)
- Import `FileResponse` from `fastapi.responses`.
- Add a catch-all route at the bottom of the application.
- Implementation logic:
    - If a path is requested that doesn't match an existing route.
    - And it's NOT an API call (`/v1/`) or a static file (`/static/`).
    - Serve `app/static/index.html`.

## Open Questions

- None. This is the standard fix for SPA 404s in FastAPI.

## Verification Plan

### Automated Tests
- `curl -I http://localhost:3099/chat` should return `200 OK` (serving index.html).
- `curl -I http://localhost:3099/v1/unknown` should still return `404 Not Found` (preserving API errors).

### Manual Verification
- Navigate to `https://chat.save-aichats.com/chat` and verify the UI loads correctly.
